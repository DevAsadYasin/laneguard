from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent
ROOT_DIR = BASE_DIR.parent
load_dotenv(ROOT_DIR / ".env")
load_dotenv(BASE_DIR / ".env")

SECRET_KEY = os.getenv("DJANGO_SECRET_KEY", "dev-insecure-change-me")
DEBUG = os.getenv("DJANGO_DEBUG", "true").lower() in ("1", "true", "yes")
ALLOWED_HOSTS = [
    h.strip()
    for h in os.getenv("ALLOWED_HOSTS", "localhost,127.0.0.1").split(",")
    if h.strip()
]

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "rest_framework",
    "corsheaders",
    "routing",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "whitenoise.middleware.WhiteNoiseMiddleware",
    "corsheaders.middleware.CorsMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "config.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

WSGI_APPLICATION = "config.wsgi.application"

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": BASE_DIR / "db.sqlite3",
    }
}

AUTH_PASSWORD_VALIDATORS = []

LANGUAGE_CODE = "en-us"
TIME_ZONE = "UTC"
USE_I18N = True
USE_TZ = True

STATIC_URL = "static/"
STATIC_ROOT = BASE_DIR / "staticfiles"
STORAGES = {
    "default": {
        "BACKEND": "django.core.files.storage.FileSystemStorage",
    },
    "staticfiles": {
        "BACKEND": "whitenoise.storage.CompressedStaticFilesStorage",
    },
}
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

if not DEBUG:
    SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")

RATE_LIMIT_GEOCODE = os.getenv("RATE_LIMIT_GEOCODE", "20/min")
RATE_LIMIT_ANALYZE = os.getenv("RATE_LIMIT_ANALYZE", "6/min")
RATE_LIMIT_DEFAULT = os.getenv("RATE_LIMIT_DEFAULT", "60/min")
ORS_RATE_LIMIT_PER_MINUTE = int(os.getenv("ORS_RATE_LIMIT_PER_MINUTE", "35"))

REST_FRAMEWORK = {
    "DEFAULT_RENDERER_CLASSES": [
        "rest_framework.renderers.JSONRenderer",
    ],
    "UNAUTHENTICATED_USER": None,
    "DEFAULT_THROTTLE_CLASSES": [
        "routing.throttles.EnvScopedRateThrottle",
    ],
    "DEFAULT_THROTTLE_RATES": {
        "geocode": RATE_LIMIT_GEOCODE,
        "analyze": RATE_LIMIT_ANALYZE,
        "default": RATE_LIMIT_DEFAULT,
    },
    "EXCEPTION_HANDLER": "routing.exceptions.custom_exception_handler",
}

_cors = os.getenv(
    "CORS_ORIGINS",
    "http://localhost:5173,http://127.0.0.1:5173",
)
CORS_ALLOWED_ORIGINS = [o.strip() for o in _cors.split(",") if o.strip()]
CORS_ALLOW_CREDENTIALS = False

ORS_API_KEY = os.getenv("ORS_API_KEY", "")
ORS_BASE_URL = os.getenv("ORS_BASE_URL", "https://api.openrouteservice.org")
ORS_ROUTING_PROFILE = os.getenv("ORS_ROUTING_PROFILE", "driving-hgv")
OPEN_METEO_URL = os.getenv(
    "OPEN_METEO_URL",
    "https://api.open-meteo.com/v1/forecast",
)

TRUCK_VEHICLE_TYPE = os.getenv("TRUCK_VEHICLE_TYPE", "hgv")
TRUCK_LENGTH_M = float(os.getenv("TRUCK_LENGTH_M", "16.5"))
TRUCK_WIDTH_M = float(os.getenv("TRUCK_WIDTH_M", "2.55"))
TRUCK_HEIGHT_M = float(os.getenv("TRUCK_HEIGHT_M", "4.0"))
TRUCK_AXLELOAD_T = float(os.getenv("TRUCK_AXLELOAD_T", "11.5"))
TRUCK_TARE_LBS = float(os.getenv("TRUCK_TARE_LBS", "30000"))
TRUCK_HAZMAT = os.getenv("TRUCK_HAZMAT", "false").lower() in ("1", "true", "yes")

DEPARTURE_MAX_HOURS_AHEAD = int(os.getenv("DEPARTURE_MAX_HOURS_AHEAD", "168"))
DEPARTURE_PAST_GRACE_MINUTES = int(os.getenv("DEPARTURE_PAST_GRACE_MINUTES", "5"))
WEATHER_ETA_BUFFER_HOURS = int(os.getenv("WEATHER_ETA_BUFFER_HOURS", "24"))
WEATHER_FORECAST_DAYS = int(os.getenv("WEATHER_FORECAST_DAYS", "8"))
HEATMAP_HOURS = int(os.getenv("HEATMAP_HOURS", "48"))
