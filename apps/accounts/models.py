"""Models for the accounts app."""

from django.contrib.auth.models import AbstractBaseUser, PermissionsMixin
from django.db import models

from apps.common.models import BaseModel

from .managers import UserManager


class User(AbstractBaseUser, PermissionsMixin, BaseModel):
    """Minimal custom user model for Nexora identity management."""

    email = models.EmailField(unique=True)
    username = models.CharField(max_length=150, blank=True, default="")
    first_name = models.CharField(max_length=150, blank=True, default="")
    last_name = models.CharField(max_length=150, blank=True, default="")
    is_active = models.BooleanField(default=True)
    is_staff = models.BooleanField(default=False)

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = ["first_name", "last_name"]

    objects = UserManager()

    class Meta:
        verbose_name = "user"
        verbose_name_plural = "users"

    def __str__(self):
        return self.email or self.username or "User"

    def get_full_name(self):
        return f"{self.first_name} {self.last_name}".strip()

    def get_short_name(self):
        return self.first_name or self.email
