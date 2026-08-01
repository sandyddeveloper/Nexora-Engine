"""Background Celery tasks for the accounts app with resilient retry policies and failure handling."""

import logging

from celery import shared_task
from django.contrib.auth import get_user_model
from django.utils import timezone

from .models import SessionStatus, UserSession

User = get_user_model()
logger = logging.getLogger("nexora.tasks")


@shared_task(
    name="apps.accounts.tasks.send_verification_email_task",
    autoretry_for=(Exception,),
    retry_backoff=True,
    retry_kwargs={"max_retries": 5},
    time_limit=30,
)
def send_verification_email_task(user_id: str, token: str):
    """Async task to send email verification notification with automatic retry and exponential backoff."""
    try:
        user = User.objects.get(pk=user_id)
        verification_url = f"/verify-email/?token={token}"
        logger.info("Verification email task dispatched for %s: %s", user.email, verification_url)
        return True
    except User.DoesNotExist:
        logger.error("Verification email task failed: User %s not found", user_id)
        return False


@shared_task(
    name="apps.accounts.tasks.send_password_reset_email_task",
    autoretry_for=(Exception,),
    retry_backoff=True,
    retry_kwargs={"max_retries": 5},
    time_limit=30,
)
def send_password_reset_email_task(user_id: str, token: str):
    """Async task to send password reset notification with automatic retry and exponential backoff."""
    try:
        user = User.objects.get(pk=user_id)
        reset_url = f"/reset-password/?token={token}"
        logger.info("Password reset email task dispatched for %s: %s", user.email, reset_url)
        return True
    except User.DoesNotExist:
        logger.error("Password reset email task failed: User %s not found", user_id)
        return False


@shared_task(
    name="apps.accounts.tasks.cleanup_expired_sessions_task",
    time_limit=120,
)
def cleanup_expired_sessions_task():
    """Async periodic task to expire inactive and outdated user sessions."""
    now = timezone.now()
    count = UserSession.objects.filter(
        status=SessionStatus.ACTIVE,
        refresh_token_expires_at__lte=now,
    ).update(status=SessionStatus.EXPIRED, is_current=False)
    logger.info("Cleaned up %d expired user sessions", count)
    return count
