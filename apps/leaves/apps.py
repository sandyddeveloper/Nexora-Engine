"""AppConfig configuration for the Leave Management Foundation Engine application."""

from django.apps import AppConfig


class LeavesConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.leaves"
    verbose_name = "Leave Management Foundation Engine"
