"""Models for the roles app."""

from django.db import models

from apps.common.models import BaseModel


class Role(BaseModel):
    """A named collection of permissions.

    Roles are assigned to users to grant them a set of permissions.
    System roles (is_system=True) are built-in and cannot be deleted.
    """

    name = models.CharField(
        max_length=100,
        help_text="Human-readable role name (e.g. 'Organization Admin').",
    )
    code = models.CharField(
        max_length=50,
        unique=True,
        help_text="Unique uppercase code (e.g. 'ORG_ADMIN').",
    )
    description = models.TextField(
        blank=True,
        default="",
        help_text="Optional description of what this role allows.",
    )
    is_system = models.BooleanField(
        default=False,
        help_text="System roles are built-in and cannot be deleted by users.",
    )

    class Meta:
        verbose_name = "role"
        verbose_name_plural = "roles"
        ordering = ["name"]

    def __str__(self):
        return f"{self.name} ({self.code})"
