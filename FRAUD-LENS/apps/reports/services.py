import csv
import io
import json
from datetime import datetime, timezone as dt_timezone

from django.conf import settings
from django.db.models import Count
from django.utils import timezone

from apps.accounts.models import Organization
from apps.core.middleware import suspend_audit
from apps.detection.models import FraudFinding, RiskScore
from apps.investigations.models import InvestigationCase
from apps.transactions.models import Transaction

from .models import Report


def build_summary(organization, days=30):
    cutoff = timezone.now() - timezone.timedelta(days=days)
    transactions = Transaction.objects.filter(organization=organization, timestamp__gte=cutoff)
    transaction_count = transactions.count()
    total_value = sum(float(value or 0) for value in transactions.values_list("amount", flat=True)[:10000])
    findings = FraudFinding.objects.filter(organization=organization, detected_at__gte=cutoff)
    severity_counts = dict(findings.values_list("severity").annotate(count=Count("id")))
    case_queryset = InvestigationCase.objects.filter(organization=organization, opened_at__gte=cutoff)
    open_cases = case_queryset.filter(status__in=["open", "investigating", "escalated"]).count()
    top_findings = list(findings.order_by("-confidence").values("title", "kind", "severity", "confidence")[:10])
    return {
        "generated_at": timezone.now().isoformat(),
        "organization": organization.name,
        "window_days": days,
        "transaction_count": transaction_count,
        "transaction_value": round(total_value, 2),
        "finding_count": findings.count(),
        "high_risk_count": RiskScore.objects.filter(
            organization=organization,
            risk_score__gte=settings.FRAUDLENS_HIGH_RISK_THRESHOLD,
            computed_at__gte=cutoff,
        ).count(),
        "case_count": case_queryset.count(),
        "open_cases": open_cases,
        "severity_counts": severity_counts,
        "top_findings": top_findings,
        "disclaimer": "Synthetic demonstration data. No real accounts or transactions were used.",
    }


def render_report(summary, file_format, transactions=None, findings=None, cases=None):
    if file_format == "json":
        payload = {
            "summary": summary,
            "transactions": [
                {
                    "transaction_id": item.transaction_id,
                    "amount": float(item.amount),
                    "timestamp": item.timestamp.isoformat(),
                    "type": item.transaction_type,
                }
                for item in (transactions or [])[:500]
            ],
            "findings": [
                {
                    "title": item.title,
                    "severity": item.severity,
                    "confidence": item.confidence,
                    "kind": item.kind,
                }
                for item in (findings or [])[:500]
            ],
            "cases": [
                {"case_id": item.case_id, "title": item.title, "status": item.status, "priority": item.priority}
                for item in (cases or [])[:500]
            ],
        }
        return json.dumps(payload, indent=2, default=str).encode("utf-8"), "application/json", "json"

    if file_format == "csv":
        output = io.StringIO()
        writer = csv.writer(output)
        writer.writerow(["section", "field", "value"])
        for key, value in summary.items():
            if isinstance(value, (list, dict)):
                value = json.dumps(value, default=str)
            writer.writerow(["summary", key, value])
        for item in (transactions or [])[:1000]:
            writer.writerow(["transaction", item.transaction_id, f"{item.amount} {item.currency}"])
        for item in (findings or [])[:1000]:
            writer.writerow(["finding", item.title, f"{item.severity} ({item.confidence:.1f})"])
        for item in (cases or [])[:1000]:
            writer.writerow(["case", item.case_id, item.status])
        return output.getvalue().encode("utf-8"), "text/csv", "csv"

    try:
        from reportlab.lib.pagesizes import LETTER
        from reportlab.lib.styles import getSampleStyleSheet
        from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer
    except ImportError:
        lines = ["FraudLens Report", f"Generated: {summary['generated_at']}"]
        lines.extend(f"{key}: {value}" for key, value in summary.items() if key != "generated_at")
        return "\n".join(lines).encode("utf-8"), "text/plain", "txt"

    buffer = io.BytesIO()
    document = SimpleDocTemplate(buffer, pagesize=LETTER, title="FraudLens Report")
    styles = getSampleStyleSheet()
    story = [Paragraph("FraudLens Fraud Intelligence Report", styles["Title"]), Spacer(1, 12)]
    story.append(Paragraph(f"Organization: {summary['organization']}", styles["Heading2"]))
    story.append(Paragraph(f"Generated: {summary['generated_at']}", styles["Normal"]))
    story.append(Paragraph(f"Window: last {summary['window_days']} days", styles["Normal"]))
    story.append(Spacer(1, 12))
    for key, value in summary.items():
        if key in {"organization", "generated_at", "window_days"}:
            continue
        if isinstance(value, (dict, list)):
            value = json.dumps(value, default=str)
        story.append(Paragraph(f"<b>{key.replace('_', ' ').title()}:</b> {value}", styles["BodyText"]))
    story.append(Spacer(1, 12))
    story.append(Paragraph(summary["disclaimer"], styles["Italic"]))
    document.build(story)
    return buffer.getvalue(), "application/pdf", "pdf"


def generate_report(organization, created_by=None, kind="summary", file_format="pdf", title=None, parameters=None):
    if not isinstance(organization, Organization):
        organization = Organization.objects.get(pk=organization)
    parameters = parameters or {}
    days = int(parameters.get("days", 30))
    summary = build_summary(organization, days=days)
    cutoff = timezone.now() - timezone.timedelta(days=days)
    transactions = list(organization.transactions.filter(timestamp__gte=cutoff).order_by("-timestamp")[:500])
    findings = list(FraudFinding.objects.filter(organization=organization, detected_at__gte=cutoff).order_by("-confidence")[:500])
    cases = list(InvestigationCase.objects.filter(organization=organization, opened_at__gte=cutoff).order_by("-opened_at")[:500])
    data, content_type, extension = render_report(summary, file_format, transactions, findings, cases)
    stamp = timezone.now().strftime("%Y%m%d-%H%M%S")
    safe_name = (title or f"FraudLens {kind} report").replace("/", "-")
    with suspend_audit():
        report = Report.objects.create(
            organization=organization,
            created_by=created_by,
            title=safe_name[:180],
            kind=kind,
            file_format=file_format,
            file_name=f"{safe_name}-{stamp}.{extension}",
            file_data=data,
            content_type=content_type,
            summary=summary,
            parameters=parameters,
        )
    return report
