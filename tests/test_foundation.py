from django.core.exceptions import (
    ObjectDoesNotExist,
)
from django.core.exceptions import ValidationError as DjangoValidationError
from django.db import IntegrityError
from django.test import SimpleTestCase
from rest_framework import status
from rest_framework.exceptions import (
    AuthenticationFailed,
)
from rest_framework.exceptions import PermissionDenied as DRFPermissionDenied
from rest_framework.exceptions import ValidationError as DRFValidationError

from apps.common.models import BaseModel
from core.exceptions import NexoraError, custom_exception_handler
from core.pagination import paginate_queryset


class FoundationTests(SimpleTestCase):
    def test_paginate_queryset_returns_standard_pagination_metadata(self):
        queryset = list(range(1, 26))

        result = paginate_queryset(queryset, page_size=10, page=1)

        self.assertEqual(result["data"], list(range(1, 11)))
        self.assertEqual(result["pagination"]["page"], 1)
        self.assertEqual(result["pagination"]["page_size"], 10)
        self.assertEqual(result["pagination"]["total_records"], 25)
        self.assertEqual(result["pagination"]["total_pages"], 3)
        self.assertTrue(result["pagination"]["next"])
        self.assertFalse(result["pagination"]["previous"])

    def test_custom_exception_handler_returns_standard_response(self):
        response = custom_exception_handler(
            DRFValidationError({"detail": "bad data"}), None
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertFalse(response.data["success"])
        self.assertEqual(response.data["message"], "Validation failed.")
        self.assertIn("detail", response.data["errors"])

    def test_custom_exception_handler_handles_django_validation(self):
        response = custom_exception_handler(DjangoValidationError("invalid"), None)

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(response.data["message"], "Validation failed.")

    def test_custom_exception_handler_handles_custom_exception(self):
        response = custom_exception_handler(NexoraError("custom issue"), None)

        self.assertEqual(response.status_code, status.HTTP_500_INTERNAL_SERVER_ERROR)
        self.assertEqual(response.data["message"], "An unexpected error occurred.")

    def test_custom_exception_handler_handles_database_errors(self):
        integrity_response = custom_exception_handler(
            IntegrityError("duplicate key"), None
        )
        missing_response = custom_exception_handler(ObjectDoesNotExist("missing"), None)

        self.assertEqual(integrity_response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(missing_response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_basemodel_contains_expected_fields(self):
        self.assertTrue(BaseModel._meta.abstract)
        field_names = {field.name for field in BaseModel._meta.fields}
        self.assertIn("created_at", field_names)
        self.assertIn("updated_at", field_names)
        self.assertIn("is_active", field_names)

    def test_authentication_and_permission_errors_use_expected_statuses(self):
        auth_response = custom_exception_handler(
            AuthenticationFailed("bad token"), None
        )
        perm_response = custom_exception_handler(DRFPermissionDenied("no access"), None)

        self.assertEqual(auth_response.status_code, status.HTTP_401_UNAUTHORIZED)
        self.assertEqual(perm_response.status_code, status.HTTP_403_FORBIDDEN)
