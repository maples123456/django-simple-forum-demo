import json
from datetime import timedelta

from django.contrib.admin.views.decorators import staff_member_required
from django.http import HttpResponseBadRequest, JsonResponse
from django.shortcuts import get_object_or_404, render
from django.utils import timezone
from django.views.decorators.http import require_GET, require_POST

from forum.models import Board, Post

from .events import record_event
from .models import AnalyticsEvent, ProductMetricsDaily, RetentionCohort
from .services import generate_metrics


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


@staff_member_required
def dashboard(request):
    return render(request, 'analytics/dashboard.html')


@require_GET
@staff_member_required
def dashboard_api(request):
    try:
        days = min(max(int(request.GET.get('days', 30)), 7), 90)
    except ValueError:
        return HttpResponseBadRequest('days 必须是整数。')
    end_date = timezone.localdate()
    start_date = end_date - timedelta(days=days - 1)
    metrics = list(ProductMetricsDaily.objects.filter(metric_date__gte=start_date, metric_date__lte=end_date).order_by('metric_date'))
    cohorts = RetentionCohort.objects.filter(cohort_date__gte=start_date, cohort_date__lte=end_date).order_by('-cohort_date', 'retention_day')
    cohort_map = {}
    for row in cohorts:
        item = cohort_map.setdefault(row.cohort_date.isoformat(), {'date': row.cohort_date.isoformat(), 'cohortSize': row.cohort_size})
        item[f'd{row.retention_day}'] = float(row.retention_rate)
    latest = metrics[-1] if metrics else None
    latest_d1 = RetentionCohort.objects.filter(retention_day=1, cohort_size__gt=0).order_by('-cohort_date').first()
    latest_d7 = RetentionCohort.objects.filter(retention_day=7, cohort_size__gt=0).order_by('-cohort_date').first()
    return JsonResponse({
        'summary': {
            'date': latest.metric_date.isoformat() if latest else None,
            'dau': latest.dau if latest else 0,
            'wau': latest.wau if latest else 0,
            'mau': latest.mau if latest else 0,
            'newUsers': latest.new_users if latest else 0,
            'd1Retention': float(latest_d1.retention_rate) if latest_d1 else 0,
            'd7Retention': float(latest_d7.retention_rate) if latest_d7 else 0,
        },
        'trend': [{
            'date': row.metric_date.isoformat(), 'dau': row.dau, 'newUsers': row.new_users,
            'pageViews': row.page_views, 'postViews': row.post_views,
            'posts': row.posts_created, 'replies': row.replies_created, 'likes': row.likes_created,
        } for row in metrics],
        'cohorts': list(cohort_map.values()),
    })


@require_POST
@staff_member_required
def refresh_metrics(request):
    try:
        data = json.loads(request.body or '{}')
        days = min(max(int(data.get('days', 30)), 7), 90)
    except (json.JSONDecodeError, ValueError):
        return HttpResponseBadRequest('参数无效。')
    end_date = timezone.localdate()
    generate_metrics(end_date - timedelta(days=days - 1), end_date)
    return JsonResponse({'ok': True})
