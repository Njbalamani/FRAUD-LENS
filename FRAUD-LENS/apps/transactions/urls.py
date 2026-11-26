from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import FinancialAccountViewSet, TransactionImportView, TransactionImportViewSet, TransactionViewSet

router = DefaultRouter()
router.register("accounts", FinancialAccountViewSet, basename="financial-account")
router.register("transactions", TransactionViewSet, basename="transaction")
router.register("imports", TransactionImportViewSet, basename="transaction-import")

urlpatterns = [
    path("import/", TransactionImportView.as_view(), name="transaction-import-create"),
    path("summary/", TransactionViewSet.as_view({"get": "summary"}), name="transaction-summary-global"),
    path("", include(router.urls)),
]
