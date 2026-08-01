"""Permissions for the organizations app."""

from rest_framework import permissions


class IsOrganizationAdmin(permissions.BasePermission):
    """Permission check ensuring caller is authenticated and possesses Organization Admin or Staff privileges."""

    def has_permission(self, request, view):
        user = request.user
        if not (user and user.is_authenticated and user.is_active):
            return False
        return bool(user.is_staff or user.is_superuser)

    def has_object_permission(self, request, view, obj):
        user = request.user
        if not (user and user.is_authenticated and user.is_active):
            return False
        if user.is_superuser or user.is_staff:
            return True
        return False
