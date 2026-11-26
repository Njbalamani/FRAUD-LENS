from django.conf import settings

from .utils import mask_identifier


def fraudlens_context(request):
    user = getattr(request, "user", None)
    authenticated = bool(user and getattr(user, "is_authenticated", False))
    organization = getattr(user, "organization", None) if authenticated else None
    role = getattr(user, "get_role_display", None)
    return {
        "fraudlens_mode": settings.FRAUDLENS_MODE,
        "fraudlens_live_data": settings.FRAUDLENS_ENABLE_LIVE_DATA,
        "fraudlens_author": "n j bala manikantan",
        "fraudlens_version": "1.0.0",
        "fraudlens_organization": organization.name if organization else "No organization",
        "fraudlens_role": role() if role and authenticated else ("Administrator" if authenticated else "Anonymous"),
    }


__all__ = ["fraudlens_context", "mask_identifier"]
