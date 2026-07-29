"""Tests for the login API endpoint."""

from django.contrib.auth import get_user_model
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from apps.accounts import services

User = get_user_model()


class LoginAPIViewTest(APITestCase):
    """Test suite for POST /api/v1/auth/login/."""

    def setUp(self):
        self.url = reverse("accounts:login")
        self.password = "StrongPassword@123"
        self.user = services.create_user(
            email="login@example.com",
            password=self.password,
            first_name="Login",
            last_name="User",
        )

    # ── Success ──────────────────────────────────────────────

    def test_successful_login(self):
        response = self.client.post(
            self.url, {"email": "login@example.com", "password": self.password}
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.data["success"])
        self.assertEqual(response.data["message"], "Login successful.")
        data = response.data["data"]
        self.assertIn("access", data)
        self.assertIn("refresh", data)
        self.assertIn("user", data)
        self.assertEqual(data["user"]["email"], "login@example.com")
        self.assertEqual(data["user"]["first_name"], "Login")
        self.assertEqual(data["user"]["last_name"], "User")
        self.assertNotIn("password", data["user"])

    def test_login_returns_valid_jwt_tokens(self):
        response = self.client.post(
            self.url, {"email": "login@example.com", "password": self.password}
        )
        data = response.data["data"]
        # JWT tokens have 3 dot-separated segments
        self.assertEqual(len(data["access"].split(".")), 3)
        self.assertEqual(len(data["refresh"].split(".")), 3)

    def test_login_updates_last_login(self):
        self.assertIsNone(self.user.last_login)
        self.client.post(
            self.url, {"email": "login@example.com", "password": self.password}
        )
        self.user.refresh_from_db()
        self.assertIsNotNone(self.user.last_login)

    # ── Wrong password ───────────────────────────────────────

    def test_wrong_password_rejected(self):
        response = self.client.post(
            self.url, {"email": "login@example.com", "password": "WrongPassword@999"}
        )
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
        self.assertFalse(response.data["success"])
        self.assertEqual(response.data["message"], "Invalid email or password.")

    # ── Unknown email ────────────────────────────────────────

    def test_unknown_email_rejected(self):
        response = self.client.post(
            self.url, {"email": "ghost@example.com", "password": self.password}
        )
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
        self.assertFalse(response.data["success"])
        # Same generic message — never reveal if email exists
        self.assertEqual(response.data["message"], "Invalid email or password.")

    # ── Inactive user ────────────────────────────────────────

    def test_inactive_user_rejected(self):
        services.deactivate_user(user=self.user)
        response = self.client.post(
            self.url, {"email": "login@example.com", "password": self.password}
        )
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
        self.assertFalse(response.data["success"])

    # ── Missing fields ───────────────────────────────────────

    def test_missing_email_rejected(self):
        response = self.client.post(self.url, {"password": self.password})
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertFalse(response.data["success"])

    def test_missing_password_rejected(self):
        response = self.client.post(self.url, {"email": "login@example.com"})
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertFalse(response.data["success"])

    def test_empty_body_rejected(self):
        response = self.client.post(self.url, {})
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertFalse(response.data["success"])
