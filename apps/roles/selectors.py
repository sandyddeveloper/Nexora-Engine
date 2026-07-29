"""Selector methods for querying roles."""

from .models import Role


def get_role(*, role_id) -> Role | None:
    """Retrieve a single role by ID."""
    try:
        return Role.objects.get(id=role_id)
    except Role.DoesNotExist:
        return None


def get_role_by_code(*, code: str) -> Role | None:
    """Retrieve a single role by unique code."""
    try:
        return Role.objects.get(code=code.upper())
    except Role.DoesNotExist:
        return None


def list_roles():
    """Return all roles ordered by name."""
    return Role.objects.all()


def active_roles():
    """Return only active roles."""
    return Role.objects.filter(is_active=True)


def system_roles():
    """Return only system (built-in) roles."""
    return Role.objects.filter(is_system=True)
