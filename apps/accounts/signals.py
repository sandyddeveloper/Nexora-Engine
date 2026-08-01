"""Signals for the accounts app."""

from django.contrib.auth import get_user_model
from django.db.models.signals import post_save
from django.dispatch import receiver

from .models import UserPreference, UserProfile

User = get_user_model()


@receiver(post_save, sender=User)
def create_user_profile_and_preferences(sender, instance, created, **kwargs):
    """Automatically create UserProfile and UserPreference records when a User is created."""
    if created:
        UserProfile.objects.get_or_create(user=instance)
        UserPreference.objects.get_or_create(user=instance)
