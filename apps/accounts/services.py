"""Domain service methods for managing authentication, security, sessions, devices, and users."""

import hashlib
import logging

from django.contrib.auth import authenticate, get_user_model
from django.contrib.auth.tokens import default_token_generator
from django.core.signing import BadSignature, SignatureExpired, TimestampSigner
from django.db import transaction
from django.utils import timezone
from django.utils.encoding import force_bytes, force_str
from django.utils.http import urlsafe_base64_decode, urlsafe_base64_encode
from rest_framework_simplejwt.tokens import RefreshToken

from .models import (
    Device,
    DeviceType,
    EmailVerificationToken,
    LoginEventType,
    LoginHistory,
    PasswordResetToken,
    SessionStatus,
    UserSession,
    UserStatus,
)
from .tasks import send_password_reset_email_task, send_verification_email_task

User = get_user_model()

logger = logging.getLogger("nexora.auth")
email_signer = TimestampSigner(salt="nexora.email_verification")


# ── Device & Session Management ──────────────────────────────────────────────


def register_device(
    *,
    user: User,
    device_type: str = DeviceType.UNKNOWN,
    user_agent: str = "",
    ip_address: str | None = None,
    device_name: str = "",
    fingerprint: str = "",
    browser: str = "",
    os: str = "",
    platform: str = "",
    is_trusted: bool = False,
) -> Device:
    """Register or update a user device record."""
    if fingerprint:
        device, created = Device.objects.get_or_create(
            user=user,
            fingerprint=fingerprint,
            defaults={
                "device_type": device_type,
                "device_name": device_name,
                "user_agent": user_agent,
                "ip_address": ip_address,
                "browser": browser,
                "os": os,
                "platform": platform,
                "is_trusted": is_trusted,
                "last_active": timezone.now(),
            },
        )
        if not created:
            device.ip_address = ip_address or device.ip_address
            device.user_agent = user_agent or device.user_agent
            device.last_active = timezone.now()
            if device_name:
                device.device_name = device_name
            device.save(
                update_fields=[
                    "ip_address",
                    "user_agent",
                    "last_active",
                    "device_name",
                    "updated_at",
                ]
            )
        return device

    return Device.objects.create(
        user=user,
        device_type=device_type,
        device_name=device_name,
        user_agent=user_agent,
        ip_address=ip_address,
        browser=browser,
        os=os,
        platform=platform,
        is_trusted=is_trusted,
        last_active=timezone.now(),
    )


def record_login_event(
    *,
    event_type: str,
    user: User | None = None,
    email_attempted: str = "",
    status: str = "SUCCESS",
    failure_reason: str = "",
    ip_address: str | None = None,
    user_agent: str = "",
    location: str = "",
    device: Device | None = None,
) -> LoginHistory:
    """Create an audit trail log entry for an authentication event."""
    return LoginHistory.objects.create(
        user=user,
        email_attempted=email_attempted or (user.email if user else ""),
        event_type=event_type,
        status=status,
        failure_reason=failure_reason,
        ip_address=ip_address,
        user_agent=user_agent,
        location=location,
        device=device,
        timestamp=timezone.now(),
    )


def create_user_session(
    *,
    user: User,
    jti: str,
    refresh_token: str,
    access_token_expires_at,
    refresh_token_expires_at,
    device: Device | None = None,
    ip_address: str | None = None,
    browser: str = "",
    location: str = "",
) -> UserSession:
    """Create an active JWT session record."""
    refresh_hash = hashlib.sha256(refresh_token.encode("utf-8")).hexdigest()
    return UserSession.objects.create(
        user=user,
        jti=jti,
        refresh_token_hash=refresh_hash,
        access_token_expires_at=access_token_expires_at,
        refresh_token_expires_at=refresh_token_expires_at,
        device=device,
        ip_address=ip_address,
        browser=browser,
        location=location,
        login_time=timezone.now(),
        last_activity=timezone.now(),
        status=SessionStatus.ACTIVE,
        is_current=True,
    )


def revoke_user_session(*, jti: str) -> bool:
    """Revoke an active JWT session by JTI."""
    updated = UserSession.objects.filter(
        jti=jti, status=SessionStatus.ACTIVE
    ).update(
        status=SessionStatus.REVOKED,
        logout_time=timezone.now(),
        is_current=False,
    )
    return updated > 0


def revoke_all_user_sessions(
    *, user: User, except_jti: str | None = None
) -> int:
    """Revoke all active sessions for a user, optionally excluding one session."""
    qs = UserSession.objects.filter(user=user, status=SessionStatus.ACTIVE)
    if except_jti:
        qs = qs.exclude(jti=except_jti)
    return qs.update(
        status=SessionStatus.REVOKED,
        logout_time=timezone.now(),
        is_current=False,
    )


# ── User Lifecycle Services ──────────────────────────────────────────────────


@transaction.atomic
def create_user(
    *, email: str, password: str, is_email_verified: bool = True, **extra_fields
) -> User:
    """Create and return a new User within an atomic transaction."""
    user = User.objects.create_user(
        email=email,
        password=password,
        email_verified=is_email_verified,
        **extra_fields,
    )
    if not is_email_verified:
        token = generate_email_verification_token(user)
        logger.info("Verification token generated for new user %s", email)
        try:
            send_verification_email_task.delay(str(user.id), token)
        except Exception:
            logger.warning("Celery queue offline. Verification email link for %s: /verify-email/?token=%s", email, token)
    return user


def update_user(*, user: User, **fields) -> User:
    """Update fields on an existing User instance."""
    allowed_fields = {
        "first_name",
        "last_name",
        "display_name",
        "username",
        "phone_number",
        "date_of_birth",
        "gender",
        "language",
        "timezone",
        "theme",
        "status",
        "is_active",
        "is_staff",
    }
    for field, value in fields.items():
        if field in allowed_fields:
            setattr(user, field, value)
    user.save()
    return user


def activate_user(*, user: User) -> User:
    """Activate a user account."""
    user.status = UserStatus.ACTIVE
    user.is_active = True
    user.save(update_fields=["status", "is_active", "updated_at"])
    return user


def deactivate_user(*, user: User) -> User:
    """Deactivate a user account."""
    user.status = UserStatus.INACTIVE
    user.is_active = False
    user.save(update_fields=["status", "is_active", "updated_at"])
    return user


@transaction.atomic
def soft_delete_user(*, user: User) -> User:
    """Soft delete user account and revoke all active sessions atomically."""
    user.delete(soft=True)
    revoke_all_user_sessions(user=user)
    return user


@transaction.atomic
def restore_user(*, user: User) -> User:
    """Restore soft-deleted user account atomically."""
    user.restore()
    user.status = UserStatus.ACTIVE
    user.save(update_fields=["status", "is_active", "updated_at"])
    return user


def change_password(*, user: User, new_password: str) -> User:
    """Change a user's password."""
    user.set_password(new_password)
    user.password_changed_at = timezone.now()
    user.save(update_fields=["password", "password_changed_at", "updated_at"])
    return user


# ── Authentication Services ──────────────────────────────────────────────────


def authenticate_user(*, email: str, password: str, ip_address: str | None = None):
    """Authenticate a user with email and password.

    Returns (user, reason) tuple.
    """
    user = authenticate(email=email, password=password)
    if user is None:
        logger.warning("Failed login attempt for email: %s", email)
        record_login_event(
            event_type=LoginEventType.FAILED,
            email_attempted=email,
            status="FAILED",
            failure_reason="INVALID_CREDENTIALS",
            ip_address=ip_address,
        )
        return None, "INVALID_CREDENTIALS"

    if not user.is_active or user.status == UserStatus.INACTIVE:
        logger.warning("Login attempt for inactive account: %s", email)
        record_login_event(
            event_type=LoginEventType.FAILED,
            user=user,
            status="FAILED",
            failure_reason="INACTIVE_ACCOUNT",
            ip_address=ip_address,
        )
        return None, "INACTIVE_ACCOUNT"

    if user.status == UserStatus.LOCKED or (
        user.locked_until and user.locked_until > timezone.now()
    ):
        logger.warning("Login attempt for locked account: %s", email)
        record_login_event(
            event_type=LoginEventType.FAILED,
            user=user,
            status="FAILED",
            failure_reason="ACCOUNT_LOCKED",
            ip_address=ip_address,
        )
        return None, "ACCOUNT_LOCKED"

    if not user.email_verified:
        logger.warning("Login attempt for unverified account: %s", email)
        record_login_event(
            event_type=LoginEventType.FAILED,
            user=user,
            status="FAILED",
            failure_reason="UNVERIFIED_EMAIL",
            ip_address=ip_address,
        )
        return None, "UNVERIFIED_EMAIL"

    user.failed_login_attempts = 0
    user.last_login_ip = ip_address or user.last_login_ip
    user.save(update_fields=["failed_login_attempts", "last_login_ip", "updated_at"])

    record_login_event(
        event_type=LoginEventType.SUCCESS,
        user=user,
        status="SUCCESS",
        ip_address=ip_address,
    )
    return user, "SUCCESS"


def generate_tokens(*, user: User) -> dict:
    """Generate JWT access and refresh tokens for a user."""
    refresh = RefreshToken.for_user(user)
    return {
        "access": str(refresh.access_token),
        "refresh": str(refresh),
    }


def build_login_response(*, user: User) -> dict:
    """Build the complete login response data payload.

    Combines JWT tokens with a safe user profile representation.
    """
    tokens = generate_tokens(user=user)
    user.last_login = timezone.now()
    user.save(update_fields=["last_login"])

    return {
        **tokens,
        "user": {
            "id": str(user.id),
            "email": user.email,
            "username": user.username,
            "first_name": user.first_name,
            "last_name": user.last_name,
        },
    }


def refresh_access_token(*, refresh_token: str) -> dict | None:
    """Validate a refresh token and return new access + refresh tokens."""
    try:
        from django.conf import settings

        jwt_settings = getattr(settings, "SIMPLE_JWT", {})
        refresh = RefreshToken(refresh_token)

        if jwt_settings.get("ROTATE_REFRESH_TOKENS", False):
            if jwt_settings.get("BLACKLIST_AFTER_ROTATION", False):
                refresh.blacklist()
            refresh.set_jti()
            refresh.set_exp()
            refresh.set_iat()

        return {
            "access": str(refresh.access_token),
            "refresh": str(refresh),
        }
    except Exception:
        logger.warning("Invalid or expired refresh token used")
        return None


def logout_user(*, refresh_token: str, user: User | None = None) -> bool:
    """Blacklist a refresh token to invalidate the session."""
    try:
        token = RefreshToken(refresh_token)
        jti = token.payload.get("jti")
        if jti:
            revoke_user_session(jti=jti)

        token.blacklist()
        if user:
            record_login_event(event_type=LoginEventType.LOGOUT, user=user)
        logger.info("User logged out, refresh token blacklisted")
        return True
    except Exception:
        logger.warning("Logout failed: invalid or already blacklisted token")
        return False


# ── Password Management Services ─────────────────────────────────────────────


def generate_reset_token(user: User) -> str:
    """Generate a combined base64(uid).token string for password reset."""
    uidb64 = urlsafe_base64_encode(force_bytes(user.pk))
    token = default_token_generator.make_token(user)

    token_hash = hashlib.sha256(token.encode("utf-8")).hexdigest()
    expires_at = timezone.now() + timezone.timedelta(hours=24)
    PasswordResetToken.objects.create(
        user=user,
        token_hash=token_hash,
        expires_at=expires_at,
    )
    return f"{uidb64}.{token}"


def verify_and_get_user_from_token(token_str: str) -> User | None:
    """Verify reset token and return user, or None if invalid/expired/reused."""
    try:
        if "." not in token_str:
            return None
        uidb64, token = token_str.split(".", 1)
        uid = force_str(urlsafe_base64_decode(uidb64))
        user = User.objects.get(pk=uid)
        if not user.is_active:
            return None
        if not default_token_generator.check_token(user, token):
            return None

        # Verify token has not already been consumed
        token_hash = hashlib.sha256(token.encode("utf-8")).hexdigest()
        if PasswordResetToken.objects.filter(
            user=user, token_hash=token_hash, is_used=True
        ).exists():
            logger.warning("Attempted reuse of already consumed password reset token for %s", user.email)
            return None

        return user
    except Exception:
        return None


def change_user_password(
    *, user: User, current_password: str, new_password: str
) -> bool:
    """Change user password after verifying current_password."""
    if not user.check_password(current_password):
        logger.warning(
            "Password change failed for user %s: wrong current_password", user.email
        )
        return False

    user.set_password(new_password)
    user.password_changed_at = timezone.now()
    user.save(update_fields=["password", "password_changed_at", "updated_at"])
    logger.info("Password changed successfully for user %s", user.email)
    record_login_event(event_type=LoginEventType.PASSWORD_RESET, user=user)
    return True


def request_password_reset(*, email: str) -> None:
    """Request a password reset token for the given email."""
    try:
        user = User.objects.get(email=email, is_active=True)
        token = generate_reset_token(user)
        logger.info("Password reset token generated for user %s", email)
        try:
            send_password_reset_email_task.delay(str(user.id), token)
        except Exception:
            logger.warning("Celery queue offline. Password reset link for %s: /reset-password/?token=%s", email, token)
    except User.DoesNotExist:
        logger.info(
            "Password reset requested for non-existent/inactive email: %s", email
        )


@transaction.atomic
def reset_password_with_token(*, token: str, new_password: str) -> bool:
    """Reset user password using a valid one-time reset token."""
    user = verify_and_get_user_from_token(token)
    if user is None:
        logger.warning("Invalid or expired password reset token used")
        return False

    if "." in token:
        _, raw_token = token.split(".", 1)
        token_hash = hashlib.sha256(raw_token.encode("utf-8")).hexdigest()
        PasswordResetToken.objects.filter(
            user=user, token_hash=token_hash, is_used=False
        ).update(
            is_used=True,
            used_at=timezone.now(),
        )

    user.set_password(new_password)
    user.password_changed_at = timezone.now()
    user.save(update_fields=["password", "password_changed_at", "updated_at"])
    logger.info("Password reset successfully for user %s", user.email)
    record_login_event(event_type=LoginEventType.PASSWORD_RESET, user=user)
    return True


# ── Email Verification Services ──────────────────────────────────────────────


def generate_email_verification_token(user: User) -> str:
    """Generate a signed base64(uid).signature email verification token."""
    uidb64 = urlsafe_base64_encode(force_bytes(user.pk))
    signed_value = email_signer.sign(str(user.pk))
    token_hash = hashlib.sha256(signed_value.encode("utf-8")).hexdigest()
    expires_at = timezone.now() + timezone.timedelta(hours=24)

    EmailVerificationToken.objects.create(
        user=user,
        token_hash=token_hash,
        expires_at=expires_at,
    )
    return f"{uidb64}.{signed_value}"


@transaction.atomic
def verify_email(*, token: str, max_age: int = 86400) -> tuple[bool, str]:
    """Verify user email using signed verification token."""
    try:
        if "." not in token:
            return False, "Invalid verification token."
        uidb64, signed_value = token.split(".", 1)
        uid = force_str(urlsafe_base64_decode(uidb64))

        user = User.objects.get(pk=uid)
        if user.email_verified:
            return False, "Email address is already verified."

        token_hash = hashlib.sha256(signed_value.encode("utf-8")).hexdigest()
        token_record = EmailVerificationToken.objects.filter(
            token_hash=token_hash,
            user=user,
            is_used=False,
            expires_at__gt=timezone.now(),
        ).first()

        try:
            unsigned_pk = email_signer.unsign(signed_value, max_age=max_age)
            if unsigned_pk != str(user.pk):
                return False, "Invalid verification token."
        except SignatureExpired:
            return False, "Verification token has expired."
        except BadSignature:
            return False, "Invalid verification token."

        user.email_verified = True
        user.email_verified_at = timezone.now()
        user.save(update_fields=["email_verified", "email_verified_at", "updated_at"])

        if token_record:
            token_record.is_used = True
            token_record.used_at = timezone.now()
            token_record.save(update_fields=["is_used", "used_at", "updated_at"])

        logger.info("Email verified successfully for user %s", user.email)
        record_login_event(
            event_type=LoginEventType.EMAIL_VERIFICATION,
            user=user,
            status="SUCCESS",
        )
        return True, "Email verified successfully."
    except Exception:
        return False, "Invalid verification token."


def resend_verification_email(*, email: str) -> None:
    """Resend email verification token for the given email."""
    try:
        user = User.objects.get(email=email, is_active=True)
        if not user.email_verified:
            token = generate_email_verification_token(user)
            logger.info("Verification token resent for user %s", email)
            try:
                send_verification_email_task.delay(str(user.id), token)
            except Exception:
                logger.warning("Celery queue offline. Resent verification link for %s: /verify-email/?token=%s", email, token)
        else:
            logger.info(
                "Resend verification requested for already verified email: %s", email
            )
    except User.DoesNotExist:
        logger.info(
            "Resend verification requested for non-existent/inactive email: %s", email
        )
