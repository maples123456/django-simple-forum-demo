import json
from datetime import timedelta

from django.contrib.admin.views.decorators import staff_member_required
from django.http import HttpResponseBadRequest, JsonResponse
from django.db.models import Count, Max, Q, Sum
from django.shortcuts import get_object_or_404, render
from django.utils import timezone
from django.views.decorators.http import require_GET, require_POST
from django.views.decorators.cache import never_cache

from forum.models import Board, Post

from .events import record_event
from .models import AnalyticsEvent, ProductMetricsDaily, RetentionCohort, UserActivityDaily
from .services import EFFECTIVE_EVENTS, _day_range, generate_metrics


BROWSER_EVENTS = {'page_view', 'board_view', 'post_view'}


@require_POST
def track_event(request):
    try:
        data = json.loads(request.body)
    except (json.JSONDecodeError, UnicodeDecodeError):
        return HttpResponseBadRequest('无效的 JSON。')
    event_name = data.get('eventName')
    if event_name not in BROWSER_EVENTS:
        return HttpResponseBadRequest('不允许的事件类型。')
    board = get_object_or_404(Board, pk=data['boardId']) if data.get('boardId') else None
    post = get_object_or_404(Post, pk=data['postId']) if data.get('postId') else None
    record_event(
        event_name,
        user=request.user,
        board=board,
        post=post,
        source=AnalyticsEvent.Source.REACT,
        anonymous_id=str(data.get('anonymousId', '')),
        session_id=str(data.get('sessionId', '')),
        properties=data.get('properties') if isinstance(data.get('properties'), dict) else {},
    )
    return JsonResponse({'ok': True}, status=201)


@never_cache
@staff_member_required
def dashboard(request):
    return render(request, 'analytics/dashboard.html')


@never_cache
@require_GET
@staff_member_required
def dashboard_api(request):
    try:
        days = min(max(int(request.GET.get('days', 30)), 7), 90)
    except ValueError:
        return HttpResponseBadRequest('days 必须是整数。')
    end_date = timezone.localdate() - timedelta(days=1)
    start_date = end_date - timedelta(days=days - 1)
    start_time, _ = _day_range(start_date)
    _, end_time = _day_range(end_date)
    metrics = list(ProductMetricsDaily.objects.filter(metric_date__gte=start_date, metric_date__lte=end_date).order_by('metric_date'))
    cohorts = RetentionCohort.objects.filter(cohort_date__gte=start_date, cohort_date__lte=end_date).order_by('-cohort_date', 'retention_day')
    user_daily = UserActivityDaily.objects.filter(activity_date__gte=start_date, activity_date__lte=end_date)
    events = AnalyticsEvent.objects.filter(
        occurred_at__gte=start_time,
        occurred_at__lt=end_time,
        user__isnull=False,
        user__is_staff=False,
        user__is_superuser=False,
    )
    cohort_map = {}
    for row in cohorts:
        item = cohort_map.setdefault(row.cohort_date.isoformat(), {'date': row.cohort_date.isoformat(), 'cohortSize': row.cohort_size})
        item[f'd{row.retention_day}'] = float(row.retention_rate)
    latest = metrics[-1] if metrics else None
    retention = {}
    for retention_day in (1, 7):
        totals = cohorts.filter(retention_day=retention_day, cohort_size__gt=0).aggregate(
            cohort_size=Sum('cohort_size'),
            retained_users=Sum('retained_users'),
        )
        retention[retention_day] = round(totals['retained_users'] * 100 / totals['cohort_size'], 2) if totals['cohort_size'] else 0

    active_users = events.filter(event_name__in=EFFECTIVE_EVENTS).values('user_id').distinct().count()
    interaction_users = {
        'posting': events.filter(event_name='post_create').values('user_id').distinct().count(),
        'replying': events.filter(event_name='reply_create').values('user_id').distinct().count(),
        'liking': events.filter(event_name='post_like').values('user_id').distinct().count(),
    }
    funnel = [
        {'name': '访问论坛', 'users': user_daily.filter(page_view_count__gt=0).values('user_id').distinct().count()},
        {'name': '浏览板块', 'users': user_daily.filter(board_view_count__gt=0).values('user_id').distinct().count()},
        {'name': '浏览帖子', 'users': user_daily.filter(post_view_count__gt=0).values('user_id').distinct().count()},
        {'name': '产生互动', 'users': events.filter(event_name__in=('post_create', 'reply_create', 'post_like')).values('user_id').distinct().count()},
    ]

    segment_counts = {'新增未活跃': 0, '只读用户': 0, '轻互动用户': 0, '讨论用户': 0, '创作者': 0}
    user_rollups = user_daily.values('user_id').annotate(
        is_new=Max('is_new_user'),
        views=Sum('page_view_count') + Sum('board_view_count') + Sum('post_view_count'),
        posts=Sum('post_count'),
        replies=Sum('reply_count'),
        likes=Sum('like_count'),
    )
    for row in user_rollups:
        if row['posts']:
            segment_counts['创作者'] += 1
        elif row['replies']:
            segment_counts['讨论用户'] += 1
        elif row['likes']:
            segment_counts['轻互动用户'] += 1
        elif row['views']:
            segment_counts['只读用户'] += 1
        elif row['is_new']:
            segment_counts['新增未活跃'] += 1

    board_rows = events.filter(board__isnull=False).values('board_id', 'board__name').annotate(
        users=Count('user_id', distinct=True),
        views=Count('id', filter=Q(event_name='post_view')),
        posts=Count('id', filter=Q(event_name='post_create')),
        replies=Count('id', filter=Q(event_name='reply_create')),
        likes=Count('id', filter=Q(event_name='post_like')),
    ).order_by('-views')
    post_rows = events.filter(post__isnull=False).values('post_id', 'post__title', 'board__name').annotate(
        viewers=Count('user_id', distinct=True, filter=Q(event_name='post_view')),
        views=Count('id', filter=Q(event_name='post_view')),
        replies=Count('id', filter=Q(event_name='reply_create')),
        likes=Count('id', filter=Q(event_name='post_like')),
    ).filter(views__gt=0).order_by('-views')[:18]

    period_totals = {
        'sessions': sum(row.session_count for row in metrics),
        'postViews': sum(row.post_views for row in metrics),
        'posts': sum(row.posts_created for row in metrics),
        'replies': sum(row.replies_created for row in metrics),
        'likes': sum(row.likes_created for row in metrics),
    }
    anonymous_events = AnalyticsEvent.objects.filter(occurred_at__gte=start_time, occurred_at__lt=end_time, user__isnull=True)
    period_totals['anonymousVisitors'] = anonymous_events.exclude(anonymous_id='').values('anonymous_id').distinct().count()

    def percentage(numerator, denominator):
        return round(numerator * 100 / denominator, 2) if denominator else 0

    return JsonResponse({
        'summary': {
            'date': latest.metric_date.isoformat() if latest else None,
            'dau': latest.dau if latest else 0,
            'wau': latest.wau if latest else 0,
            'mau': latest.mau if latest else 0,
            'newUsers': latest.new_users if latest else 0,
            'd1Retention': retention[1],
            'd7Retention': retention[7],
            'activeUsers': active_users,
            'anonymousVisitors': period_totals['anonymousVisitors'],
            'postViewDepth': round(period_totals['postViews'] / active_users, 2) if active_users else 0,
            'creatorRate': percentage(interaction_users['posting'], active_users),
            'discussionRate': percentage(interaction_users['replying'], active_users),
        },
        'trend': [{
            'date': row.metric_date.isoformat(), 'dau': row.dau, 'wau': row.wau, 'mau': row.mau, 'newUsers': row.new_users,
            'dauWau': percentage(row.dau, row.wau), 'dauMau': percentage(row.dau, row.mau),
            'sessions': row.session_count, 'pageViews': row.page_views, 'boardViews': row.board_views, 'postViews': row.post_views,
            'pageViewUsers': row.page_view_users, 'boardViewUsers': row.board_view_users, 'postViewUsers': row.post_view_users,
            'posts': row.posts_created, 'postingUsers': row.posting_users,
            'replies': row.replies_created, 'replyingUsers': row.replying_users,
            'likes': row.likes_created, 'likingUsers': row.liking_users, 'unlikes': row.unlikes_created,
            'anonymousVisitors': row.anonymous_visitors, 'anonymousPageViews': row.anonymous_page_views,
        } for row in metrics],
        'cohorts': list(cohort_map.values()),
        'funnel': funnel,
        'segments': [{'name': name, 'value': value} for name, value in segment_counts.items()],
        'boards': [{'id': row['board_id'], 'name': row['board__name'], 'users': row['users'], 'views': row['views'], 'posts': row['posts'], 'replies': row['replies'], 'likes': row['likes']} for row in board_rows],
        'posts': [{'id': row['post_id'], 'title': row['post__title'], 'board': row['board__name'], 'viewers': row['viewers'], 'views': row['views'], 'replies': row['replies'], 'likes': row['likes']} for row in post_rows],
        'period': {**period_totals, **interaction_users},
    })


@never_cache
@require_POST
@staff_member_required
def refresh_metrics(request):
    try:
        data = json.loads(request.body or '{}')
        days = min(max(int(data.get('days', 30)), 7), 90)
    except (json.JSONDecodeError, ValueError):
        return HttpResponseBadRequest('参数无效。')
    end_date = timezone.localdate() - timedelta(days=1)
    generate_metrics(end_date - timedelta(days=days - 1), end_date)
    return JsonResponse({'ok': True})
