from django.urls import path

from routing.views import AnalyzeView, ConfigView, GeocodeView, HealthView

urlpatterns = [
    path("health/", HealthView.as_view(), name="health"),
    path("config/", ConfigView.as_view(), name="config"),
    path("geocode/", GeocodeView.as_view(), name="geocode"),
    path("routes/analyze/", AnalyzeView.as_view(), name="analyze"),
]
