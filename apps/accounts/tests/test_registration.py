"""Tests for the registration API endpoint."""

from django.contrib.auth import get_user_model
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

User = get_user_model()


class RegisterAPIViewTest(APITestCase):
    """Test suite for POST /api/v1/auth/register/."""

    def setUp(self):
        self.url = reverse("accounts:register")
        self.valid_payload = {
            "email": "newuser@example.com",
            "password": "StrongPassword@123",
            "confirm_password": "StrongPassword@123",
            "first_name": "John",
            "last_name": "Doe",
        }

    # ── Success ──────────────────────────────────────────────

    def test_successful_registration(self):
        response = self.client.post(self.url, self.valid_payload)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertTrue(response.data["success"])
        self.assertEqual(response.data["message"], "User registered successfully.")
        self.assertEqual(response.data["data"]["email"], "newuser@example.com")
        self.assertEqual(response.data["data"]["first_name"], "John")
        self.assertEqual(response.data["data"]["last_name"], "Doe")
        self.assertNotIn("password", response.data["data"])
        self.assertNotIn("confirm_password", response.data["data"])

    def test_user_stored_in_database(self):
        self.client.post(self.url, self.valid_payload)
        self.assertTrue(User.objects.filter(email="newuser@example.com").exists())

    def test_password_is_hashed(self):
        self.client.post(self.url, self.valid_payload)
        user = User.objects.get(email="newuser@example.com")
        self.assertNotEqual(user.password, "StrongPassword@123")
        self.assertTrue(user.check_password("StrongPassword@123"))

    def test_email_is_normalized_to_lowercase(self):
        payload = {**self.valid_payload, "email": "   UPPERCASE@Example.COM   "}
        response = self.client.post(self.url, payload)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        user = User.objects.get(pk=response.data["data"]["id"])
        self.assertEqual(user.email, "uppercase@example.com")

    def test_whitespace_trimmed_from_names(self):
        payload = {
            **self.valid_payload,
            "first_name": "  John  ",
            "last_name": "  Doe  ",
        }
        response = self.client.post(self.url, payload)
        self.assertEqual(response.data["data"]["first_name"], "John")
        self.assertEqual(response.data["data"]["last_name"], "Doe")

    # ── Duplicate email ──────────────────────────────────────

    def test_duplicate_email_rejected(self):
        self.client.post(self.url, self.valid_payload)
        response = self.client.post(self.url, self.valid_payload)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertFalse(response.data["success"])

    # ── Password mismatch ────────────────────────────────────

    def test_password_mismatch_rejected(self):
        payload = {**self.valid_payload, "confirm_password": "DifferentPass@999"}
        response = self.client.post(self.url, payload)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertFalse(response.data["success"])

    # ── Weak password ────────────────────────────────────────

    def test_weak_password_rejected(self):
        payload = {
            **self.valid_payload,
            "password": "123",
            "confirm_password": "123",
        }
        response = self.client.post(self.url, payload)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertFalse(response.data["success"])

    def test_common_password_rejected(self):
        payload = {
            **self.valid_payload,
            "password": "password123",
            "confirm_password": "password123",
        }
        response = self.client.post(self.url, payload)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertFalse(response.data["success"])

    def test_numeric_only_password_rejected(self):
        payload = {
            **self.valid_payload,
            "password": "98765432",
            "confirm_password": "98765432",
        }
        response = self.client.post(self.url, payload)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertFalse(response.data["success"])

    # ── Missing required fields ──────────────────────────────

    def test_missing_email_rejected(self):
        payload = {**self.valid_payload}
        del payload["email"]
        response = self.client.post(self.url, payload)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertFalse(response.data["success"])

    def test_missing_password_rejected(self):
        payload = {**self.valid_payload}
        del payload["password"]
        response = self.client.post(self.url, payload)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertFalse(response.data["success"])

    def test_missing_confirm_password_rejected(self):
        payload = {**self.valid_payload}
        del payload["confirm_password"]
        response = self.client.post(self.url, payload)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertFalse(response.data["success"])

    def test_missing_first_name_rejected(self):
        payload = {**self.valid_payload}
        del payload["first_name"]
        response = self.client.post(self.url, payload)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertFalse(response.data["success"])

    def test_missing_last_name_rejected(self):
        payload = {**self.valid_payload}
        del payload["last_name"]
        response = self.client.post(self.url, payload)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertFalse(response.data["success"])
