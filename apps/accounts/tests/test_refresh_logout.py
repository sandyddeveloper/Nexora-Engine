"""Tests for Refresh Token and Logout API endpoints."""

from django.contrib.auth import get_user_model
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from apps.accounts import services

User = get_user_model()


class RefreshAndLogoutAPITestCase(APITestCase):
    """Test suite for POST /api/v1/auth/refresh/ and POST /api/v1/auth/logout/."""

    def setUp(self):
        self.refresh_url = reverse("accounts:token-refresh")
        self.logout_url = reverse("accounts:logout")

        self.password = "StrongPassword@123"
        self.user = services.create_user(
            email="session@example.com",
            password=self.password,
            first_name="Session",
            last_name="User",
        )

        # Generate tokens for tests
        self.tokens = services.generate_tokens(user=self.user)
        self.access_token = self.tokens["access"]
        self.refresh_token = self.tokens["refresh"]

    # ── Refresh Token Tests ──────────────────────────────────

    def test_valid_refresh_token_generates_new_access_token(self):
        response = self.client.post(self.refresh_url, {"refresh": self.refresh_token})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.data["success"])
        self.assertEqual(response.data["message"], "Token refreshed successfully.")
        self.assertIn("access", response.data["data"])
        self.assertIn("refresh", response.data["data"])

    def test_invalid_refresh_token_rejected(self):
        response = self.client.post(self.refresh_url, {"refresh": "invalid.jwt.token"})
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertFalse(response.data["success"])
        self.assertEqual(response.data["message"], "Token refresh failed.")

    def test_blacklisted_refresh_token_rejected(self):
        # Blacklist the token first
        services.logout_user(refresh_token=self.refresh_token)

        # Attempt to refresh using the blacklisted token
        response = self.client.post(self.refresh_url, {"refresh": self.refresh_token})
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertFalse(response.data["success"])
        self.assertEqual(response.data["message"], "Token refresh failed.")

    def test_rotated_old_refresh_token_cannot_be_reused(self):
        # Refresh once to trigger token rotation
        ref_res = self.client.post(self.refresh_url, {"refresh": self.refresh_token})
        self.assertEqual(ref_res.status_code, status.HTTP_200_OK)
        new_refresh = ref_res.data["data"]["refresh"]

        # Attempting to use the OLD refresh token again must fail.
        # Rotation should blacklist the old token.
        reuse_res = self.client.post(
            self.refresh_url,
            {"refresh": self.refresh_token},
        )
        self.assertEqual(reuse_res.status_code, status.HTTP_400_BAD_REQUEST)

        # Using the NEW refresh token must succeed
        valid_res = self.client.post(self.refresh_url, {"refresh": new_refresh})
        self.assertEqual(valid_res.status_code, status.HTTP_200_OK)

    def test_missing_refresh_field_rejected(self):
        response = self.client.post(self.refresh_url, {})
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    # ── Logout Tests ─────────────────────────────────────────

    def test_successful_logout(self):
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {self.access_token}")
        response = self.client.post(self.logout_url, {"refresh": self.refresh_token})

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.data["success"])
        self.assertEqual(response.data["message"], "Logged out successfully.")
        self.assertEqual(response.data["data"], {})

        # Confirm token is blacklisted by attempting refresh
        ref_response = self.client.post(
            self.refresh_url, {"refresh": self.refresh_token}
        )
        self.assertEqual(ref_response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_logout_without_authentication_rejected(self):
        # No Bearer header supplied
        response = self.client.post(self.logout_url, {"refresh": self.refresh_token})
        self.assertIn(
            response.status_code,
            [status.HTTP_401_UNAUTHORIZED, status.HTTP_403_FORBIDDEN],
        )

    def test_logout_using_invalid_token_rejected(self):
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {self.access_token}")
        response = self.client.post(self.logout_url, {"refresh": "invalid.jwt.token"})
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertFalse(response.data["success"])

    def test_logout_using_already_blacklisted_token_rejected(self):
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {self.access_token}")
        # Logout first time
        self.client.post(self.logout_url, {"refresh": self.refresh_token})

        # Second logout attempt with same token
        response = self.client.post(self.logout_url, {"refresh": self.refresh_token})
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
