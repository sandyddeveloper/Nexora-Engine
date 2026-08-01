"""Common base models, querysets, and managers for Nexora Engine."""

import uuid

from django.conf import settings
from django.db import models
from django.utils import timezone


class SoftDeleteQuerySet(models.QuerySet):
    """QuerySet supporting soft deletion and restoring records."""

    def active(self):
        """Filter records that are active and not soft-deleted."""
        return self.filter(deleted_at__isnull=True, is_active=True)

    def deleted(self):
        """Filter records that are soft-deleted."""
        return self.filter(deleted_at__isnull=False)

    def with_deleted(self):
        """Include soft-deleted records in the queryset."""
        return self

    def delete(self, soft: bool = True):
        """Soft delete records in the queryset by setting deleted_at."""
        if soft:
            return self.update(deleted_at=timezone.now(), is_active=False)
        return super().delete()

    def hard_delete(self):
        """Permanently delete records in the queryset from the database."""
        return super().delete()

    def restore(self):
        """Restore soft-deleted records in the queryset."""
        return self.update(deleted_at=None, is_active=True)


class SoftDeleteManager(models.Manager):
    """Default manager filtering out soft-deleted objects."""

    def get_queryset(self):
        """Return QuerySet excluding soft-deleted instances by default."""
        return SoftDeleteQuerySet(self.model, using=self._db).filter(
            deleted_at__isnull=True
        )

    def active(self):
        """Return active, non-deleted instances."""
        return self.get_queryset().active()

    def deleted(self):
        """Return only soft-deleted instances."""
        return SoftDeleteQuerySet(self.model, using=self._db).deleted()

    def with_deleted(self):
        """Return all instances including soft-deleted ones."""
        return SoftDeleteQuerySet(self.model, using=self._db)


class BaseModel(models.Model):
    """Shared base model for all Nexora application entities.

    Provides UUID primary keys, timestamp tracking, audit fields (created_by/updated_by),
    is_active status, and soft deletion capabilities.
    """

    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False,
        help_text="Unique Identifier (UUIDv4) for entity.",
    )
    created_at = models.DateTimeField(
        auto_now_add=True,
        db_index=True,
        help_text="Timestamp when the entity was created.",
    )
    updated_at = models.DateTimeField(
        auto_now=True,
        help_text="Timestamp when the entity was last updated.",
    )
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="%(class)s_created_by",
        help_text="User who created this entity.",
    )
    updated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="%(class)s_updated_by",
        help_text="User who last updated this entity.",
    )
    deleted_at = models.DateTimeField(
        null=True,
        blank=True,
        db_index=True,
        help_text="Timestamp when entity was soft-deleted, null if active.",
    )
    is_active = models.BooleanField(
        default=True,
        help_text="Designates whether this record is active.",
    )

    objects = SoftDeleteManager()

    class Meta:
        abstract = True

    @property
    def is_deleted(self) -> bool:
        """Return True if the entity is soft-deleted."""
        return self.deleted_at is not None

    def delete(self, using=None, keep_parents=False, soft: bool = True):
        """Soft-delete entity by setting deleted_at timestamp unless soft=False."""
        if soft:
            self.deleted_at = timezone.now()
            self.is_active = False
            self.save(update_fields=["deleted_at", "is_active", "updated_at"])
            return 1, {self._meta.label: 1}
        return super().delete(using=using, keep_parents=keep_parents)

    def hard_delete(self, using=None, keep_parents=False):
        """Permanently delete entity from the database."""
        return super().delete(using=using, keep_parents=keep_parents)

    def restore(self):
        """Restore soft-deleted entity."""
        self.deleted_at = None
        self.is_active = True
        self.save(update_fields=["deleted_at", "is_active", "updated_at"])
