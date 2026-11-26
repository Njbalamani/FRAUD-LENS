from django.contrib import admin
from django.contrib.auth.views import LoginView, LogoutView
from django.urls import include, path

from apps.core.views import HealthView
from apps.dashboard import views as dashboard_views

urlpatterns = [
    path("", dashboard_views.dashboard, name="dashboard"),
    path("transactions/", dashboard_views.transactions_view, name="transactions-page"),
    path("network/", dashboard_views.network_view, name="network-page"),
    path("investigations/", dashboard_views.investigations_view, name="investigations-page"),
    path("reports/", dashboard_views.reports_view, name="reports-page"),
    path("login/", LoginView.as_view(template_name="login.html"), name="login"),
    path("logout/", LogoutView.as_view(next_page="login"), name="logout"),
    path("health/", HealthView.as_view(), name="health"),
    path("admin/", admin.site.urls),
    path("api/", include("apps.core.urls")),
    path("api/accounts/", include("apps.accounts.urls")),
    path("api/transactions/", include("apps.transactions.urls")),
    path("api/detection/", include("apps.detection.urls")),
    path("api/behavior/", include("apps.behavior.urls")),
    path("api/graph/", include("apps.graph.urls")),
    path("api/investigations/", include("apps.investigations.urls")),
    path("api/reports/", include("apps.reports.urls")),
]

handler403 = "apps.core.views.permission_denied"
handler404 = "apps.core.views.page_not_found"
handler500 = "apps.core.views.server_error"
