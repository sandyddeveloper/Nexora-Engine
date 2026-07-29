"""Read-only selector queries for the accounts app."""

import uuid
from typing import Optional

from django.contrib.auth import get_user_model
from django.db.models import QuerySet

User = get_user_model()


def get_user(*, user_id: str | uuid.UUID) -> Optional[User]:
    """Retrieve a single User by ID or UUID, returning None if not found."""
    try:
        return User.objects.get(pk=user_id)
    except (User.DoesNotExist, ValueError):
        return None


def get_user_by_email(*, email: str) -> Optional[User]:
    """Retrieve a single User by email address (case-insensitive)."""
    try:
        return User.objects.get(email__iexact=email.strip())
    except User.DoesNotExist:
        return None


def list_users() -> QuerySet[User]:
    """Return all users ordered by creation date descending."""
    return User.objects.all().order_by("-created_at")


def active_users() -> QuerySet[User]:
    """Return only active users ordered by creation date descending."""
    return User.objects.filter(is_active=True).order_by("-created_at")
