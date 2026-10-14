from datetime import datetime, timedelta, timezone

from django.conf import settings
from rest_framework import serializers


class AnalyzeRequestSerializer(serializers.Serializer):
    origin = serializers.JSONField()
    destination = serializers.JSONField()
    departure_at = serializers.CharField()
    load_lbs = serializers.FloatField(min_value=0)

    def validate_origin(self, value):
        return self._validate_place(value, "origin")

    def validate_destination(self, value):
        return self._validate_place(value, "destination")

    def validate_departure_at(self, value: str) -> str:
        try:
            raw = value.replace("Z", "+00:00")
            dt = datetime.fromisoformat(raw)
        except ValueError as exc:
            raise serializers.ValidationError(
                "departure_at must be a valid ISO datetime"
            ) from exc

        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)

        now = datetime.now(timezone.utc)
        grace = timedelta(minutes=int(settings.DEPARTURE_PAST_GRACE_MINUTES))
        max_ahead = timedelta(hours=int(settings.DEPARTURE_MAX_HOURS_AHEAD))

        if dt < now - grace:
            raise serializers.ValidationError(
                "Departure cannot be in the past. Choose a time from now onward."
            )
        if dt > now + max_ahead:
            hours = int(settings.DEPARTURE_MAX_HOURS_AHEAD)
            days = hours / 24
            day_label = (
                f"{hours} hours"
                if hours < 48
                else f"{hours} hours (~{days:g} days)"
            )
            raise serializers.ValidationError(
                f"Departure must be within the next {day_label} "
                "(limited by the weather forecast window)."
            )
        return dt.isoformat()

    def _validate_place(self, value, field):
        if isinstance(value, str) and value.strip():
            return value.strip()
        if isinstance(value, dict) and "lat" in value and "lng" in value:
            return value
        raise serializers.ValidationError(
            f"{field} must be an address string or {{lat, lng}} object"
        )


class GeocodeQuerySerializer(serializers.Serializer):
    q = serializers.CharField(min_length=2, max_length=200)
