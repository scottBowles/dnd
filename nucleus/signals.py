"""
Signals for updating user activity tracking.
"""
from django.contrib.auth.signals import user_logged_in
from django.dispatch import receiver
from django.utils import timezone
from .models import User


@receiver(user_logged_in)
def update_last_activity_on_login(sender, user, request, **kwargs):
    """
    Update last_activity when user logs in via Django auth.
    This covers admin login and any session-based authentication.
    """
    User.objects.filter(pk=user.pk).update(last_activity=timezone.now())


def update_user_activity(user):
    """
    Helper function to update user activity.
    Can be called from GraphQL resolvers or other parts of the application.
    """
    if user and user.is_authenticated:
        User.objects.filter(pk=user.pk).update(last_activity=timezone.now())
