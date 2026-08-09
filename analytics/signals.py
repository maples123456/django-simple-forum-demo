from django.contrib.auth import get_user_model
from django.contrib.auth.signals import user_logged_in
from django.db.models.signals import post_save
from django.dispatch import receiver

from .events import record_event


@receiver(post_save, sender=get_user_model())
def record_signup(sender, instance, created, **kwargs):
    if created:
        record_event('sign_up', user=instance)


@receiver(user_logged_in)
def record_login(sender, request, user, **kwargs):
    record_event('login', user=user, session_id=request.session.session_key or '')
