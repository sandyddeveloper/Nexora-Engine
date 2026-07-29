"""Custom DRF permissions for the accounts app."""

from rest_framework.permissions import BasePermission


class IsOwner(BasePermission):
    """Permission class to allow access only to the resource owner."""

    def has_object_permission(self, request, view, obj):
        if not (request.user and request.user.is_authenticated):
            return False
        return obj == request.user or getattr(obj, "id", None) == request.user.id


class IsAdmin(BasePermission):
    """Permission class to allow access only to superusers."""

    def has_permission(self, request, view):
        return bool(
            request.user and request.user.is_authenticated and request.user.is_superuser
        )


class IsStaff(BasePermission):
    """Permission class to allow access only to staff members."""

    def has_permission(self, request, view):
        return bool(
            request.user and request.user.is_authenticated and request.user.is_staff
        )
