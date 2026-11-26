from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import CurrentUserView, OrganizationViewSet, TokenView, UserViewSet

router = DefaultRouter()
router.register("users", UserViewSet, basename="user")
router.register("organizations", OrganizationViewSet, basename="organization")

urlpatterns = [
    path("token/", TokenView.as_view(), name="token"),
    path("me/", CurrentUserView.as_view(), name="me"),
    path("", include(router.urls)),
]
