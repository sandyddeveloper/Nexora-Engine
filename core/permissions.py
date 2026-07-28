"""Permission helpers."""

from django.contrib.auth.models import AnonymousUser


def is_authenticated_user(user):
    """Return True when the user is authenticated."""
    return isinstance(user, AnonymousUser) is False and getattr(user, "is_authenticated", False)
