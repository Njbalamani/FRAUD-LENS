from apps.accounts.models import Organization
from apps.core.middleware import suspend_audit
from apps.detection.models import FraudFinding

from .models import InvestigationCase


def create_case_from_findings(organization, finding_ids, created_by=None, title=None, description=None, priority="high", assigned_to=None):
    if not isinstance(organization, Organization):
        organization = Organization.objects.get(pk=organization)
    unique_ids = list(dict.fromkeys(int(value) for value in finding_ids))
    if not unique_ids:
        raise ValueError("At least one finding is required")
    findings = list(FraudFinding.objects.filter(id__in=unique_ids, organization=organization).select_related("transaction"))
    if len(findings) != len(unique_ids):
        raise ValueError("One or more findings do not belong to this organization")
    default_title = "Fraud review: " + findings[0].title
    if len(findings) > 1:
        default_title = f"Fraud review: {findings[0].title} (+{len(findings) - 1} signals)"
    default_description = "\n".join(
        f"- {finding.title} ({finding.severity}, confidence {finding.confidence:.1f})"
        for finding in findings
    )
    with suspend_audit():
        case = InvestigationCase.objects.create(
            organization=organization,
            title=(title or default_title)[:180],
            description=description or default_description,
            priority=priority,
            created_by=created_by,
            assigned_to=assigned_to,
            tags=["auto-suggested" if created_by is None else "analyst-created"],
        )
        case.findings.set(findings)
    case.refresh_from_db()
    return case
