from django.contrib.auth import get_user_model
from django.test import TestCase

from apps.accounts import selectors, services

User = get_user_model()


class UserSelectorTest(TestCase):
    def setUp(self):
        self.user1 = services.create_user(
            email="user1@example.com",
            password="Password123!",
            first_name="User",
            last_name="One",
        )
        self.user2 = services.create_user(
            email="user2@example.com",
            password="Password123!",
            first_name="User",
            last_name="Two",
        )
        services.deactivate_user(user=self.user2)

    def test_get_user(self):
        fetched = selectors.get_user(user_id=self.user1.id)
        self.assertEqual(fetched, self.user1)

    def test_get_user_by_email(self):
        fetched = selectors.get_user_by_email(email="USER1@EXAMPLE.COM")
        self.assertEqual(fetched, self.user1)

    def test_list_users(self):
        users = list(selectors.list_users())
        self.assertEqual(len(users), 2)

    def test_active_users(self):
        active = list(selectors.active_users())
        self.assertEqual(len(active), 1)
        self.assertEqual(active[0], self.user1)
