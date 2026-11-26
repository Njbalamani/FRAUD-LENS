from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import ReportDownloadView, ReportGenerateView, ReportViewSet

router = DefaultRouter()
router.register("reports", ReportViewSet, basename="report")

urlpatterns = [
    path("generate/", ReportGenerateView.as_view(), name="report-generate"),
    path("download/<int:pk>/", ReportDownloadView.as_view(), name="report-download"),
    path("", include(router.urls)),
]
