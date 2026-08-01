"""Read-only selector queries for the accounts domain."""

import uuid
from typing import Optional

from django.contrib.auth import get_user_model
from django.db.models import QuerySet
from django.utils import timezone

from .models import (
    Device,
    EmailVerificationToken,
    LoginHistory,
    PasswordResetToken,
    SessionStatus,
    UserPreference,
    UserProfile,
    UserSession,
)

User = get_user_model()


def get_user(*, user_id: str | uuid.UUID) -> Optional[User]:
    """Retrieve a single User by ID or UUID with select_related profile and preferences."""
    try:
        return User.objects.select_related("profile", "preference").get(pk=user_id)
    except (User.DoesNotExist, ValueError):
        return None


def get_user_by_email(*, email: str) -> Optional[User]:
    """Retrieve a single User by email address (case-insensitive) with pre-fetched relations."""
    if not email:
        return None
    try:
        return User.objects.select_related("profile", "preference").get(
            email__iexact=email.strip()
        )
    except User.DoesNotExist:
        return None


def get_user_by_username(*, username: str) -> Optional[User]:
    """Retrieve a single User by username handle (case-insensitive)."""
    if not username:
        return None
    try:
        return User.objects.select_related("profile", "preference").get(
            username__iexact=username.strip()
        )
    except User.DoesNotExist:
        return None


def list_users() -> QuerySet[User]:
    """Return all active non-deleted users ordered by creation date descending."""
    return (
        User.objects.select_related("profile", "preference")
        .all()
        .order_by("-created_at")
    )


def active_users() -> QuerySet[User]:
    """Return only active users ordered by creation date descending."""
    return (
        User.objects.select_related("profile", "preference")
        .active()
        .order_by("-created_at")
    )


def get_user_profile(*, user: User) -> Optional[UserProfile]:
    """Retrieve UserProfile for a given user instance."""
    try:
        return UserProfile.objects.select_related("user").get(user=user)
    except UserProfile.DoesNotExist:
        return None


def get_user_preferences(*, user: User) -> Optional[UserPreference]:
    """Retrieve UserPreference settings for a given user instance."""
    try:
        return UserPreference.objects.select_related("user").get(user=user)
    except UserPreference.DoesNotExist:
        return None


def get_user_devices(*, user: User) -> QuerySet[Device]:
    """Return all devices registered to a user ordered by last active timestamp."""
    return Device.objects.filter(user=user).order_by("-last_active")


def get_active_user_sessions(*, user: User) -> QuerySet[UserSession]:
    """Return active JWT sessions for a user."""
    return (
        UserSession.objects.select_related("device")
        .filter(
            user=user,
            status=SessionStatus.ACTIVE,
            refresh_token_expires_at__gt=timezone.now(),
        )
        .order_by("-last_activity")
    )


def get_user_login_history(*, user: User, limit: int = 50) -> QuerySet[LoginHistory]:
    """Return recent login audit logs for a given user."""
    return (
        LoginHistory.objects.select_related("device")
        .filter(user=user)
        .order_by("-timestamp")[:limit]
    )


def get_valid_password_reset_token(
    *, token_hash: str
) -> Optional[PasswordResetToken]:
    """Retrieve an unused, unexpired password reset token by hash."""
    try:
        return PasswordResetToken.objects.select_related("user").get(
            token_hash=token_hash,
            is_used=False,
            expires_at__gt=timezone.now(),
        )
    except PasswordResetToken.DoesNotExist:
        return None


def get_valid_email_verification_token(
    *, token_hash: str
) -> Optional[EmailVerificationToken]:
    """Retrieve an unused, unexpired email verification token by hash."""
    try:
        return EmailVerificationToken.objects.select_related("user").get(
            token_hash=token_hash,
            is_used=False,
            expires_at__gt=timezone.now(),
        )
    except EmailVerificationToken.DoesNotExist:
        return None
