from django.urls import path
from . import views

urlpatterns = [
    path("chat/sessions/", views.SessionListCreateView.as_view()),
    path("chat/sessions/<uuid:session_id>/", views.SessionDetailView.as_view()),
    path("chat/sessions/<uuid:session_id>/messages/", views.MessageCreateView.as_view()),
    path("chat/sessions/<uuid:session_id>/images/", views.ImageAnalysisView.as_view()),
    path("standards/search/", views.standards_search),
    path("standards/recommend/", views.standards_recommend),
    path("verification/check/", views.verification_check),
    path("guides/", views.guide_list),
    path("guides/<slug:slug>/", views.guide_detail),
    path("safety-alerts/", views.safety_alerts),
    path("feedback/", views.feedback),
    path("health/", views.health),
    path("auth/google/", views.google_auth),
    path("auth/me/", views.auth_me),
    path("auth/logout/", views.auth_logout),
]
