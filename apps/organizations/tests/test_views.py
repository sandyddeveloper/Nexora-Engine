"""Unit tests for organizations API views and permissions."""

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient

from apps.accounts.services import create_user
from apps.organizations.services import create_organization

User = get_user_model()


class OrganizationAPIViewTests(TestCase):
    """Test suite for organization endpoints authorization and pagination."""

    def setUp(self):
        self.client = APIClient()
        self.admin_user = create_user(
            email="org_admin@example.com",
            password="Password123!",
            is_staff=True,
            is_superuser=True,
        )
        self.regular_user = create_user(
            email="org_regular@example.com",
            password="Password123!",
        )
        self.org = create_organization(name="TechCorp", legal_name="TechCorp Ltd")
        self.list_url = reverse("organizations:organization-list")
        self.detail_url = reverse("organizations:organization-detail", kwargs={"pk": str(self.org.id)})

    def test_anonymous_user_cannot_list_organizations(self):
        response = self.client.get(self.list_url)
        self.assertIn(response.status_code, [status.HTTP_401_UNAUTHORIZED, status.HTTP_403_FORBIDDEN])

    def test_admin_user_can_list_and_create_organizations(self):
        self.client.force_authenticate(user=self.admin_user)
        response = self.client.get(self.list_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("pagination", response.data)

        payload = {"name": "Nexus Systems", "legal_name": "Nexus Systems Inc"}
        response = self.client.post(self.list_url, payload)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertIn("code", response.data["data"])

    def test_retrieve_organization_details(self):
        self.client.force_authenticate(user=self.admin_user)
        response = self.client.get(self.detail_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["data"]["name"], "TechCorp")
        self.assertIn("setting", response.data["data"])
