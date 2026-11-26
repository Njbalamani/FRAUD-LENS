from celery import shared_task

from apps.accounts.models import Organization
from apps.core.middleware import audit_context

from .services import rebuild_profiles


@shared_task(name="fraudlens.rebuild_behavior_profiles")
def rebuild_behavior_profiles_task(organization_id=None, days=None):
    if organization_id:
        organizations = [Organization.objects.get(pk=organization_id)]
    else:
        organizations = list(Organization.objects.all())
    total = 0
    for organization in organizations:
        with audit_context(path="celery:behavior"):
            total += len(rebuild_profiles(organization, days=days))
    return {"organizations": len(organizations), "profiles_rebuilt": total}
