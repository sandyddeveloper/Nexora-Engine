"""Comprehensive unit tests for accounts domain models and relationships."""

import uuid
from datetime import timedelta
from django.contrib.auth import get_user_model
from django.db import IntegrityError
from django.test import TestCase
from django.utils import timezone

from apps.accounts.models import (
    Device,
    DeviceType,
    EmailVerificationToken,
    GenderChoices,
    LoginEventType,
    LoginHistory,
    PasswordResetToken,
    ProfileVisibility,
    SessionStatus,
    UserPreference,
    UserProfile,
    UserSession,
    UserStatus,
)

User = get_user_model()


class UserModelTests(TestCase):
    """Unit tests for User model, soft deletion, and properties."""

    def test_user_creation_and_defaults(self):
        user = User.objects.create_user(
            email="testuser@example.com",
            password="SecurePassword123!",
            first_name="Test",
            last_name="User",
        )
        self.assertIsInstance(user.id, uuid.UUID)
        self.assertEqual(user.email, "testuser@example.com")
        self.assertEqual(user.username, "testuser")
        self.assertEqual(user.status, UserStatus.ACTIVE)
        self.assertTrue(user.is_active)
        self.assertFalse(user.is_staff)
        self.assertFalse(user.email_verified)
        self.assertFalse(user.is_deleted)
        self.assertEqual(str(user), "testuser@example.com")
        self.assertEqual(user.get_full_name(), "Test User")

    def test_superuser_creation(self):
        admin_user = User.objects.create_superuser(
            email="admin@example.com",
            password="AdminPassword123!",
        )
        self.assertTrue(admin_user.is_staff)
        self.assertTrue(admin_user.is_superuser)
        self.assertTrue(admin_user.email_verified)
        self.assertEqual(admin_user.status, UserStatus.ACTIVE)

    def test_user_soft_delete_and_restore(self):
        user = User.objects.create_user(
            email="softdelete@example.com",
            password="Password123!",
        )
        user.delete(soft=True)
        self.assertTrue(user.is_deleted)
        self.assertFalse(user.is_active)
        self.assertIsNotNone(user.deleted_at)

        # Ensure default queryset excludes soft-deleted users
        self.assertFalse(User.objects.filter(pk=user.id).exists())
        self.assertTrue(User.objects.with_deleted().filter(pk=user.id).exists())

        # Restore user
        user.restore()
        self.assertFalse(user.is_deleted)
        self.assertTrue(user.is_active)
        self.assertIsNone(user.deleted_at)
        self.assertTrue(User.objects.filter(pk=user.id).exists())

    def test_unique_email_constraint(self):
        User.objects.create_user(email="unique@example.com", password="Password123!")
        with self.assertRaises(IntegrityError):
            User.objects.create_user(email="unique@example.com", password="Password456!")


class UserProfileAndPreferenceSignalsTests(TestCase):
    """Unit tests for automatic UserProfile and UserPreference creation via signals."""

    def test_auto_profile_and_preference_creation(self):
        user = User.objects.create_user(
            email="signals@example.com",
            password="Password123!",
        )
        self.assertTrue(hasattr(user, "profile"))
        self.assertTrue(hasattr(user, "preference"))
        self.assertIsInstance(user.profile, UserProfile)
        self.assertIsInstance(user.preference, UserPreference)
        self.assertEqual(user.profile.visibility, ProfileVisibility.PUBLIC)
        self.assertEqual(user.preference.language, "en")


class DeviceModelTests(TestCase):
    """Unit tests for Device tracking model."""

    def test_device_creation(self):
        user = User.objects.create_user(email="device@example.com", password="Password123!")
        device = Device.objects.create(
            user=user,
            device_name="MacBook Pro",
            device_type=DeviceType.DESKTOP,
            browser="Chrome 120",
            os="macOS 14",
            ip_address="192.168.1.1",
            fingerprint="fp_abc123hash",
            is_trusted=True,
        )
        self.assertEqual(device.user, user)
        self.assertEqual(device.device_type, DeviceType.DESKTOP)
        self.assertTrue(device.is_trusted)
        self.assertIn("MacBook Pro", str(device))


class UserSessionModelTests(TestCase):
    """Unit tests for UserSession model."""

    def test_session_lifecycle(self):
        user = User.objects.create_user(email="session@example.com", password="Password123!")
        device = Device.objects.create(user=user, device_name="iPhone 15", device_type=DeviceType.MOBILE)
        session = UserSession.objects.create(
            user=user,
            jti="jti-uuid-12345",
            refresh_token_hash="hash123",
            access_token_expires_at=timezone.now() + timedelta(minutes=15),
            refresh_token_expires_at=timezone.now() + timedelta(days=7),
            device=device,
            status=SessionStatus.ACTIVE,
        )
        self.assertEqual(session.status, SessionStatus.ACTIVE)
        self.assertEqual(session.device, device)
        self.assertIn("jti-uuid", str(session))


class LoginHistoryModelTests(TestCase):
    """Unit tests for LoginHistory audit log."""

    def test_login_history_creation(self):
        user = User.objects.create_user(email="history@example.com", password="Password123!")
        log = LoginHistory.objects.create(
            user=user,
            email_attempted=user.email,
            event_type=LoginEventType.SUCCESS,
            status="SUCCESS",
            ip_address="10.0.0.1",
        )
        self.assertEqual(log.user, user)
        self.assertEqual(log.event_type, LoginEventType.SUCCESS)
        self.assertIn("SUCCESS", str(log))


class TokenModelsTests(TestCase):
    """Unit tests for PasswordResetToken and EmailVerificationToken."""

    def test_password_reset_token(self):
        user = User.objects.create_user(email="reset@example.com", password="Password123!")
        token = PasswordResetToken.objects.create(
            user=user,
            token_hash="reset_hash_123",
            expires_at=timezone.now() + timedelta(hours=24),
        )
        self.assertFalse(token.is_used)
        self.assertEqual(token.user, user)

    def test_email_verification_token(self):
        user = User.objects.create_user(email="verify@example.com", password="Password123!")
        token = EmailVerificationToken.objects.create(
            user=user,
            token_hash="verify_hash_123",
            expires_at=timezone.now() + timedelta(hours=24),
        )
        self.assertFalse(token.is_used)
        self.assertEqual(token.user, user)
