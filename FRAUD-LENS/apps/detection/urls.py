from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import DetectionAnalyzeView, DetectionExplainView, DetectionRunViewSet, FraudFindingViewSet, PerformanceViewSet, RiskScoreViewSet

router = DefaultRouter()
router.register("runs", DetectionRunViewSet, basename="detection-run")
router.register("findings", FraudFindingViewSet, basename="finding")
router.register("risk-scores", RiskScoreViewSet, basename="risk-score")
router.register("performance", PerformanceViewSet, basename="model-performance")

urlpatterns = [
    path("analyze/", DetectionAnalyzeView.as_view(), name="detection-analyze"),
    path("explain/", DetectionExplainView.as_view(), name="detection-explain"),
    path("", include(router.urls)),
]
