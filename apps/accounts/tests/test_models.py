from django.contrib.auth import get_user_model
from django.test import TestCase

User = get_user_model()


class UserModelTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            email="testuser@example.com",
            password="SecurePassword123!",
            first_name="John",
            last_name="Doe",
        )

    def test_create_user(self):
        self.assertEqual(self.user.email, "testuser@example.com")
        self.assertTrue(self.user.check_password("SecurePassword123!"))
        self.assertTrue(self.user.is_active)
        self.assertFalse(self.user.is_staff)

    def test_str_and_names(self):
        self.assertEqual(str(self.user), "testuser@example.com")
        self.assertEqual(self.user.get_full_name(), "John Doe")
        self.assertEqual(self.user.get_short_name(), "John")

    def test_create_superuser(self):
        admin_user = User.objects.create_superuser(
            email="admin@example.com",
            password="AdminPassword123!",
            first_name="Admin",
            last_name="User",
        )
        self.assertTrue(admin_user.is_staff)
        self.assertTrue(admin_user.is_superuser)
