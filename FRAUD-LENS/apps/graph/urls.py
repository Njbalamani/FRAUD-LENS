from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import ClusterView, GraphView, PathView, RelationshipSyncView, RelationshipViewSet

router = DefaultRouter()
router.register("relationships", RelationshipViewSet, basename="relationship")

urlpatterns = [
    path("graph/", GraphView.as_view(), name="graph-data"),
    path("clusters/", ClusterView.as_view(), name="graph-clusters"),
    path("path/", PathView.as_view(), name="graph-path"),
    path("sync/", RelationshipSyncView.as_view(), name="graph-sync"),
    path("", include(router.urls)),
]
