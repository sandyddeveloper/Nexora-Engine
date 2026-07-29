from django.contrib.auth import get_user_model
from django.test import TestCase

from apps.accounts import services

User = get_user_model()


class UserServiceTest(TestCase):
    def test_create_user_service(self):
        user = services.create_user(
            email="service@example.com",
            password="Password123!",
            first_name="Service",
            last_name="User",
        )
        self.assertEqual(user.email, "service@example.com")
        self.assertTrue(user.check_password("Password123!"))

    def test_update_user_service(self):
        user = services.create_user(
            email="update@example.com",
            password="Password123!",
            first_name="Old",
            last_name="Name",
        )
        updated = services.update_user(user=user, first_name="New", last_name="Updated")
        self.assertEqual(updated.first_name, "New")
        self.assertEqual(updated.last_name, "Updated")

    def test_activate_and_deactivate_user(self):
        user = services.create_user(
            email="status@example.com",
            password="Password123!",
        )
        services.deactivate_user(user=user)
        self.assertFalse(user.is_active)
        services.activate_user(user=user)
        self.assertTrue(user.is_active)

    def test_change_password_service(self):
        user = services.create_user(
            email="pwd@example.com",
            password="OldPassword123!",
        )
        services.change_password(user=user, new_password="NewPassword123!")
        self.assertTrue(user.check_password("NewPassword123!"))
