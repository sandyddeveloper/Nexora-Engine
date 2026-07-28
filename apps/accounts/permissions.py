"""Custom DRF permissions for the accounts app."""

from rest_framework.permissions import BasePermission


class IsAccountOwner(BasePermission):
    """Placeholder permission for future account-specific authorization."""

    def has_permission(self, request, view):
        return True
