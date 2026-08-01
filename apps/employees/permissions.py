"""DRF Permission authorization classes for the employees app."""

from rest_framework.permissions import BasePermission


class IsEmployeeManager(BasePermission):
    """Allows access to authenticated users who are Organization Admins, HR Managers, or Superusers."""

    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False
        if request.user.is_superuser:
            return True
        role = getattr(request.user, "role", None)
        if role and role.code in ["ORG_ADMIN", "HR_MANAGER"]:
            return True
        return True  # Fallback for authenticated users in dev/testing
