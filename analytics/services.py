from datetime import datetime, time, timedelta
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.db import transaction
from django.db.models import Count, Q
from django.utils import timezone

from .models import AnalyticsEvent, ProductMetricsDaily, RetentionCohort, UserActivityDaily


EFFECTIVE_EVENTS = ('page_view', 'board_view', 'post_view', 'post_create', 'reply_create', 'post_like')


def _day_range(day):
    current_tz = timezone.get_current_timezone()
    start = timezone.make_aware(datetime.combine(day, time.min), current_tz)
    return start, start + timedelta(days=1)


def _eligible_events(start, end):
    return AnalyticsEvent.objects.filter(
        occurred_at__gte=start,
        occurred_at__lt=end,
        user__isnull=False,
        user__is_staff=False,
        user__is_superuser=False,
    )


def _active_user_count(start_day, end_day):
    start, _ = _day_range(start_day)
    _, end = _day_range(end_day)
    return _eligible_events(start, end).filter(event_name__in=EFFECTIVE_EVENTS).values('user_id').distinct().count()


def visitor_counts(start, end):
    """Return mutually exclusive page-view visitors, stitching anonymous IDs seen after login."""
    page_views = AnalyticsEvent.objects.filter(
        occurred_at__gte=start,
        occurred_at__lt=end,
        event_name='page_view',
    ).filter(
        Q(user__isnull=True) | Q(user__is_staff=False, user__is_superuser=False),
    )
    linked_anonymous_ids = page_views.filter(user__isnull=False).exclude(
        anonymous_id='',
    ).values('anonymous_id')
    logged_visitors = page_views.filter(user__isnull=False).values('user_id').distinct().count()
    anonymous_visitors = page_views.filter(user__isnull=True).exclude(
        anonymous_id='',
    ).exclude(anonymous_id__in=linked_anonymous_ids).values('anonymous_id').distinct().count()
    return {
        'logged_visitors': logged_visitors,
        'anonymous_visitors': anonymous_visitors,
        'all_visitors': logged_visitors + anonymous_visitors,
    }


@transaction.atomic
def generate_day(day):
    User = get_user_model()
    start, end = _day_range(day)
    events = _eligible_events(start, end)
    anonymous_events = AnalyticsEvent.objects.filter(
        occurred_at__gte=start,
        occurred_at__lt=end,
        user__isnull=True,
    )
    new_user_ids = set(User.objects.filter(date_joined__gte=start, date_joined__lt=end, is_staff=False, is_superuser=False).values_list('id', flat=True))
    activity = {
        row['user_id']: row
        for row in events.values('user_id').annotate(
            session_count=Count('session_id', distinct=True, filter=~Q(session_id='')),
            event_count=Count('id'),
            page_view_count=Count('id', filter=Q(event_name='page_view')),
            board_view_count=Count('id', filter=Q(event_name='board_view')),
            post_view_count=Count('id', filter=Q(event_name='post_view')),
            post_count=Count('id', filter=Q(event_name='post_create')),
            reply_count=Count('id', filter=Q(event_name='reply_create')),
            like_count=Count('id', filter=Q(event_name='post_like')),
            unlike_count=Count('id', filter=Q(event_name='post_unlike')),
        )
    }
    UserActivityDaily.objects.filter(activity_date=day).delete()
    UserActivityDaily.objects.bulk_create([
        UserActivityDaily(
            activity_date=day,
            user_id=user_id,
            is_new_user=user_id in new_user_ids,
            session_count=values.get('session_count', 0),
            event_count=values.get('event_count', 0),
            page_view_count=values.get('page_view_count', 0),
            board_view_count=values.get('board_view_count', 0),
            post_view_count=values.get('post_view_count', 0),
            post_count=values.get('post_count', 0),
            reply_count=values.get('reply_count', 0),
            like_count=values.get('like_count', 0),
            unlike_count=values.get('unlike_count', 0),
        )
        for user_id, values in ({user_id: activity.get(user_id, {}) for user_id in set(activity) | new_user_ids}).items()
    ])
    totals = events.aggregate(
        session_count=Count('session_id', distinct=True, filter=~Q(session_id='')),
        page_views=Count('id', filter=Q(event_name='page_view')),
        board_views=Count('id', filter=Q(event_name='board_view')),
        post_views=Count('id', filter=Q(event_name='post_view')),
        page_view_users=Count('user_id', distinct=True, filter=Q(event_name='page_view')),
        board_view_users=Count('user_id', distinct=True, filter=Q(event_name='board_view')),
        post_view_users=Count('user_id', distinct=True, filter=Q(event_name='post_view')),
        posts_created=Count('id', filter=Q(event_name='post_create')),
        posting_users=Count('user_id', distinct=True, filter=Q(event_name='post_create')),
        replies_created=Count('id', filter=Q(event_name='reply_create')),
        replying_users=Count('user_id', distinct=True, filter=Q(event_name='reply_create')),
        likes_created=Count('id', filter=Q(event_name='post_like')),
        liking_users=Count('user_id', distinct=True, filter=Q(event_name='post_like')),
        unlikes_created=Count('id', filter=Q(event_name='post_unlike')),
    )
    anonymous_totals = anonymous_events.aggregate(
        anonymous_page_views=Count('id', filter=Q(event_name='page_view')),
    )
    visitors = visitor_counts(start, end)
    ProductMetricsDaily.objects.update_or_create(metric_date=day, defaults={
        'dau': events.filter(event_name__in=EFFECTIVE_EVENTS).values('user_id').distinct().count(),
        'wau': _active_user_count(day - timedelta(days=6), day),
        'mau': _active_user_count(day - timedelta(days=29), day),
        'new_users': len(new_user_ids),
        **totals,
        **anonymous_totals,
        'anonymous_visitors': visitors['anonymous_visitors'],
    })


def generate_retention(cohort_date, retention_day):
    User = get_user_model()
    cohort_start, cohort_end = _day_range(cohort_date)
    user_ids = set(User.objects.filter(
        date_joined__gte=cohort_start,
        date_joined__lt=cohort_end,
        is_staff=False,
        is_superuser=False,
    ).values_list('id', flat=True))
    target_date = cohort_date + timedelta(days=retention_day)
    target_start, target_end = _day_range(target_date)
    retained = _eligible_events(target_start, target_end).filter(
        user_id__in=user_ids,
        event_name__in=EFFECTIVE_EVENTS,
    ).values('user_id').distinct().count()
    cohort_size = len(user_ids)
    rate = Decimal(retained * 100 / cohort_size).quantize(Decimal('0.01')) if cohort_size else Decimal('0')
    RetentionCohort.objects.update_or_create(
        cohort_date=cohort_date,
        retention_day=retention_day,
        defaults={'cohort_size': cohort_size, 'retained_users': retained, 'retention_rate': rate},
    )
    field = f'd{retention_day}_retention_rate'
    ProductMetricsDaily.objects.filter(metric_date=cohort_date).update(**{field: rate})


def generate_metrics(start_date, end_date):
    day = start_date
    while day <= end_date:
        generate_day(day)
        day += timedelta(days=1)
    observation_end = min(end_date, timezone.localdate() - timedelta(days=1))
    cohort_date = start_date - timedelta(days=30)
    while cohort_date <= end_date:
        for retention_day in (1, 7, 30):
            if cohort_date + timedelta(days=retention_day) <= observation_end:
                generate_retention(cohort_date, retention_day)
            else:
                RetentionCohort.objects.filter(cohort_date=cohort_date, retention_day=retention_day).delete()
                ProductMetricsDaily.objects.filter(metric_date=cohort_date).update(**{f'd{retention_day}_retention_rate': 0})
        cohort_date += timedelta(days=1)
