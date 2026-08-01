from django.urls import path

from .views import health_check, version_info

app_name = "health"

urlpatterns = [
    path("health/", health_check, name="health-check"),
    path("version/", version_info, name="version-info"),
]
