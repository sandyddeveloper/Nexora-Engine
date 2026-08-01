"""Model managers for the accounts app."""

from django.contrib.auth.base_user import BaseUserManager

from apps.common.models import SoftDeleteQuerySet


class UserManager(BaseUserManager):
    """Manager for creating regular users, superusers, and managing soft delete querysets."""

    def get_queryset(self):
        """Return QuerySet excluding soft-deleted users by default."""
        return SoftDeleteQuerySet(self.model, using=self._db).filter(
            deleted_at__isnull=True
        )

    def active(self):
        """Return active, non-deleted users."""
        return self.get_queryset().filter(is_active=True)

    def deleted(self):
        """Return only soft-deleted users."""
        return SoftDeleteQuerySet(self.model, using=self._db).filter(
            deleted_at__isnull=False
        )

    def with_deleted(self):
        """Return all users including soft-deleted ones."""
        return SoftDeleteQuerySet(self.model, using=self._db)

    def create_user(self, email, username=None, password=None, **extra_fields):
        """Create and save a regular user with given email, username, and password."""
        if not email:
            raise ValueError("The Email field must be set")

        email = self.normalize_email(email)

        if not username:
            base_name = email.split("@")[0]
            username = base_name

        extra_fields.setdefault("username", username)
        extra_fields.setdefault("is_active", True)
        extra_fields.setdefault("email_verified", False)

        # Backward compatibility with is_email_verified kwarg if supplied
        if "is_email_verified" in extra_fields:
            extra_fields["email_verified"] = extra_fields.pop("is_email_verified")

        user = self.model(email=email, **extra_fields)
        if password:
            user.set_password(password)
        else:
            user.set_unusable_password()

        user.save(using=self._db)
        return user

    def create_superuser(self, email, username=None, password=None, **extra_fields):
        """Create and save a superuser with elevated permissions."""
        extra_fields.setdefault("is_staff", True)
        extra_fields.setdefault("is_superuser", True)
        extra_fields.setdefault("is_active", True)
        extra_fields.setdefault("email_verified", True)

        if extra_fields.get("is_staff") is not True:
            raise ValueError("Superuser must have is_staff=True.")
        if extra_fields.get("is_superuser") is not True:
            raise ValueError("Superuser must have is_superuser=True.")

        return self.create_user(
            email=email, username=username, password=password, **extra_fields
        )
