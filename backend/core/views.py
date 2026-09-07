import os
from django.contrib.auth import get_user_model
from django.db import connection
from django.db.models import Q
from django.shortcuts import get_object_or_404
from rest_framework import status
from rest_framework.decorators import api_view, throttle_classes
from rest_framework.response import Response
from rest_framework.exceptions import PermissionDenied
from rest_framework.throttling import AnonRateThrottle
from rest_framework.views import APIView
from rest_framework.authtoken.models import Token
from rest_framework.permissions import IsAuthenticated
from drf_spectacular.utils import extend_schema
from .models import ApplicationGuide, ChatMessage, ChatSession, Citation, SafetyAlert, StandardRecord
from .serializers import (ApplicationGuideSerializer, AskMessageSerializer, ChatMessageSerializer,
    ChatSessionSerializer, FeedbackSerializer, StandardRecommendSerializer, StandardSearchSerializer,
    StandardSerializer, VerificationSerializer)
from .serializers import GoogleCredentialSerializer
from .services.rag import RagAnswerService, detect_intent
from .services.retrieval import terms
from .services.verification import VerificationService
from .services.vision import VisionService
from .services.gemini import AIProviderError

class BurstThrottle(AnonRateThrottle):
    rate = "120/minute"

class SessionListCreateView(APIView):
    def get(self, request):
        if not request.user.is_authenticated:
            return Response([])
        sessions=ChatSession.objects.filter(user=request.user).order_by("-updated_at")[:50]
        return Response(ChatSessionSerializer(sessions,many=True).data)
    @extend_schema(request=ChatSessionSerializer, responses=ChatSessionSerializer)
    def post(self, request):
        serializer = ChatSessionSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        session = serializer.save(user=request.user if request.user.is_authenticated else None)
        return Response(ChatSessionSerializer(session).data, status=status.HTTP_201_CREATED)

class SessionDetailView(APIView):
    def get(self, request, session_id):
        session = get_object_or_404(ChatSession, public_id=session_id)
        if session.user_id and session.user_id != getattr(request.user,"id",None):
            raise PermissionDenied("This conversation belongs to another account.")
        return Response(ChatSessionSerializer(session).data)
    def delete(self, request, session_id):
        session=get_object_or_404(ChatSession, public_id=session_id)
        if session.user_id != getattr(request.user,"id",None):
            raise PermissionDenied("Sign in with the conversation owner to delete it.")
        session.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)
    def patch(self, request, session_id):
        session=get_object_or_404(ChatSession, public_id=session_id)
        if session.user_id != getattr(request.user,"id",None):
            raise PermissionDenied("Sign in with the conversation owner to pin it.")
        if "is_pinned" not in request.data or not isinstance(request.data["is_pinned"], bool):
            return Response({"error":{"code":"invalid_pin_state","message":"is_pinned must be true or false."}},status=status.HTTP_400_BAD_REQUEST)
        session.is_pinned=request.data["is_pinned"]
        session.save(update_fields=["is_pinned","updated_at"])
        return Response(ChatSessionSerializer(session).data)

class MessageCreateView(APIView):
    throttle_classes = [BurstThrottle]
    @extend_schema(request=AskMessageSerializer, responses=ChatMessageSerializer)
    def post(self, request, session_id):
        session = get_object_or_404(ChatSession, public_id=session_id)
        if session.user_id and session.user_id != getattr(request.user,"id",None):
            raise PermissionDenied("This conversation belongs to another account.")
        if not request.user.is_authenticated and session.messages.filter(role="user").count() >= 6:
            return Response({"error":{"code":"login_required","message":"Sign in with Google to continue after six guest questions."}},status=status.HTTP_403_FORBIDDEN)
        if request.user.is_authenticated and session.user_id is None:
            session.user=request.user
            session.save(update_fields=["user","updated_at"])
        payload = AskMessageSerializer(data=request.data)
        payload.is_valid(raise_exception=True)
        question, language = payload.validated_data["message"], payload.validated_data["language"]
        user_message=ChatMessage.objects.create(session=session, role="user", content=question, trace={"hidden": True} if payload.validated_data.get("silent") else {})
        latest_assistant=session.messages.filter(role="assistant").order_by("-created_at").first()
        previous = latest_assistant if latest_assistant and latest_assistant.trace.get("awaiting_brand") else None
        contextual_question=question
        if previous and "ROADMAP_STAGE" not in question and detect_intent(question) not in {"lab_locator", "testing_guidance"}:
            contextual_question=f"I need certification and production guidance for {previous.trace['detected_product']}. The user says the brand or company is: {question}."
        previous_lab=session.messages.filter(role="assistant",intent="lab_locator").order_by("-created_at").first()
        if previous_lab and len(question.split())<=5 and not previous:
            contextual_question=f"Find a nearby lab in {question} for the product and standard discussed in this conversation."
        current_intent=detect_intent(question)
        if current_intent in {"lab_locator","testing_guidance"}:
            prior_user=(session.messages.filter(role="user").exclude(id=user_message.id)
                        .exclude(content__contains="ROADMAP_STAGE")
                        .exclude(content__icontains="nearby lab")
                        .order_by("-created_at").first())
            if prior_user: contextual_question=f"{question}\nPreviously discussed product context: {prior_user.content}"
        result = RagAnswerService().answer(contextual_question, language)
        trace = {**result.trace, "next_steps": result.next_steps}
        message = ChatMessage.objects.create(session=session, role="assistant", content=result.answer,
            intent=result.intent, confidence=result.confidence, abstained=result.abstained, trace=trace)
        for ordinal, item in enumerate(result.citations, 1):
            Citation.objects.create(message=message, chunk=item.chunk, ordinal=ordinal, label=f"{item.chunk.document.standard_number} — {item.chunk.section or 'Scope'}")
        if session.messages.count() <= 2:
            session.title = question[:80]
        session.language = language
        session.save(update_fields=["title", "language", "updated_at"])
        return Response(ChatMessageSerializer(message).data, status=status.HTTP_201_CREATED)

class ImageAnalysisView(APIView):
    throttle_classes=[BurstThrottle]
    allowed_types={"image/jpeg","image/png","image/webp"}
    def post(self,request,session_id):
        session=get_object_or_404(ChatSession,public_id=session_id)
        if session.user_id and session.user_id!=getattr(request.user,"id",None): raise PermissionDenied("This conversation belongs to another account.")
        upload=request.FILES.get("image")
        if not upload:return Response({"error":{"code":"image_required","message":"Choose a product image."}},status=400)
        if upload.content_type not in self.allowed_types:return Response({"error":{"code":"invalid_image","message":"Use a JPEG, PNG, or WebP image."}},status=400)
        if upload.size>5*1024*1024:return Response({"error":{"code":"image_too_large","message":"Image must be 5 MB or smaller."}},status=400)
        language=request.data.get("language","en")
        ChatMessage.objects.create(session=session,role="user",content=f"Product photo: {upload.name}")
        try:detection=VisionService().analyze(upload.read(),upload.content_type,upload.name)
        except AIProviderError as exc:return Response({"error":{"code":"vision_failed","message":str(exc)}},status=503)
        if not detection.product:
            message=ChatMessage.objects.create(session=session,role="assistant",content="I could not identify the product confidently. Please upload a clearer photo showing the complete product and its label, or tell me the product name.",intent="product_image_clarification",confidence=0,abstained=True,trace={"next_steps":[]})
            return Response(ChatMessageSerializer(message).data,status=201)
        if not detection.brand:
            details="; ".join(detection.visible_details) or "No readable label details"
            content=f"I identified this as **{detection.product}** ({round(detection.confidence*100)}% visual confidence). Visible details: {details}. I could not reliably read the company or brand. Which company/brand manufactures it? Once you confirm that, I’ll provide the likely standard, certification route, and production roadmap."
            message=ChatMessage.objects.create(session=session,role="assistant",content=content,intent="product_image_clarification",confidence=detection.confidence,trace={"detected_product":detection.product,"awaiting_brand":True,"visible_details":detection.visible_details,"next_steps":[]})
            return Response(ChatMessageSerializer(message).data,status=201)
        query=f"I will be making {detection.product} under the brand {detection.brand}. Which certification is required to get this product into production? Provide a roadmap."
        result=RagAnswerService().answer(query,language)
        trace={**result.trace,"next_steps":result.next_steps,"detected_product":detection.product,"detected_brand":detection.brand}
        message=ChatMessage.objects.create(session=session,role="assistant",content=f"Image detected: {detection.product} · Brand: {detection.brand}\n\n{result.answer}",intent=result.intent,confidence=min(result.confidence,detection.confidence),abstained=result.abstained,trace=trace)
        for ordinal,item in enumerate(result.citations,1):Citation.objects.create(message=message,chunk=item.chunk,ordinal=ordinal,label=f"{item.chunk.document.standard_number} — {item.chunk.section or 'Scope'}")
        return Response(ChatMessageSerializer(message).data,status=201)

@api_view(["POST"])
def standards_search(request):
    serializer = StandardSearchSerializer(data=request.data); serializer.is_valid(raise_exception=True)
    query = serializer.validated_data["query"]
    records = StandardRecord.objects.filter(Q(number__icontains=query) | Q(title__icontains=query) | Q(scope__icontains=query))[:20]
    return Response({"results": StandardSerializer(records, many=True).data, "count": len(records), "demo_data": True})

@api_view(["POST"])
def standards_recommend(request):
    serializer = StandardRecommendSerializer(data=request.data); serializer.is_valid(raise_exception=True)
    query = " ".join(str(v) for v in serializer.validated_data.values())
    query_terms = terms(query)
    scored = []
    for record in StandardRecord.objects.all():
        match = len(query_terms & terms(f"{record.number} {record.title} {record.scope} {record.department}"))
        if match:
            scored.append((match, record))
    scored.sort(key=lambda x: x[0], reverse=True)
    results = []
    for score, record in scored[:5]:
        data = StandardSerializer(record).data
        data.update({"confidence": "high" if score >= 3 else "medium" if score == 2 else "exploratory",
                     "reason": f"Matched {score} relevant product or scope term(s).",
                     "disclaimer": "Demo recommendation. Confirm final applicability through an official BIS channel."})
        results.append(data)
    return Response({"results": results, "demo_data": True})

@api_view(["POST"])
def verification_check(request):
    serializer = VerificationSerializer(data=request.data); serializer.is_valid(raise_exception=True)
    return Response(VerificationService().check(serializer.validated_data["identifier"]))

@api_view(["GET"])
def guide_list(request):
    return Response(ApplicationGuideSerializer(ApplicationGuide.objects.all(), many=True).data)

@api_view(["GET"])
def guide_detail(request, slug):
    return Response(ApplicationGuideSerializer(get_object_or_404(ApplicationGuide, slug=slug)).data)

@api_view(["GET"])
def safety_alerts(request):
    return Response([{"id": x.id, "title": x.title, "summary": x.summary, "severity": x.severity, "source_url": x.source_url, "is_demo": x.is_demo} for x in SafetyAlert.objects.filter(active=True)])

@api_view(["POST"])
def feedback(request):
    serializer = FeedbackSerializer(data=request.data); serializer.is_valid(raise_exception=True); obj = serializer.save()
    return Response({"id": obj.id, "saved": True}, status=status.HTTP_201_CREATED)

@api_view(["GET"])
def health(request):
    db_ok = True
    try:
        connection.ensure_connection()
    except Exception:
        db_ok = False
    provider = "gemini" if os.getenv("AI_PROVIDER") == "gemini" and os.getenv("GEMINI_API_KEY") else "mock"
    return Response({"status": "ok" if db_ok else "degraded", "database": db_ok,
                     "vector_store": {"configured": bool(os.getenv("QDRANT_URL")), "active": os.getenv("VECTOR_PROVIDER", "local")},
                     "gemini": {"configured": bool(os.getenv("GEMINI_API_KEY")), "active_provider": provider}, "demo_mode": os.getenv("DEMO_MODE", "true").lower() == "true"})

@api_view(["POST"])
def google_auth(request):
    payload=GoogleCredentialSerializer(data=request.data); payload.is_valid(raise_exception=True)
    client_id=os.getenv("GOOGLE_CLIENT_ID")
    if not client_id:
        return Response({"error":{"code":"google_auth_not_configured","message":"Set GOOGLE_CLIENT_ID on the backend."}},status=503)
    try:
        from google.auth.transport import requests as google_requests
        from google.oauth2 import id_token
        claims=id_token.verify_oauth2_token(payload.validated_data["credential"],google_requests.Request(),client_id)
        if not claims.get("email_verified"): raise ValueError("Google email is not verified")
    except ValueError:
        return Response({"error":{"code":"invalid_google_token","message":"Google sign-in token is invalid or expired."}},status=400)
    User=get_user_model(); email=claims["email"].lower()
    user,created=User.objects.get_or_create(username=f"google_{claims['sub']}",defaults={"email":email,"first_name":claims.get("given_name","")[:150],"last_name":claims.get("family_name","")[:150]})
    if created: user.set_unusable_password(); user.save(update_fields=["password"])
    token,_=Token.objects.get_or_create(user=user)
    return Response({"token":token.key,"user":{"id":user.id,"email":user.email,"name":user.get_full_name() or user.email,"picture":claims.get("picture","")}})

@api_view(["GET"])
def auth_me(request):
    if not request.user.is_authenticated: return Response({"authenticated":False})
    return Response({"authenticated":True,"user":{"id":request.user.id,"email":request.user.email,"name":request.user.get_full_name() or request.user.username}})

@api_view(["POST"])
def auth_logout(request):
    if request.auth: request.auth.delete()
    return Response({"signed_out":True})
