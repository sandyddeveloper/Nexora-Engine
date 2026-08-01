"""Standard API response helpers."""

from rest_framework import status as drf_status
from rest_framework.response import Response


def _base_payload(success: bool, message: str, data=None, errors=None):
    payload = {
        "success": success,
        "message": message,
        "data": {} if data is None else data,
    }
    payload["errors"] = errors if errors is not None else None
    return payload


def success_response(
    message: str = "Request successful.",
    data=None,
    status: int = drf_status.HTTP_200_OK,
):
    return Response(_base_payload(True, message, data=data, errors=None), status=status)


def created_response(message: str = "Resource created successfully.", data=None):
    return Response(
        _base_payload(True, message, data=data, errors=None),
        status=drf_status.HTTP_201_CREATED,
    )


def updated_response(message: str = "Resource updated successfully.", data=None):
    return Response(
        _base_payload(True, message, data=data, errors=None),
        status=drf_status.HTTP_200_OK,
    )


def deleted_response(message: str = "Resource deleted successfully."):
    return Response(status=drf_status.HTTP_204_NO_CONTENT)


def list_response(
    items,
    message: str = "List retrieved successfully.",
    page: int = 1,
    page_size: int = 20,
    total_records: int = 0,
    total_pages: int = 0,
    next: bool = False,
    previous: bool = False,
    status: int = drf_status.HTTP_200_OK,
):
    payload = _base_payload(True, message, data=items, errors=None)
    payload["pagination"] = {
        "page": page,
        "page_size": page_size,
        "total_records": total_records,
        "total_pages": total_pages,
        "next": next,
        "previous": previous,
    }
    return Response(payload, status=status)


def validation_error_response(errors, message: str = "Validation failed."):
    return Response(
        _base_payload(False, message, data={}, errors=errors),
        status=drf_status.HTTP_400_BAD_REQUEST,
    )


def unauthorized_response(
    message: str = "Authentication credentials were not provided.",
    errors=None,
):
    return Response(
        _base_payload(False, message, data={}, errors=errors),
        status=drf_status.HTTP_401_UNAUTHORIZED,
    )


def forbidden_response(message: str = "Permission denied.", errors=None):
    return Response(
        _base_payload(False, message, data={}, errors=errors),
        status=drf_status.HTTP_403_FORBIDDEN,
    )


def not_found_response(message: str = "Resource not found.", errors=None):
    return Response(
        _base_payload(False, message, data={}, errors=errors),
        status=drf_status.HTTP_404_NOT_FOUND,
    )


def server_error_response(message: str = "An unexpected error occurred.", errors=None):
    return Response(
        _base_payload(False, message, data={}, errors=errors),
        status=drf_status.HTTP_500_INTERNAL_SERVER_ERROR,
    )
