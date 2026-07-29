"""Tests for Password Management API endpoints.

Includes change-password, forgot-password, and reset-password.
"""

from django.contrib.auth import get_user_model
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from apps.accounts import services

User = get_user_model()


class PasswordManagementAPITestCase(APITestCase):
    """Test suite for password management APIs."""

    def setUp(self):
        self.change_password_url = reverse("accounts:change-password")
        self.forgot_password_url = reverse("accounts:forgot-password")
        self.reset_password_url = reverse("accounts:reset-password")

        self.old_password = "OldPassword@123"
        self.new_password = "NewPassword@123"
        self.user = services.create_user(
            email="pass@example.com",
            password=self.old_password,
            first_name="Pass",
            last_name="User",
        )

        tokens = services.generate_tokens(user=self.user)
        self.access_token = tokens["access"]

    # ── Change Password Tests ────────────────────────────────

    def test_change_password_success(self):
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {self.access_token}")
        response = self.client.post(
            self.change_password_url,
            {
                "current_password": self.old_password,
                "new_password": self.new_password,
                "confirm_password": self.new_password,
            },
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.data["success"])
        self.assertEqual(response.data["message"], "Password changed successfully.")

        # Verify new password works for authentication
        authenticated = services.authenticate_user(
            email="pass@example.com", password=self.new_password
        )
        self.assertIsNotNone(authenticated)

    def test_change_password_wrong_current_password(self):
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {self.access_token}")
        response = self.client.post(
            self.change_password_url,
            {
                "current_password": "WrongPassword@999",
                "new_password": self.new_password,
                "confirm_password": self.new_password,
            },
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertFalse(response.data["success"])

    def test_change_password_same_password_rejected(self):
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {self.access_token}")
        response = self.client.post(
            self.change_password_url,
            {
                "current_password": self.old_password,
                "new_password": self.old_password,
                "confirm_password": self.old_password,
            },
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertFalse(response.data["success"])

    def test_change_password_mismatch_rejected(self):
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {self.access_token}")
        response = self.client.post(
            self.change_password_url,
            {
                "current_password": self.old_password,
                "new_password": self.new_password,
                "confirm_password": "DifferentPassword@999",
            },
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertFalse(response.data["success"])

    def test_change_password_weak_new_password_rejected(self):
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {self.access_token}")
        response = self.client.post(
            self.change_password_url,
            {
                "current_password": self.old_password,
                "new_password": "123",
                "confirm_password": "123",
            },
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertFalse(response.data["success"])

    def test_change_password_unauthenticated_rejected(self):
        response = self.client.post(
            self.change_password_url,
            {
                "current_password": self.old_password,
                "new_password": self.new_password,
                "confirm_password": self.new_password,
            },
        )
        self.assertIn(
            response.status_code,
            [status.HTTP_401_UNAUTHORIZED, status.HTTP_403_FORBIDDEN],
        )

    # ── Forgot Password Tests ────────────────────────────────

    def test_forgot_password_existing_email(self):
        response = self.client.post(
            self.forgot_password_url, {"email": "pass@example.com"}
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.data["success"])
        self.assertEqual(
            response.data["message"],
            "If an account exists, a password reset link has been sent.",
        )

    def test_forgot_password_non_existing_email(self):
        response = self.client.post(
            self.forgot_password_url, {"email": "ghost@example.com"}
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.data["success"])
        # Same exact message to prevent email enumeration
        self.assertEqual(
            response.data["message"],
            "If an account exists, a password reset link has been sent.",
        )

    def test_forgot_password_invalid_email_format(self):
        response = self.client.post(
            self.forgot_password_url, {"email": "invalid-email-string"}
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertFalse(response.data["success"])

    # ── Reset Password Tests ─────────────────────────────────

    def test_reset_password_success(self):
        token = services.generate_reset_token(self.user)
        response = self.client.post(
            self.reset_password_url,
            {
                "token": token,
                "new_password": self.new_password,
                "confirm_password": self.new_password,
            },
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.data["success"])
        self.assertEqual(response.data["message"], "Password reset successfully.")

        # Verify user can login with new password
        authenticated = services.authenticate_user(
            email="pass@example.com", password=self.new_password
        )
        self.assertIsNotNone(authenticated)

    def test_reset_password_reused_token_rejected(self):
        token = services.generate_reset_token(self.user)
        # First reset succeeds
        self.client.post(
            self.reset_password_url,
            {
                "token": token,
                "new_password": self.new_password,
                "confirm_password": self.new_password,
            },
        )

        # Second reset attempt with same token must fail
        response = self.client.post(
            self.reset_password_url,
            {
                "token": token,
                "new_password": "AnotherPassword@999",
                "confirm_password": "AnotherPassword@999",
            },
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertFalse(response.data["success"])

    def test_reset_password_invalid_token_rejected(self):
        response = self.client.post(
            self.reset_password_url,
            {
                "token": "invalid.reset.token.string",
                "new_password": self.new_password,
                "confirm_password": self.new_password,
            },
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertFalse(response.data["success"])

    def test_reset_password_mismatch_rejected(self):
        token = services.generate_reset_token(self.user)
        response = self.client.post(
            self.reset_password_url,
            {
                "token": token,
                "new_password": self.new_password,
                "confirm_password": "DifferentPass@999",
            },
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertFalse(response.data["success"])

    def test_reset_password_weak_password_rejected(self):
        token = services.generate_reset_token(self.user)
        response = self.client.post(
            self.reset_password_url,
            {
                "token": token,
                "new_password": "123",
                "confirm_password": "123",
            },
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertFalse(response.data["success"])
