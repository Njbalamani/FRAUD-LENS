from django.db.models import Avg, Count, Max, Min, Sum
from django.utils.dateparse import parse_datetime
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.core.permissions import IsAnalystOrAdmin, IsAnalystWriteOrReadOnly
from apps.core.utils import request_organization

from .models import FinancialAccount, Transaction, TransactionImport
from .serializers import FinancialAccountSerializer, TransactionImportSerializer, TransactionSerializer
from .services import import_transactions_csv


class FinancialAccountViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = FinancialAccount.objects.select_related("organization").all()
    serializer_class = FinancialAccountSerializer
    permission_classes = [IsAnalystOrAdmin]
    search_fields = ["account_holder", "account_number"]
    filterset_fields = ["account_type", "status", "currency"]
    ordering_fields = ["opened_at", "created_at", "account_holder"]

    def get_queryset(self):
        queryset = super().get_queryset()
        organization = request_organization(self.request)
        if organization:
            queryset = queryset.filter(organization_id=organization)
        return queryset


class TransactionViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Transaction.objects.select_related("account", "risk_score").all()
    serializer_class = TransactionSerializer
    permission_classes = [IsAnalystWriteOrReadOnly]
    filterset_fields = ["status", "transaction_type", "channel", "currency", "source"]
    search_fields = ["transaction_id", "description", "counterparty_reference", "location"]
    ordering_fields = ["timestamp", "amount", "created_at"]

    def get_queryset(self):
        queryset = super().get_queryset()
        organization = request_organization(self.request)
        if organization:
            queryset = queryset.filter(organization_id=organization)
        params = self.request.query_params
        start = params.get("start")
        end = params.get("end")
        min_amount = params.get("min_amount")
        max_amount = params.get("max_amount")
        if start:
            parsed = parse_datetime(start)
            if parsed:
                queryset = queryset.filter(timestamp__gte=parsed)
        if end:
            parsed = parse_datetime(end)
            if parsed:
                queryset = queryset.filter(timestamp__lte=parsed)
        if min_amount:
            try:
                queryset = queryset.filter(amount__gte=float(min_amount))
            except ValueError:
                pass
        if max_amount:
            try:
                queryset = queryset.filter(amount__lte=float(max_amount))
            except ValueError:
                pass
        return queryset

    @action(detail=False, methods=["get"])
    def summary(self, request):
        queryset = self.get_queryset()
        aggregates = queryset.aggregate(
            count=Count("id"),
            total=Sum("amount"),
            average=Avg("amount"),
            minimum=Min("amount"),
            maximum=Max("amount"),
        )
        by_type = list(queryset.values("transaction_type").annotate(count=Count("id"), total=Sum("amount")).order_by("-count"))
        by_status = list(queryset.values("status").annotate(count=Count("id")).order_by("-count"))
        return Response(
            {
                "count": aggregates["count"],
                "total_amount": float(aggregates["total"] or 0),
                "average_amount": float(aggregates["average"] or 0),
                "minimum_amount": float(aggregates["minimum"] or 0),
                "maximum_amount": float(aggregates["maximum"] or 0),
                "by_type": by_type,
                "by_status": by_status,
            }
        )


class TransactionImportViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = TransactionImport.objects.select_related("imported_by").all()
    serializer_class = TransactionImportSerializer
    permission_classes = [IsAnalystOrAdmin]
    ordering_fields = ["created_at", "rows_total", "rows_imported"]
    filterset_fields = ["status"]

    def get_queryset(self):
        queryset = super().get_queryset()
        organization = request_organization(self.request)
        if organization:
            queryset = queryset.filter(organization_id=organization)
        return queryset


class TransactionImportView(APIView):
    permission_classes = [IsAnalystOrAdmin]

    def post(self, request):
        organization = request_organization(request)
        if not organization:
            return Response({"detail": "No organization context"}, status=status.HTTP_400_BAD_REQUEST)
        uploaded = request.FILES.get("file")
        if not uploaded:
            return Response({"detail": "A CSV file is required"}, status=status.HTTP_400_BAD_REQUEST)
        mapping = request.data.get("column_mapping")
        record = import_transactions_csv(
            organization,
            uploaded,
            uploaded.name,
            mapping=mapping,
            imported_by=request.user,
        )
        return Response(TransactionImportSerializer(record).data, status=status.HTTP_201_CREATED)
