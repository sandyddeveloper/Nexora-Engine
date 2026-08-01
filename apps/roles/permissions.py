"""Permissions for the roles app and RBAC authorization."""

from rest_framework import permissions


class HasRolePermission(permissions.BasePermission):
    """Permission check ensuring user is authenticated and has administrative privileges."""

    def has_permission(self, request, view):
        user = request.user
        if not (user and user.is_authenticated and user.is_active):
            return False
        return bool(user.is_staff or user.is_superuser)
