"""Domain unit tests for accounts services."""

from datetime import timedelta
from django.contrib.auth import get_user_model
from django.test import TestCase
from django.utils import timezone

from apps.accounts import services
from apps.accounts.models import DeviceType, LoginEventType, SessionStatus

User = get_user_model()


class UserServiceTest(TestCase):
    """Unit tests for user domain services."""

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

    def test_soft_delete_and_restore_user_services(self):
        user = services.create_user(
            email="softdelserv@example.com",
            password="Password123!",
        )
        services.create_user_session(
            user=user,
            jti="jti-softdel",
            refresh_token="ref-softdel",
            access_token_expires_at=timezone.now() + timedelta(minutes=15),
            refresh_token_expires_at=timezone.now() + timedelta(days=7),
        )
        services.soft_delete_user(user=user)
        self.assertTrue(user.is_deleted)
        self.assertFalse(user.sessions.filter(status=SessionStatus.ACTIVE).exists())

        services.restore_user(user=user)
        self.assertFalse(user.is_deleted)
        self.assertTrue(user.is_active)

    def test_device_and_session_services(self):
        user = services.create_user(
            email="devicesession@example.com",
            password="Password123!",
        )
        device = services.register_device(
            user=user,
            device_type=DeviceType.MOBILE,
            user_agent="Mozilla/5.0 Android",
            ip_address="1.2.3.4",
            fingerprint="fp_android_123",
        )
        self.assertEqual(device.user, user)
        self.assertEqual(device.fingerprint, "fp_android_123")

        session = services.create_user_session(
            user=user,
            jti="jti-service-test",
            refresh_token="ref-service-token",
            access_token_expires_at=timezone.now() + timedelta(minutes=15),
            refresh_token_expires_at=timezone.now() + timedelta(days=7),
            device=device,
            ip_address="1.2.3.4",
        )
        self.assertEqual(session.status, SessionStatus.ACTIVE)

        revoked = services.revoke_user_session(jti="jti-service-test")
        self.assertTrue(revoked)

    def test_audit_logging_service(self):
        user = services.create_user(
            email="auditlog@example.com",
            password="Password123!",
        )
        log = services.record_login_event(
            event_type=LoginEventType.SUCCESS,
            user=user,
            status="SUCCESS",
            ip_address="192.168.1.50",
        )
        self.assertEqual(log.user, user)
        self.assertEqual(log.event_type, LoginEventType.SUCCESS)
