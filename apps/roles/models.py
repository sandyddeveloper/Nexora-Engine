"""Models for the roles app."""

from django.conf import settings
from django.db import models
from django.utils.translation import gettext_lazy as _

from apps.common.models import BaseModel


class Role(BaseModel):
    """A named collection of permissions.

    Roles are assigned to users to grant them a set of permissions.
    System roles (is_system=True) are built-in and cannot be deleted.
    """

    name = models.CharField(
        max_length=100,
        help_text=_("Human-readable role name (e.g. 'Organization Admin')."),
    )
    code = models.CharField(
        max_length=50,
        unique=True,
        help_text=_("Unique uppercase code (e.g. 'ORG_ADMIN')."),
    )
    description = models.TextField(
        blank=True,
        default="",
        help_text=_("Optional description of what this role allows."),
    )
    is_system = models.BooleanField(
        default=False,
        help_text=_("System roles are built-in and cannot be deleted by users."),
    )

    class Meta:
        verbose_name = _("role")
        verbose_name_plural = _("roles")
        ordering = ["name"]

    def __str__(self) -> str:
        return f"{self.name} ({self.code})"


class UserRole(BaseModel):
    """Assignment of a Role to a User with optional organization scoping."""

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="user_roles",
        help_text=_("User granted this role."),
    )
    role = models.ForeignKey(
        Role,
        on_delete=models.CASCADE,
        related_name="user_assignments",
        help_text=_("Role granted to user."),
    )
    organization_id = models.UUIDField(
        null=True,
        blank=True,
        db_index=True,
        help_text=_("Optional organization UUID scope for role assignment."),
    )

    class Meta:
        verbose_name = _("user role")
        verbose_name_plural = _("user roles")
        indexes = [
            models.Index(fields=["user", "role"], name="idx_userrole_user_role"),
            models.Index(
                fields=["user", "organization_id"], name="idx_userrole_user_org"
            ),
        ]
        constraints = [
            models.UniqueConstraint(
                fields=["user", "role", "organization_id"],
                name="unique_user_role_org",
            )
        ]

    def __str__(self) -> str:
        org_str = f" in org {self.organization_id}" if self.organization_id else ""
        return f"{self.user.email} - {self.role.code}{org_str}"
