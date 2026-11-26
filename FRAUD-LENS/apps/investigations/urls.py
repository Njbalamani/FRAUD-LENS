from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import CaseEvidenceViewSet, CaseNoteViewSet, InvestigationCaseViewSet

router = DefaultRouter()
router.register("cases", InvestigationCaseViewSet, basename="case")
router.register("notes", CaseNoteViewSet, basename="case-note")
router.register("evidence", CaseEvidenceViewSet, basename="case-evidence")

urlpatterns = [path("", include(router.urls))]
