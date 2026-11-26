from django.conf import settings
from django.db.models import Q
from django.shortcuts import render
from rest_framework import viewsets
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.core.permissions import IsAdminRole

from .models import AuditLog
from .serializers import AuditLogSerializer
from .utils import request_organization


class APIRootView(APIView):
    permission_classes = [AllowAny]

    def get(self, request):
        return Response(
            {
                "name": "FraudLens API",
                "version": "1.0.0",
                "mode": settings.FRAUDLENS_MODE,
                "live_data_enabled": settings.FRAUDLENS_ENABLE_LIVE_DATA,
                "endpoints": {
                    "accounts": "/api/accounts/",
                    "transactions": "/api/transactions/",
                    "detection": "/api/detection/",
                    "behavior": "/api/behavior/",
                    "graph": "/api/graph/",
                    "investigations": "/api/investigations/",
                    "reports": "/api/reports/",
                    "search": "/api/search/",
                    "audit_logs": "/api/core/audit-logs/",
                    "health": "/health/",
                    "schema": "/api/schema/",
                },
            }
        )


class SchemaView(APIView):
    permission_classes = [AllowAny]

    def get(self, request):
        return Response(
            {
                "openapi": "3.0.3",
                "info": {"title": "FraudLens API", "version": "1.0.0"},
                "description": "Programmatic index of FraudLens REST endpoints. Full details are in docs/API.md.",
                "paths": {
                    "/api/accounts/token/": {"post": {"summary": "Obtain an API token"}},
                    "/api/transactions/import/": {"post": {"summary": "Import and validate a CSV transaction file"}},
                    "/api/transactions/transactions/": {"get": {"summary": "List masked transactions"}},
                    "/api/detection/analyze/": {"post": {"summary": "Run fraud detection and scoring"}},
                    "/api/detection/explain/": {"get": {"summary": "Show feature contributions and model metrics"}},
                    "/api/behavior/profiles/": {"get": {"summary": "List account behavior baselines"}},
                    "/api/graph/graph/": {"get": {"summary": "Return the account transaction graph"}},
                    "/api/graph/clusters/": {"get": {"summary": "Return suspicious connected clusters"}},
                    "/api/investigations/cases/": {"get": {"summary": "List investigation cases"}, "post": {"summary": "Create a case"}},
                    "/api/investigations/cases/from-findings/": {"post": {"summary": "Create a case from selected findings"}},
                    "/api/reports/generate/": {"post": {"summary": "Generate a PDF or CSV report"}},
                },
            }
        )


class HealthView(APIView):
    permission_classes = [AllowAny]

    def get(self, request):
        from apps.detection.models import FraudFinding, RiskScore
        from apps.investigations.models import InvestigationCase
        from apps.transactions.models import Transaction

        try:
            payload = {
                "status": "ok",
                "version": "1.0.0",
                "mode": settings.FRAUDLENS_MODE,
                "live_data_enabled": settings.FRAUDLENS_ENABLE_LIVE_DATA,
                "checks": {"database": "ok"},
                "transaction_count": Transaction.objects.count(),
                "finding_count": FraudFinding.objects.count(),
                "high_risk_count": RiskScore.objects.filter(risk_score__gte=settings.FRAUDLENS_HIGH_RISK_THRESHOLD).count(),
                "case_count": InvestigationCase.objects.count(),
            }
        except Exception:
            payload = {
                "status": "degraded",
                "version": "1.0.0",
                "mode": settings.FRAUDLENS_MODE,
                "live_data_enabled": settings.FRAUDLENS_ENABLE_LIVE_DATA,
                "checks": {"database": "unavailable"},
            }
            return Response(payload, status=503)
        return Response(payload)


class AuditLogViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = AuditLog.objects.select_related("user", "organization").all()
    serializer_class = AuditLogSerializer
    permission_classes = [IsAdminRole]
    search_fields = ["action", "content_type_label", "object_id"]
    ordering_fields = ["created_at", "action"]

    def get_queryset(self):
        queryset = super().get_queryset()
        organization = request_organization(self.request)
        if organization:
            queryset = queryset.filter(organization_id=organization)
        return queryset


class GlobalSearchView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        term = (request.query_params.get("q") or "").strip()
        if len(term) < 2:
            return Response({"detail": "Query must contain at least 2 characters"}, status=400)
        organization = request_organization(request)
        if not organization:
            return Response({"detail": "No organization context"}, status=400)

        from apps.accounts.models import User
        from apps.detection.models import FraudFinding
        from apps.investigations.models import InvestigationCase
        from apps.reports.models import Report
        from apps.transactions.models import FinancialAccount, Transaction

        query = Q(id__icontains=term)
        for field in ("transaction_id", "counterparty_reference", "description", "location"):
            query |= Q(**{f"{field}__icontains": term})
        transactions = Transaction.objects.filter(organization_id=organization).filter(query).order_by("-timestamp")[:20]
        findings = FraudFinding.objects.filter(organization_id=organization, title__icontains=term).order_by("-detected_at")[:20]
        cases = InvestigationCase.objects.filter(organization_id=organization, title__icontains=term).order_by("-opened_at")[:20]
        accounts = FinancialAccount.objects.filter(organization_id=organization, account_holder__icontains=term)[:20]
        reports = Report.objects.filter(organization_id=organization, title__icontains=term).order_by("-created_at")[:20]
        users = User.objects.filter(organization_id=organization, username__icontains=term)[:20] if request.user.is_admin_role else []
        return Response(
            {
                "transactions": [{"id": item.id, "transaction_id": item.transaction_id, "amount": float(item.amount)} for item in transactions],
                "findings": [{"id": item.id, "title": item.title, "kind": item.kind} for item in findings],
                "cases": [{"id": item.id, "case_id": item.case_id, "title": item.title} for item in cases],
                "accounts": [{"id": item.id, "holder": item.account_holder} for item in accounts],
                "reports": [{"id": item.id, "title": item.title} for item in reports],
                "users": [{"id": item.id, "username": item.username} for item in users],
            }
        )


def permission_denied(request, exception, template_name="403.html"):
    return render(request, template_name, {"page_title": "Access denied"}, status=403)


def page_not_found(request, exception, template_name="404.html"):
    return render(request, template_name, {"page_title": "Page not found"}, status=404)


def server_error(request, template_name="500.html"):
    return render(request, template_name, {"page_title": "Server error"}, status=500)
