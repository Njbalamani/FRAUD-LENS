from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import APIRootView, AuditLogViewSet, GlobalSearchView, HealthView, SchemaView

router = DefaultRouter()
router.register("audit-logs", AuditLogViewSet, basename="audit-log")

urlpatterns = [
    path("", APIRootView.as_view(), name="api-root"),
    path("schema/", SchemaView.as_view(), name="api-schema"),
    path("search/", GlobalSearchView.as_view(), name="global-search"),
    path("", include(router.urls)),
]
