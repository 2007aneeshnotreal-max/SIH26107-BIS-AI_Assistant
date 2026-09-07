from rest_framework import serializers
from .models import ApplicationGuide, ApplicationStep, ChatMessage, ChatSession, Citation, Feedback, StandardRecord

class CitationSerializer(serializers.ModelSerializer):
    source_title = serializers.CharField(source="chunk.document.title", read_only=True)
    document_id = serializers.CharField(source="chunk.document.document_id", read_only=True)
    standard_number = serializers.CharField(source="chunk.document.standard_number", read_only=True)
    section = serializers.CharField(source="chunk.section", read_only=True)
    page = serializers.IntegerField(source="chunk.page", read_only=True)
    source_url = serializers.URLField(source="chunk.document.source_url", read_only=True)
    source_type = serializers.CharField(source="chunk.document.source_type", read_only=True)
    excerpt = serializers.SerializerMethodField()

    class Meta:
        model = Citation
        fields = ("id", "ordinal", "label", "source_title", "document_id", "standard_number", "section", "page", "source_url", "source_type", "excerpt")

    def get_excerpt(self, obj):
        return obj.chunk.text[:420]

class ChatMessageSerializer(serializers.ModelSerializer):
    citations = CitationSerializer(many=True, read_only=True)
    next_steps = serializers.SerializerMethodField()
    lab_results = serializers.SerializerMethodField()
    class Meta:
        model = ChatMessage
        fields = ("id", "role", "content", "intent", "confidence", "abstained", "created_at", "citations", "next_steps", "lab_results")
    def get_next_steps(self, obj):
        return obj.trace.get("next_steps", [])
    def get_lab_results(self, obj):
        return obj.trace.get("lab_results", [])

class ChatSessionSerializer(serializers.ModelSerializer):
    messages = serializers.SerializerMethodField()
    class Meta:
        model = ChatSession
        fields = ("public_id", "title", "audience", "language", "is_pinned", "created_at", "messages")
        read_only_fields = ("public_id", "created_at", "messages")
    def get_messages(self, obj):
        visible_messages = [message for message in obj.messages.all() if not message.trace.get("hidden", False)]
        return ChatMessageSerializer(visible_messages, many=True).data

class AskMessageSerializer(serializers.Serializer):
    message = serializers.CharField(min_length=2, max_length=4000)
    language = serializers.ChoiceField(choices=("en", "hi"), default="en")
    silent = serializers.BooleanField(default=False, required=False)

class StandardSerializer(serializers.ModelSerializer):
    class Meta:
        model = StandardRecord
        fields = ("id", "number", "title", "equivalent_standard", "supersedes", "equivalence", "revision_count", "amendment_count", "aspect", "language", "department", "committee", "scope", "is_demo")

class StandardSearchSerializer(serializers.Serializer):
    query = serializers.CharField(max_length=500)

class StandardRecommendSerializer(serializers.Serializer):
    product_description = serializers.CharField(max_length=1000)
    category = serializers.CharField(max_length=120, required=False, allow_blank=True)
    intended_use = serializers.CharField(max_length=500, required=False, allow_blank=True)
    materials = serializers.CharField(max_length=500, required=False, allow_blank=True)
    manufacturing_details = serializers.CharField(max_length=1000, required=False, allow_blank=True)

class VerificationSerializer(serializers.Serializer):
    identifier = serializers.RegexField(r"^[A-Za-z0-9/() .:-]{3,100}$")

class ApplicationStepSerializer(serializers.ModelSerializer):
    class Meta:
        model = ApplicationStep
        fields = ("order", "title", "description", "checklist", "links", "estimated_next_step")

class ApplicationGuideSerializer(serializers.ModelSerializer):
    steps = ApplicationStepSerializer(many=True, read_only=True)
    class Meta:
        model = ApplicationGuide
        fields = ("slug", "title", "summary", "scheme", "language", "is_demo", "steps")

class FeedbackSerializer(serializers.ModelSerializer):
    class Meta:
        model = Feedback
        fields = ("message", "rating", "comment")
    def validate_rating(self, value):
        if value not in (-1, 1):
            raise serializers.ValidationError("Rating must be -1 or 1.")
        return value

class GoogleCredentialSerializer(serializers.Serializer):
    credential = serializers.CharField(min_length=100, max_length=10000, trim_whitespace=False)
