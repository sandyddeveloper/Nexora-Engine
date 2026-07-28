"""Standard response helpers."""

from django.http import JsonResponse


def success_response(data=None, status=200):
    """Build a standard success payload."""
    payload = {"success": True}
    if data is not None:
        payload["data"] = data
    return JsonResponse(payload, status=status)


def error_response(message, status=400):
    """Build a standard error payload."""
    return JsonResponse({"success": False, "error": message}, status=status)
