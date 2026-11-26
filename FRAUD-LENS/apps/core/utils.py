import contextvars
import datetime as dt
import json
import uuid
from decimal import Decimal

from django.db.models import Model, QuerySet

SENSITIVE_KEYS = {
    "password",
    "token",
    "secret",
    "authorization",
    "account_number",
    "card_number",
    "iban",
    "device_id",
}


def sanitize(value):
    if isinstance(value, (bytes, bytearray, memoryview)):
        return f"<{len(bytes(value))} bytes>"
    if isinstance(value, (dt.datetime, dt.date, dt.time)):
        return value.isoformat()
    if isinstance(value, Decimal):
        return float(value)
    if isinstance(value, uuid.UUID):
        return str(value)
    if isinstance(value, Model):
        return str(value)
    if isinstance(value, QuerySet):
        return [sanitize(item) for item in value]
    if isinstance(value, dict):
        return {str(key): sanitize(item) for key, item in value.items()}
    if isinstance(value, (list, tuple, set)):
        return [sanitize(item) for item in value]
    return value


def redact_details(details):
    if not isinstance(details, dict):
        return {}
    cleaned = {}
    for key, value in details.items():
        lower = str(key).lower()
        if any(term in lower for term in SENSITIVE_KEYS):
            cleaned[key] = "[REDACTED]"
        else:
            cleaned[key] = sanitize(value)
    return cleaned


def mask_identifier(value, visible=4):
    if value is None or value == "":
        return ""
    text = str(value)
    if len(text) <= visible:
        return "*" * len(text)
    return f"{'*' * (len(text) - visible)}{text[-visible:]}"


def request_organization(request):
    query = getattr(request, "query_params", None)
    if query is None:
        query = getattr(request, "GET", {})
    user = getattr(request, "user", None)
    if not user or not user.is_authenticated:
        return None
    requested = query.get("organization")
    if requested and (user.is_superuser or getattr(user, "role", None) == "admin"):
        try:
            return int(requested)
        except (TypeError, ValueError):
            return None
    return getattr(user, "organization_id", None)


def client_ip(request):
    forwarded = request.META.get("HTTP_X_FORWARDED_FOR", "")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.META.get("REMOTE_ADDR") or None


def safe_float(value, default=0.0):
    try:
        result = float(value)
        return result if result == result and abs(result) != float("inf") else default
    except (TypeError, ValueError):
        return default


def clamp(value, low, high):
    return max(low, min(high, value))


def json_safe_dump(value):
    return json.dumps(sanitize(value), sort_keys=True)
