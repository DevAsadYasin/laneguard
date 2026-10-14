from django.conf import settings
from rest_framework.throttling import ScopedRateThrottle


class ImproperlyConfiguredThrottle(Exception):
    pass


class EnvScopedRateThrottle(ScopedRateThrottle):
    def get_rate(self):
        rates = settings.REST_FRAMEWORK.get("DEFAULT_THROTTLE_RATES", {})
        self.THROTTLE_RATES = rates
        if not getattr(self, "scope", None):
            return None
        try:
            return rates[self.scope]
        except KeyError as exc:
            msg = (
                f"No default throttle rate set for '{self.scope}' scope. "
                "Set it in .env / REST_FRAMEWORK['DEFAULT_THROTTLE_RATES']."
            )
            raise ImproperlyConfiguredThrottle(msg) from exc

    def allow_request(self, request, view):
        if getattr(view, "throttle_scope", None) in (None, "", "health"):
            return True
        return super().allow_request(request, view)
