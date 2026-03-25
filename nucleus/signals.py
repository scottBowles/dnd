"""
Signals for updating user activity tracking.
"""
from django.contrib.auth.signals import user_logged_in
from django.dispatch import receiver
from django.utils import timezone
from .models import ActivityType, User, UserActivity


def record_activity(user=None, activity_type=ActivityType.PAGE_VIEW, path=None, metadata=None):
    """
    Record a user activity event and update User model fields.
    Creates a UserActivity row, updates User.last_activity always,
    and updates User.last_login for LOGIN activity type.
    user can be None for anonymous activity.
    """
    UserActivity.objects.create(
        user=user,
        activity_type=activity_type,
        path=path,
        metadata=metadata,
    )
    if user and user.is_authenticated:
        now = timezone.now()
        update_fields = {"last_activity": now}
        if activity_type == ActivityType.LOGIN:
            update_fields["last_login"] = now
        User.objects.filter(pk=user.pk).update(**update_fields)


@receiver(user_logged_in)
def update_last_activity_on_login(sender, user, request, **kwargs):
    """
    Update last_activity when user logs in via Django auth.
    This covers admin login and any session-based authentication.
    """
    record_activity(user=user, activity_type=ActivityType.LOGIN)


def update_user_activity(user):
    """
    Helper function to update user activity.
    Can be called from GraphQL resolvers or other parts of the application.
    Delegates to record_activity for backward compatibility.
    """
    if user and user.is_authenticated:
        record_activity(user=user, activity_type=ActivityType.LOGIN)
