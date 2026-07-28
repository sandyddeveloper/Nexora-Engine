"""Validation helpers."""

from django.core.validators import EmailValidator


def is_valid_email(value):
    """Validate an email address using Django's validator."""
    validator = EmailValidator()
    try:
        validator(value)
        return True
    except Exception:
        return False
