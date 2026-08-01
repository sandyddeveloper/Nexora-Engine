"""Custom exception definitions and secure global DRF exception handling."""

import logging

from django.core.exceptions import ObjectDoesNotExist
from django.core.exceptions import ValidationError as DjangoValidationError
from django.db import IntegrityError
from django.http import Http404
from rest_framework import status
from rest_framework.exceptions import (
    AuthenticationFailed,
    NotAuthenticated,
    PermissionDenied,
)
from rest_framework.exceptions import ValidationError as DRFValidationError
from rest_framework.response import Response
from rest_framework.views import exception_handler

from core.responses import _base_payload

logger = logging.getLogger("nexora.exceptions")


class NexoraError(Exception):
    """Base exception for Nexora Engine."""


class ValidationError(NexoraError):
    """Raised when request data is invalid."""


def custom_exception_handler(exc, context=None):
    """Return a standardized, sanitized API response for all exception types.

    Masks sensitive internal database strings and stack traces in non-DEBUG production mode.
    """
    if isinstance(exc, DRFValidationError):
        return Response(
            _base_payload(False, "Validation failed.", data={}, errors=exc.detail),
            status=status.HTTP_400_BAD_REQUEST,
        )

    if isinstance(exc, (DjangoValidationError, ValidationError)):
        detail = exc.message_dict if hasattr(exc, "message_dict") else {"detail": str(exc)}
        return Response(
            _base_payload(False, "Validation failed.", data={}, errors=detail),
            status=status.HTTP_400_BAD_REQUEST,
        )

    if isinstance(exc, (Http404, ObjectDoesNotExist)):
        return Response(
            _base_payload(False, "Resource not found.", data={}, errors={"detail": "The requested resource was not found."}),
            status=status.HTTP_404_NOT_FOUND,
        )

    if isinstance(exc, IntegrityError):
        logger.error("Database integrity error: %s", exc, exc_info=True)
        return Response(
            _base_payload(
                False,
                "Database constraint error occurred.",
                data={},
                errors={"detail": "The operation violated a database constraint or unique rule."},
            ),
            status=status.HTTP_400_BAD_REQUEST,
        )

    if isinstance(exc, AuthenticationFailed):
        return Response(
            _base_payload(
                False, "Authentication failed.", data={}, errors={"detail": str(exc)}
            ),
            status=status.HTTP_401_UNAUTHORIZED,
        )

    if isinstance(exc, (PermissionDenied, NotAuthenticated)):
        return Response(
            _base_payload(
                False, "Permission denied.", data={}, errors={"detail": str(exc)}
            ),
            status=status.HTTP_403_FORBIDDEN,
        )

    # Internal server errors & unhandled application exceptions (masked safely)
    logger.exception("Internal server exception: %s", exc, exc_info=True)
    response = exception_handler(exc, context)
    if response is not None:
        return response

    return Response(
        _base_payload(
            False,
            "An unexpected internal error occurred.",
            data={},
            errors={"detail": "An internal server error occurred. Please contact system administration if the issue persists."},
        ),
        status=status.HTTP_500_INTERNAL_SERVER_ERROR,
    )
