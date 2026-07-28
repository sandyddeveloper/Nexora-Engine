import sys
from datetime import datetime, timezone

from django.conf import settings
from django.db import connection
from drf_spectacular.utils import OpenApiResponse, extend_schema
from rest_framework.decorators import api_view

from core.responses import success_response
from core.version import VERSION


def _check_database() -> str:
    try:
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1")
        return "connected"
    except Exception:
        return "disconnected"


@extend_schema(
    tags=["Health"],
    summary="Health check",
    description=(
        "Returns a lightweight status payload for monitoring " "and deployment checks."
    ),
    responses={200: OpenApiResponse(description="Application is healthy")},
)
@api_view(["GET"])
def health_check(request):
    """Return a lightweight health payload for monitoring systems."""
    database_status = _check_database()
    return success_response(
        message="Application is healthy",
        data={
            "status": "healthy" if database_status == "connected" else "degraded",
            "database": database_status,
            "redis": "not_configured",
            "timestamp": datetime.now(timezone.utc).isoformat(),
        },
    )


@extend_schema(
    tags=["Health"],
    summary="Version info",
    description="Returns application and runtime version information.",
    responses={200: OpenApiResponse(description="Version details returned")},
)
@api_view(["GET"])
def version_info(request):
    """Return version and environment details."""
    return success_response(
        message="Version information retrieved successfully.",
        data={
            "application": "Nexora Engine",
            "version": VERSION,
            "environment": settings.ENVIRONMENT,
            "python": sys.version.split()[0],
            "django": settings.DATABASES["default"]["ENGINE"].split(".")[-1],
        },
    )
