import uuid

from django.contrib.auth import get_user_model
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from apps.accounts import services

User = get_user_model()


class UserAPIViewTest(APITestCase):
    def setUp(self):
        self.user = services.create_user(
            email="api@example.com",
            password="Password123!",
            first_name="API",
            last_name="User",
        )
        self.list_url = reverse("accounts:user-list")
        self.detail_url = reverse("accounts:user-detail", kwargs={"pk": self.user.id})

    def test_list_users_view(self):
        response = self.client.get(self.list_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.data["success"])
        self.assertEqual(len(response.data["data"]), 1)

    def test_create_user_view(self):
        data = {
            "email": "newuser@example.com",
            "password": "NewUserPassword123!",
            "first_name": "New",
            "last_name": "User",
        }
        response = self.client.post(self.list_url, data)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertTrue(response.data["success"])
        self.assertEqual(response.data["data"]["email"], "newuser@example.com")
        self.assertNotIn("password", response.data["data"])

    def test_detail_user_view(self):
        response = self.client.get(self.detail_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.data["success"])
        self.assertEqual(response.data["data"]["email"], "api@example.com")

    def test_update_user_view(self):
        data = {"first_name": "UpdatedAPI"}
        response = self.client.patch(self.detail_url, data)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.data["success"])
        self.assertEqual(response.data["data"]["first_name"], "UpdatedAPI")

    def test_delete_user_view(self):
        response = self.client.delete(self.detail_url)
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.user.refresh_from_db()
        self.assertFalse(self.user.is_active)

    def test_detail_user_not_found(self):
        non_existent_url = reverse("accounts:user-detail", kwargs={"pk": uuid.uuid4()})
        response = self.client.get(non_existent_url)
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
        self.assertFalse(response.data["success"])
