from rest_framework.throttling import SimpleRateThrottle


class FraudLensRateThrottle(SimpleRateThrottle):
    scope = "fraudlens"

    def get_cache_key(self, request, view):
        user = getattr(request, "user", None)
        if user and user.is_authenticated:
            ident = f"user-{user.pk}"
        else:
            ident = f"ip-{self.get_ident(request)}"
        return self.cache_format % {"scope": self.scope, "ident": ident}
