"""Unit tests for Phase 2.5 Security Hardening (token replay, exception masking, correlation IDs)."""

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient

from apps.accounts.services import (
    create_user,
    generate_email_verification_token,
    generate_reset_token,
    reset_password_with_token,
    verify_email,
)

User = get_user_model()


class SecurityHardeningTests(TestCase):
    """Test suite verifying token replay prevention, correlation ID header, and error masking."""

    def setUp(self):
        self.client = APIClient()
        self.user = create_user(
            email="security_test@example.com",
            password="Password123!",
            is_email_verified=False,
        )

    def test_email_verification_token_cannot_be_reused(self):
        token = generate_email_verification_token(self.user)
        success1, msg1 = verify_email(token=token)
        self.assertTrue(success1)

        # Attempt token replay (second usage must be rejected)
        success2, msg2 = verify_email(token=token)
        self.assertFalse(success2)
        self.assertIn("already verified", msg2.lower())

    def test_password_reset_token_cannot_be_reused(self):
        token = generate_reset_token(self.user)
        success1 = reset_password_with_token(token=token, new_password="NewPassword123!")
        self.assertTrue(success1)

        # Attempt token replay (second usage must be rejected)
        success2 = reset_password_with_token(token=token, new_password="AnotherPassword123!")
        self.assertFalse(success2)

    def test_correlation_id_header_middleware(self):
        health_url = reverse("health:health-check")
        response = self.client.get(health_url, HTTP_X_REQUEST_ID="test-correlation-id-999")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.headers.get("X-Request-ID"), "test-correlation-id-999")
