from django.conf import settings
from django.contrib.auth.decorators import login_required
from django.db.models import Avg, Count
from django.db.models.functions import TruncDate
from django.shortcuts import render

from apps.core.utils import request_organization
from apps.detection.models import DetectionRun, FraudFinding, ModelPerformance, RiskScore
from apps.graph.services import build_graph
from apps.investigations.models import InvestigationCase
from apps.reports.models import Report
from apps.transactions.models import FinancialAccount, Transaction


def scoped(request):
    return request_organization(request)


@login_required
def dashboard(request):
    organization = scoped(request)
    transactions = Transaction.objects.all()
    findings = FraudFinding.objects.all()
    cases = InvestigationCase.objects.all()
    if organization:
        transactions = transactions.filter(organization_id=organization)
        findings = findings.filter(organization_id=organization)
        cases = cases.filter(organization_id=organization)
    risk_scores = RiskScore.objects.filter(organization_id=organization) if organization else RiskScore.objects.none()
    recent_findings = findings.select_related("transaction").order_by("-detected_at")[:8]
    risk_distribution = list(risk_scores.values("risk_level").annotate(count=Count("id")))
    risk_trend = list(
        risk_scores.annotate(day=TruncDate("computed_at"))
        .values("day")
        .annotate(count=Count("id"), average=Avg("risk_score"))
        .order_by("day")[:14]
    )
    latest_run = DetectionRun.objects.filter(organization_id=organization).order_by("-started_at").first() if organization else None
    context = {
        "section": "dashboard",
        "title": "Fraud Intelligence Overview",
        "account_count": FinancialAccount.objects.filter(organization_id=organization).count() if organization else 0,
        "transaction_count": transactions.count(),
        "finding_count": findings.count(),
        "high_risk_count": risk_scores.filter(risk_score__gte=settings.FRAUDLENS_HIGH_RISK_THRESHOLD).count(),
        "open_case_count": cases.filter(status__in=["open", "investigating", "escalated"]).count(),
        "report_count": Report.objects.filter(organization_id=organization).count() if organization else 0,
        "recent_findings": recent_findings,
        "risk_distribution": risk_distribution,
        "risk_trend": risk_trend,
        "latest_run": latest_run,
        "average_risk": round(risk_scores.aggregate(value=Avg("risk_score"))["value"] or 0, 1),
        "risk_threshold": settings.FRAUDLENS_HIGH_RISK_THRESHOLD,
        "mode": "Synthetic demonstration data",
    }
    return render(request, "dashboard.html", context)


@login_required
def transactions_view(request):
    organization = scoped(request)
    queryset = Transaction.objects.select_related("account", "risk_score").all()
    if organization:
        queryset = queryset.filter(organization_id=organization)
    context = {
        "section": "transactions",
        "title": "Transactions",
        "transactions": queryset.order_by("-timestamp")[:250],
        "count": queryset.count(),
        "max_upload_mb": settings.FRAUDLENS_MAX_UPLOAD_MB,
    }
    return render(request, "transactions.html", context)


@login_required
def network_view(request):
    organization = scoped(request)
    payload = build_graph(organization, days=30, limit=250) if organization else {"graph": {"nodes": [], "edges": [], "stats": {}}}
    context = {
        "section": "network",
        "title": "Transaction Network",
        "graph": payload["graph"],
        "stats": payload["graph"]["stats"],
    }
    return render(request, "network.html", context)


@login_required
def investigations_view(request):
    organization = scoped(request)
    queryset = InvestigationCase.objects.select_related("assigned_to").prefetch_related("findings").all()
    findings = FraudFinding.objects.all()
    if organization:
        queryset = queryset.filter(organization_id=organization)
        findings = findings.filter(organization_id=organization)
    suggested_findings = list(findings.filter(severity__in=["high", "critical"]).order_by("-confidence")[:5])
    context = {
        "section": "investigations",
        "title": "Investigation Center",
        "cases": queryset.order_by("-opened_at")[:250],
        "count": queryset.count(),
        "suggested_findings": suggested_findings,
        "suggested_finding_ids": [finding.id for finding in suggested_findings],
    }
    return render(request, "investigations.html", context)


@login_required
def reports_view(request):
    organization = scoped(request)
    queryset = Report.objects.select_related("created_by").all()
    if organization:
        queryset = queryset.filter(organization_id=organization)
    performance = ModelPerformance.objects.filter(organization_id=organization).order_by("-trained_at").first() if organization else None
    context = {
        "section": "reports",
        "title": "Reports & Model Evaluation",
        "reports": queryset.order_by("-created_at")[:100],
        "count": queryset.count(),
        "performance": performance,
        "report_kinds": Report.KIND_CHOICES,
        "report_formats": Report.FORMAT_CHOICES,
    }
    return render(request, "reports.html", context)
