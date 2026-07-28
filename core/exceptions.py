"""Custom exception definitions and global DRF exception handling."""

import logging

from django.core.exceptions import (
    ObjectDoesNotExist,
)
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
    """Return a standardized API response for all known exception types."""
    if isinstance(exc, DRFValidationError):
        return Response(
            _base_payload(False, "Validation failed.", data={}, errors=exc.detail),
            status=status.HTTP_400_BAD_REQUEST,
        )

    if isinstance(exc, DjangoValidationError):
        return Response(
            _base_payload(
                False, "Validation failed.", data={}, errors={"detail": str(exc)}
            ),
            status=status.HTTP_400_BAD_REQUEST,
        )

    if isinstance(exc, ValidationError):
        return Response(
            _base_payload(
                False, "Validation failed.", data={}, errors={"detail": str(exc)}
            ),
            status=status.HTTP_400_BAD_REQUEST,
        )

    if isinstance(exc, (IntegrityError, ObjectDoesNotExist)):
        return Response(
            _base_payload(
                False,
                "The requested operation could not be completed.",
                data={},
                errors={"detail": str(exc)},
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

    if isinstance(exc, Http404):
        return Response(
            _base_payload(
                False, "Resource not found.", data={}, errors={"detail": str(exc)}
            ),
            status=status.HTTP_404_NOT_FOUND,
        )

    if isinstance(exc, NexoraError):
        logger.exception("Nexora error occurred", exc_info=exc)
        return Response(
            _base_payload(
                False,
                "An unexpected error occurred.",
                data={},
                errors={"detail": str(exc)},
            ),
            status=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )

    if isinstance(exc, (KeyError, LookupError, AttributeError)):
        logger.exception("Unexpected application error", exc_info=exc)
        return Response(
            _base_payload(
                False,
                "An unexpected error occurred.",
                data={},
                errors={"detail": str(exc)},
            ),
            status=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )

    logger.exception("Unhandled exception", exc_info=exc)
    response = exception_handler(exc, context)
    if response is not None:
        return response

    return Response(
        _base_payload(
            False, "An unexpected error occurred.", data={}, errors={"detail": str(exc)}
        ),
        status=status.HTTP_500_INTERNAL_SERVER_ERROR,
    )
