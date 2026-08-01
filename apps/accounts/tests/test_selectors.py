"""Domain unit tests for accounts selectors."""

from datetime import timedelta
from django.contrib.auth import get_user_model
from django.test import TestCase
from django.utils import timezone

from apps.accounts import selectors, services
from apps.accounts.models import DeviceType, SessionStatus

User = get_user_model()


class UserSelectorTest(TestCase):
    """Unit tests for user and authentication domain query selectors."""

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

    def test_get_user_by_username(self):
        fetched = selectors.get_user_by_username(username=self.user1.username)
        self.assertEqual(fetched, self.user1)

    def test_list_users(self):
        users = list(selectors.list_users())
        self.assertEqual(len(users), 2)

    def test_active_users(self):
        active = list(selectors.active_users())
        self.assertEqual(len(active), 1)
        self.assertEqual(active[0], self.user1)

    def test_profile_and_preference_selectors(self):
        profile = selectors.get_user_profile(user=self.user1)
        preference = selectors.get_user_preferences(user=self.user1)
        self.assertIsNotNone(profile)
        self.assertIsNotNone(preference)
        self.assertEqual(profile.user, self.user1)
        self.assertEqual(preference.user, self.user1)

    def test_device_and_session_selectors(self):
        device = services.register_device(
            user=self.user1,
            device_type=DeviceType.DESKTOP,
            device_name="Workstation",
            fingerprint="fp_selector_test",
        )
        session = services.create_user_session(
            user=self.user1,
            jti="jti-selector-test",
            refresh_token="ref-selector-token",
            access_token_expires_at=timezone.now() + timedelta(minutes=15),
            refresh_token_expires_at=timezone.now() + timedelta(days=7),
            device=device,
        )
        devices = selectors.get_user_devices(user=self.user1)
        sessions = selectors.get_active_user_sessions(user=self.user1)
        self.assertIn(device, devices)
        self.assertIn(session, sessions)
