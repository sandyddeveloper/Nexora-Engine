"""Service methods for managing roles."""

import logging

from .models import Role

logger = logging.getLogger("nexora.roles")


def create_role(
    *, name: str, code: str, description: str = "", is_system: bool = False
) -> Role:
    """Create and return a new Role."""
    role = Role.objects.create(
        name=name,
        code=code.upper(),
        description=description,
        is_system=is_system,
    )
    logger.info("Role created: %s (%s)", name, code)
    return role


def update_role(*, role: Role, **fields) -> Role:
    """Update fields on an existing Role."""
    allowed_fields = {"name", "description", "is_active"}
    for field, value in fields.items():
        if field in allowed_fields:
            setattr(role, field, value)
    role.save()
    logger.info("Role updated: %s", role.code)
    return role


def delete_role(*, role: Role) -> bool:
    """Delete a role. System roles cannot be deleted.

    Returns True on success, False if the role is a system role.
    """
    if role.is_system:
        logger.warning("Attempted to delete system role: %s", role.code)
        return False
    role.delete()
    logger.info("Role deleted: %s", role.code)
    return True


def activate_role(*, role: Role) -> Role:
    """Activate a role."""
    role.is_active = True
    role.save(update_fields=["is_active", "updated_at"])
    logger.info("Role activated: %s", role.code)
    return role


def deactivate_role(*, role: Role) -> Role:
    """Deactivate a role."""
    role.is_active = False
    role.save(update_fields=["is_active", "updated_at"])
    logger.info("Role deactivated: %s", role.code)
    return role
