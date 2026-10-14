from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from routing.serializers import AnalyzeRequestSerializer, GeocodeQuerySerializer
from routing.services.analyze import analyze_trip, autocomplete
from routing.services.open_meteo import WeatherError
from routing.services.ors import ORSError
from routing.services.rate_limit import RateLimitExceeded
from routing.throttles import EnvScopedRateThrottle


def _rate_limit_response(exc: RateLimitExceeded) -> Response:
    return Response(
        {
            "detail": str(exc),
            "retry_after": int(exc.retry_after),
        },
        status=status.HTTP_429_TOO_MANY_REQUESTS,
        headers={"Retry-After": str(int(exc.retry_after))},
    )


class HealthView(APIView):
    authentication_classes = []
    permission_classes = []
    throttle_classes = []

    def get(self, request):
        return Response({"status": "ok"})


class ConfigView(APIView):
    authentication_classes = []
    permission_classes = []
    throttle_classes = []

    def get(self, request):
        from django.conf import settings

        hours = int(settings.DEPARTURE_MAX_HOURS_AHEAD)
        return Response(
            {
                "departure_max_hours_ahead": hours,
                "departure_past_grace_minutes": int(settings.DEPARTURE_PAST_GRACE_MINUTES),
                "heatmap_hours": int(settings.HEATMAP_HOURS),
                "weather_forecast_days": int(settings.WEATHER_FORECAST_DAYS),
                "departure_guidance": (
                    "Best ETA weather accuracy is within ~48 hours; "
                    f"planning allowed up to {hours} hours "
                    f"(~{hours / 24:g} days) using Open-Meteo medium-range forecast."
                ),
            }
        )


class GeocodeView(APIView):
    authentication_classes = []
    permission_classes = []
    throttle_classes = [EnvScopedRateThrottle]
    throttle_scope = "geocode"

    def get(self, request):
        ser = GeocodeQuerySerializer(data=request.query_params)
        ser.is_valid(raise_exception=True)
        try:
            results = autocomplete(ser.validated_data["q"])
        except RateLimitExceeded as exc:
            return _rate_limit_response(exc)
        except ORSError as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_502_BAD_GATEWAY)
        return Response({"results": results})


class AnalyzeView(APIView):
    authentication_classes = []
    permission_classes = []
    throttle_classes = [EnvScopedRateThrottle]
    throttle_scope = "analyze"

    def post(self, request):
        ser = AnalyzeRequestSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        data = ser.validated_data
        try:
            result = analyze_trip(
                origin=data["origin"],
                destination=data["destination"],
                departure_at=data["departure_at"],
                load_lbs=data["load_lbs"],
            )
        except RateLimitExceeded as exc:
            return _rate_limit_response(exc)
        except ORSError as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_502_BAD_GATEWAY)
        except WeatherError as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_502_BAD_GATEWAY)
        except Exception as exc:
            return Response(
                {"detail": f"Analyze failed: {exc}"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )
        return Response(result)
