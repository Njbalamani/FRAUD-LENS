from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import BehaviorAnomaliesView, BehaviorProfileViewSet, BehaviorRebuildView

router = DefaultRouter()
router.register("profiles", BehaviorProfileViewSet, basename="behavior-profile")

urlpatterns = [
    path("rebuild/", BehaviorRebuildView.as_view(), name="behavior-rebuild"),
    path("anomalies/", BehaviorAnomaliesView.as_view(), name="behavior-anomalies"),
    path("", include(router.urls)),
]
