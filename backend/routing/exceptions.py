from rest_framework import status
from rest_framework.exceptions import Throttled
from rest_framework.response import Response
from rest_framework.views import exception_handler


def custom_exception_handler(exc, context):
    response = exception_handler(exc, context)
    if response is not None and isinstance(exc, Throttled):
        wait = getattr(exc, "wait", None) or 1
        response.data = {
            "detail": (
                f"Too many requests. Please wait {int(wait)}s before trying again."
            ),
            "retry_after": int(wait),
        }
        response.status_code = status.HTTP_429_TOO_MANY_REQUESTS
    return response
