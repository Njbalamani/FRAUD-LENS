from celery import shared_task

from apps.accounts.models import Organization, User
from apps.core.middleware import audit_context

from .services import run_detection


@shared_task(name="fraudlens.run_detection")
def run_detection_task(organization_id, initiated_by_id=None):
    organization = Organization.objects.get(pk=organization_id)
    user = User.objects.filter(pk=initiated_by_id).first() if initiated_by_id else None
    with audit_context(user=user, path="celery:detection"):
        return run_detection(organization, initiated_by=user, force=True)


@shared_task(name="fraudlens.run_detection_for_all_organizations")
def run_detection_for_all_organizations():
    results = []
    for organization in Organization.objects.all():
        with audit_context(path="celery:detection-scheduled"):
            results.append(run_detection(organization, force=True))
    return {
        "organizations": len(results),
        "transactions_analyzed": sum(result["transactions_analyzed"] for result in results),
        "findings_created": sum(result["findings_created"] for result in results),
        "high_risk_count": sum(result["high_risk_count"] for result in results),
    }
