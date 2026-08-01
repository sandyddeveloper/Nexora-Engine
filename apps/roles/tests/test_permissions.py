"""Unit tests for roles authorization and permission enforcement."""

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient

from apps.accounts.services import create_user
from apps.roles.services import create_role

User = get_user_model()


class RolesPermissionSecurityTests(TestCase):
    """Test suite ensuring non-admin and anonymous users cannot manipulate roles."""

    def setUp(self):
        self.client = APIClient()
        self.regular_user = create_user(
            email="regular@example.com",
            password="Password123!",
            first_name="Regular",
            last_name="User",
        )
        self.admin_user = create_user(
            email="admin_role@example.com",
            password="Password123!",
            is_staff=True,
            is_superuser=True,
        )
        self.test_role = create_role(name="Manager", code="MANAGER")
        self.roles_url = reverse("roles:role-list")
        self.role_detail_url = reverse("roles:role-detail", kwargs={"pk": str(self.test_role.id)})

    def test_anonymous_user_cannot_list_roles(self):
        response = self.client.get(self.roles_url)
        self.assertIn(response.status_code, [status.HTTP_401_UNAUTHORIZED, status.HTTP_403_FORBIDDEN])

    def test_regular_user_denied_role_access(self):
        self.client.force_authenticate(user=self.regular_user)
        response = self.client.get(self.roles_url)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

        create_payload = {"name": "Hacker Role", "code": "HACKER"}
        response = self.client.post(self.roles_url, create_payload)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_admin_user_can_access_and_manage_roles(self):
        self.client.force_authenticate(user=self.admin_user)
        response = self.client.get(self.roles_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("pagination", response.data)

        create_payload = {"name": "Supervisor", "code": "SUPERVISOR"}
        response = self.client.post(self.roles_url, create_payload)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
