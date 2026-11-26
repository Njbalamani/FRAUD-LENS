from django.apps import apps
from django.db.models.signals import post_delete, post_save
from django.dispatch import receiver

from .middleware import get_audit_context
from .models import AuditLog
from .utils import redact_details, sanitize

AUDITED_MODELS = {
    "organization",
    "user",
    "financialaccount",
    "transaction",
    "transactionimport",
    "detectionrun",
    "fraudfinding",
    "riskscore",
    "investigationcase",
    "caseevidence",
    "casenote",
    "report",
}


def _organization_for(instance):
    organization = getattr(instance, "organization", None)
    if organization is not None:
        return organization
    if getattr(instance, "_meta", None) and instance._meta.model_name == "organization":
        return instance
    user = getattr(instance, "user", None)
    if user is not None:
        return getattr(user, "organization", None)
    return None


def _write_audit(instance, action, details):
    context = get_audit_context()
    if context.get("suspend"):
        return
    AuditLog.objects.create(
        organization=_organization_for(instance),
        user_id=context.get("user_id"),
        action=action,
        content_type_label=f"{instance._meta.app_label}.{instance._meta.model_name}",
        object_id=str(getattr(instance, "pk", "")),
        details=redact_details(details),
        ip_address=context.get("ip_address"),
        path=context.get("path", ""),
    )


@receiver(post_save)
def audit_post_save(sender, instance, created, **kwargs):
    if kwargs.get("raw") or sender._meta.model_name not in AUDITED_MODELS:
        return
    fields = {}
    for field in sender._meta.fields:
        if field.name in {"password", "secret_key"}:
            continue
        fields[field.name] = sanitize(getattr(instance, field.name))
    _write_audit(instance, "create" if created else "update", fields)


@receiver(post_delete)
def audit_post_delete(sender, instance, **kwargs):
    if sender._meta.model_name not in AUDITED_MODELS:
        return
    _write_audit(instance, "delete", {"label": str(instance)})


__all__ = ["apps", "AuditLog"]
