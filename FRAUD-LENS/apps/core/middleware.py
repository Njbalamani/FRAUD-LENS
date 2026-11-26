import contextlib
import contextvars

from apps.core.utils import client_ip

_audit_context = contextvars.ContextVar("fraudlens_audit_context", default={})


def get_audit_context():
    return _audit_context.get()


@contextlib.contextmanager
def audit_context(user=None, path="", ip_address=None, suspend=False):
    token = _audit_context.set(
        {
            "user_id": getattr(user, "id", None),
            "path": path,
            "ip_address": ip_address,
            "suspend": suspend,
        }
    )
    try:
        yield
    finally:
        _audit_context.reset(token)


@contextlib.contextmanager
def suspend_audit():
    current = dict(_audit_context.get())
    current["suspend"] = True
    token = _audit_context.set(current)
    try:
        yield
    finally:
        _audit_context.reset(token)


class AuditContextMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        user = getattr(request, "user", None)
        token = _audit_context.set(
            {
                "user_id": getattr(user, "id", None) if getattr(user, "is_authenticated", False) else None,
                "path": request.path,
                "ip_address": client_ip(request),
                "suspend": False,
            }
        )
        try:
            return self.get_response(request)
        finally:
            _audit_context.reset(token)
