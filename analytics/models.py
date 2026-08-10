import uuid

from django.conf import settings
from django.db import models
from django.utils import timezone


class AnalyticsEvent(models.Model):
    class Source(models.TextChoices):
        REACT = 'react', 'React'
        DJANGO = 'django', 'Django'

    event_id = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)
    event_name = models.CharField(max_length=40, db_index=True)
    occurred_at = models.DateTimeField(default=timezone.now, db_index=True)
    received_at = models.DateTimeField(auto_now_add=True)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL, related_name='analytics_events')
    anonymous_id = models.CharField(max_length=64, blank=True, db_index=True)
    session_id = models.CharField(max_length=64, blank=True, db_index=True)
    board = models.ForeignKey('forum.Board', null=True, blank=True, on_delete=models.SET_NULL, related_name='+')
    post = models.ForeignKey('forum.Post', null=True, blank=True, on_delete=models.SET_NULL, related_name='+')
    properties = models.JSONField(default=dict, blank=True)
    source = models.CharField(max_length=12, choices=Source.choices)

    class Meta:
        ordering = ['-occurred_at']
        indexes = [
            models.Index(fields=['occurred_at', 'user']),
            models.Index(fields=['event_name', 'occurred_at']),
        ]

    def __str__(self):
        return f'{self.event_name} · {self.occurred_at:%Y-%m-%d %H:%M}'


class UserActivityDaily(models.Model):
    activity_date = models.DateField(db_index=True)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='+')
    is_new_user = models.BooleanField(default=False)
    session_count = models.PositiveIntegerField(default=0)
    event_count = models.PositiveIntegerField(default=0)
    page_view_count = models.PositiveIntegerField(default=0)
    board_view_count = models.PositiveIntegerField(default=0)
    post_view_count = models.PositiveIntegerField(default=0)
    post_count = models.PositiveIntegerField(default=0)
    reply_count = models.PositiveIntegerField(default=0)
    like_count = models.PositiveIntegerField(default=0)
    unlike_count = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ['-activity_date', 'user_id']
        constraints = [models.UniqueConstraint(fields=['activity_date', 'user'], name='unique_user_activity_day')]


class ProductMetricsDaily(models.Model):
    metric_date = models.DateField(primary_key=True)
    dau = models.PositiveIntegerField(default=0)
    wau = models.PositiveIntegerField(default=0)
    mau = models.PositiveIntegerField(default=0)
    new_users = models.PositiveIntegerField(default=0)
    session_count = models.PositiveIntegerField(default=0)
    page_views = models.PositiveIntegerField(default=0)
    board_views = models.PositiveIntegerField(default=0)
    post_views = models.PositiveIntegerField(default=0)
    page_view_users = models.PositiveIntegerField(default=0)
    board_view_users = models.PositiveIntegerField(default=0)
    post_view_users = models.PositiveIntegerField(default=0)
    posts_created = models.PositiveIntegerField(default=0)
    posting_users = models.PositiveIntegerField(default=0)
    replies_created = models.PositiveIntegerField(default=0)
    replying_users = models.PositiveIntegerField(default=0)
    likes_created = models.PositiveIntegerField(default=0)
    liking_users = models.PositiveIntegerField(default=0)
    unlikes_created = models.PositiveIntegerField(default=0)
    anonymous_visitors = models.PositiveIntegerField(default=0)
    anonymous_page_views = models.PositiveIntegerField(default=0)
    d1_retention_rate = models.DecimalField(max_digits=6, decimal_places=2, default=0)
    d7_retention_rate = models.DecimalField(max_digits=6, decimal_places=2, default=0)
    d30_retention_rate = models.DecimalField(max_digits=6, decimal_places=2, default=0)
    generated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-metric_date']


class RetentionCohort(models.Model):
    cohort_date = models.DateField(db_index=True)
    retention_day = models.PositiveSmallIntegerField()
    cohort_size = models.PositiveIntegerField(default=0)
    retained_users = models.PositiveIntegerField(default=0)
    retention_rate = models.DecimalField(max_digits=6, decimal_places=2, default=0)

    class Meta:
        ordering = ['-cohort_date', 'retention_day']
        constraints = [models.UniqueConstraint(fields=['cohort_date', 'retention_day'], name='unique_retention_cohort_day')]

# Create your models here.
