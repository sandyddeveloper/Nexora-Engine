"""Tests for Email Verification API endpoints.

Includes verify-email, resend-verification, and login verification enforcement.
"""

from django.contrib.auth import get_user_model
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from apps.accounts import services

User = get_user_model()


class EmailVerificationAPITestCase(APITestCase):
    """Test suite for email verification flow and login rules."""

    def setUp(self):
        self.register_url = reverse("accounts:register")
        self.login_url = reverse("accounts:login")
        self.verify_url = reverse("accounts:verify-email")
        self.resend_url = reverse("accounts:resend-verification")

        self.password = "StrongPassword@123"

        # Register unverified user via registration endpoint
        reg_payload = {
            "email": "unverified@example.com",
            "password": self.password,
            "confirm_password": self.password,
            "first_name": "Unverified",
            "last_name": "User",
        }
        self.client.post(self.register_url, reg_payload)
        self.user = User.objects.get(email="unverified@example.com")

    # ── Verification Tests ───────────────────────────────────

    def test_registration_creates_unverified_user(self):
        self.assertFalse(self.user.is_email_verified)
        self.assertIsNone(self.user.email_verified_at)

    def test_successful_email_verification(self):
        token = services.generate_email_verification_token(self.user)
        response = self.client.post(self.verify_url, {"token": token})

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.data["success"])
        self.assertEqual(response.data["message"], "Email verified successfully.")

        self.user.refresh_from_db()
        self.assertTrue(self.user.is_email_verified)
        self.assertIsNotNone(self.user.email_verified_at)

    def test_invalid_token_rejected(self):
        response = self.client.post(
            self.verify_url, {"token": "invalid.verification.token"}
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertFalse(response.data["success"])

    def test_expired_token_rejected(self):
        token = services.generate_email_verification_token(self.user)
        # Verify with max_age=-1 to simulate expiration
        success, message = services.verify_email(token=token, max_age=-1)
        self.assertFalse(success)
        self.assertEqual(message, "Verification token has expired.")

    def test_reused_token_already_verified_rejected(self):
        token = services.generate_email_verification_token(self.user)
        # First verification succeeds
        self.client.post(self.verify_url, {"token": token})

        # Second verification attempt with same token fails
        response = self.client.post(self.verify_url, {"token": token})
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertFalse(response.data["success"])

    # ── Resend Verification Tests ────────────────────────────

    def test_resend_verification_unverified_email(self):
        response = self.client.post(
            self.resend_url, {"email": "unverified@example.com"}
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.data["success"])
        self.assertEqual(
            response.data["message"],
            "If the account requires verification, a new verification "
            "email has been sent.",
        )

    def test_resend_verification_already_verified_email(self):
        token = services.generate_email_verification_token(self.user)
        self.client.post(self.verify_url, {"token": token})

        response = self.client.post(
            self.resend_url, {"email": "unverified@example.com"}
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.data["success"])
        # Same message to prevent account enumeration
        self.assertEqual(
            response.data["message"],
            "If the account requires verification, a new verification "
            "email has been sent.",
        )

    def test_resend_verification_non_existing_email(self):
        response = self.client.post(self.resend_url, {"email": "ghost@example.com"})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.data["success"])
        # Same message to prevent account enumeration
        self.assertEqual(
            response.data["message"],
            "If the account requires verification, a new verification "
            ""
            "email has been sent.",
        )

    # ── Login Verification Enforcement Tests ─────────────────

    def test_login_before_verification_rejected(self):
        response = self.client.post(
            self.login_url,
            {"email": "unverified@example.com", "password": self.password},
        )
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
        self.assertFalse(response.data["success"])
        self.assertEqual(
            response.data["message"],
            "Please verify your email address before logging in.",
        )

    def test_login_after_verification_successful(self):
        token = services.generate_email_verification_token(self.user)
        self.client.post(self.verify_url, {"token": token})

        response = self.client.post(
            self.login_url,
            {"email": "unverified@example.com", "password": self.password},
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.data["success"])
        self.assertEqual(response.data["message"], "Login successful.")
        self.assertIn("access", response.data["data"])
