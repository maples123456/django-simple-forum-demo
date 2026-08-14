import json
from datetime import timedelta
from statistics import median

from django.contrib.admin.views.decorators import staff_member_required
from django.http import HttpResponseBadRequest, JsonResponse
from django.db.models import Count, Min, Q, Sum
from django.shortcuts import get_object_or_404, render
from django.utils import timezone
from django.views.decorators.http import require_GET, require_POST
from django.views.decorators.cache import never_cache

from forum.models import Board, Post

from .events import record_event
from .models import AnalyticsEvent, BehaviorRetentionCohort, ProductMetricsDaily, RetentionCohort, UserActivityDaily
from .services import EFFECTIVE_EVENTS, _day_range, anonymous_registration_count, generate_metrics, visitor_counts


BROWSER_EVENTS = {'page_view', 'board_view', 'post_view'}
METRIC_CONTRACTS = [
    {'metric': '全站访客', 'definition': '至少产生一次 page_view 的可识别访客。已登录 user_id 与未登录 anonymous_id 互斥；窗口内曾登录的 anonymous_id 归入登录访客。', 'numerator': '登录访客 + 纯匿名访客', 'denominator': '无', 'dedupe': 'user_id；anonymous_id', 'window': '所选完整自然日窗口', 'scope': '普通登录用户 + 匿名访客'},
    {'metric': '登录访客', 'definition': '至少产生一次 page_view 的普通登录用户。', 'numerator': '登录浏览用户数', 'denominator': '无', 'dedupe': 'user_id', 'window': '所选完整自然日窗口', 'scope': '排除 staff 和 superuser'},
    {'metric': '匿名访客', 'definition': '产生 page_view、没有登录 user_id，且 anonymous_id 未在窗口内关联登录用户的访客。', 'numerator': '纯匿名浏览身份数', 'denominator': '无', 'dedupe': 'anonymous_id', 'window': '所选完整自然日窗口', 'scope': '只含非空 anonymous_id'},
    {'metric': '匿名 UV 与注册转化', 'definition': '匿名 UV 包含窗口内以未登录状态浏览的 anonymous_id；仅当同一 anonymous_id 后续关联到窗口内注册用户，才计为匿名注册转化。', 'numerator': '可归因匿名注册用户数', 'denominator': '窗口匿名 UV', 'dedupe': '分子按 user_id；分母按 anonymous_id', 'window': '所选完整自然日窗口，要求先浏览后注册', 'scope': '匿名 page_view 与普通注册用户'},
    {'metric': 'DAU / WAU / MAU', 'definition': '至少产生一次有效论坛行为的普通登录用户。WAU、MAU 是滚动窗口去重，不是 DAU 求和。', 'numerator': '有效活跃用户数', 'denominator': '无', 'dedupe': 'user_id', 'window': '1 / 7 / 30 个完整自然日', 'scope': '排除匿名、staff 和 superuser'},
    {'metric': 'DAU/WAU · DAU/MAU', 'definition': '活跃频率指标，表示滚动活跃用户中当天也活跃的比例，不是留存率。', 'numerator': '当天 DAU', 'denominator': '当天 WAU / MAU', 'dedupe': '分子分母均按 user_id', 'window': '同一指标日期', 'scope': '普通登录用户'},
    {'metric': '人均帖子浏览', 'definition': '窗口内普通登录用户平均产生的帖子浏览动作数；不是每次会话的浏览深度。', 'numerator': 'post_view 事件数', 'denominator': '窗口有效活跃用户数', 'dedupe': '分母按 user_id；分子不去重', 'window': '所选完整自然日窗口', 'scope': '普通登录用户'},
    {'metric': '新增激活率', 'definition': '注册当天至少产生一次有效论坛行为的新用户比例；只注册或只登录不算激活。', 'numerator': '注册日有效活跃的新用户', 'denominator': '当天注册普通用户', 'dedupe': 'user_id', 'window': '注册自然日，同日激活', 'scope': '普通登录用户'},
    {'metric': '创作者率', 'definition': '所选窗口活跃用户中至少发过一次帖的用户比例。', 'numerator': '发帖用户数', 'denominator': '窗口有效活跃用户数', 'dedupe': 'user_id', 'window': '所选完整自然日窗口', 'scope': '普通登录用户'},
    {'metric': '讨论参与率', 'definition': '所选窗口活跃用户中至少回复过一次的用户比例。', 'numerator': '回复用户数', 'denominator': '窗口有效活跃用户数', 'dedupe': 'user_id', 'window': '所选完整自然日窗口', 'scope': '普通登录用户'},
    {'metric': '点赞动作', 'definition': 'post_like 事件发生次数；同一用户可产生多次，不代表当前仍保持点赞。', 'numerator': 'post_like 事件数', 'denominator': '无', 'dedupe': '不按用户去重', 'window': '所选完整自然日窗口', 'scope': '普通登录用户'},
    {'metric': '点赞用户', 'definition': '所选窗口至少产生一次 post_like 的用户数。', 'numerator': '点赞用户数', 'denominator': '无', 'dedupe': 'user_id', 'window': '所选完整自然日窗口', 'scope': '普通登录用户'},
    {'metric': '净点赞变化', 'definition': '窗口内点赞动作减去取消点赞动作，可以为负数；它是流量变化而非当前存量。', 'numerator': 'post_like 次数 − post_unlike 次数', 'denominator': '无', 'dedupe': '不去重，按事件计数', 'window': '所选完整自然日窗口', 'scope': '普通登录用户'},
    {'metric': '当前点赞', 'definition': '查询时仍保留在 Post.likes 关系中的点赞总数，是当前状态快照。', 'numerator': '当前有效帖子—用户点赞关系数', 'denominator': '无', 'dedupe': 'post_id + user_id', 'window': '查询时点', 'scope': '普通登录用户'},
    {'metric': '内容消费漏斗', 'definition': '分别统计窗口内到达 page_view、board_view、post_view 和互动阶段的用户；当前是阶段到达漏斗，不要求同一会话严格按顺序发生。', 'numerator': '各阶段到达用户数', 'denominator': '转化率分母为上一阶段用户数', 'dedupe': '每阶段按 user_id', 'window': '所选完整自然日窗口', 'scope': '普通登录用户'},
    {'metric': '用户参与层级', 'definition': '按窗口内最深行为互斥分类：创作者优先，互动用户包含回复或点赞，剩余有浏览的用户为只读。未激活用户不进入活跃分层。', 'numerator': '各互斥层级用户数', 'denominator': '窗口有效活跃用户', 'dedupe': '每个 user_id 只进入一个层级', 'window': '所选完整自然日窗口', 'scope': '普通登录用户'},
    {'metric': '内容供给与互动', 'definition': '发帖、回复、点赞和帖子浏览均按事件动作计数，反映行为量而非参与用户数。', 'numerator': '对应事件数', 'denominator': '无', 'dedupe': '不按用户去重', 'window': '每个完整自然日', 'scope': '普通登录用户'},
    {'metric': '板块贡献', 'definition': '将窗口内带有 board_id 的帖子浏览、回复和点赞事件按板块分组。', 'numerator': '各板块对应事件数', 'denominator': '无', 'dedupe': '不按用户去重', 'window': '所选完整自然日窗口', 'scope': '普通登录用户'},
    {'metric': '帖子健康度', 'definition': '每个气泡代表帖子；浏览与回复是窗口事件量，气泡大小是查询时当前点赞存量。', 'numerator': 'post_view、reply_create 事件；当前点赞关系', 'denominator': '无', 'dedupe': '事件不去重；当前点赞按 post_id + user_id', 'window': '行为为所选窗口；点赞为查询时点', 'scope': '普通登录用户'},
    {'metric': '每帖回复数', 'definition': '窗口内新建帖截至窗口结束收到的普通用户回复数，除以同一批新帖数量。零回复帖也进入分母。', 'numerator': '新帖收到的回复总数', 'denominator': '窗口新帖数', 'dedupe': 'reply_id；post_id', 'window': '发帖日在所选窗口，回复观察截至窗口结束', 'scope': '普通用户发布的帖子和回复'},
    {'metric': '零回复帖子率', 'definition': '窗口内新建帖截至窗口结束仍没有普通用户回复的比例。', 'numerator': '零回复新帖数', 'denominator': '窗口新帖数', 'dedupe': 'post_id', 'window': '发帖日在所选窗口，回复观察截至窗口结束', 'scope': '普通用户发布的帖子和回复'},
    {'metric': '首次回复时间', 'definition': '从发帖到第一条普通用户回复的小时数，展示已获回复帖的中位数；零回复帖不进入该时长计算。', 'numerator': '各已回复帖首次回复耗时的中位数', 'denominator': '无', 'dedupe': '每帖仅取最早 reply.created_at', 'window': '发帖日在所选窗口，回复观察截至窗口结束', 'scope': '普通用户发布的帖子和回复'},
    {'metric': '板块级指标', 'definition': '在 board_id 粒度分别计算活跃用户、浏览、发帖、回复和点赞；用户数不能跨板块相加推导全站用户数。', 'numerator': '各板块用户数或事件数', 'denominator': '互动率使用板块活跃用户', 'dedupe': '用户指标按 board_id + user_id；动作不去重', 'window': '所选完整自然日窗口', 'scope': '普通登录用户'},
    {'metric': '首日行为与留存', 'definition': '按注册日最深行为将新增用户互斥分为未激活、只读、互动、创作者，再比较 exact-day D1/D7 留存。表示关联，不证明因果。', 'numerator': '目标日活跃的分层 Cohort 用户', 'denominator': '对应首日行为分层的成熟 Cohort 用户', 'dedupe': 'user_id', 'window': '注册日分层；D1/D7 仅成熟 Cohort', 'scope': '普通登录用户'},
    {'metric': '创作者留存', 'definition': '注册首日发帖的新用户在第 1/7 个自然日再次产生有效行为的 exact-day 留存。', 'numerator': '目标日活跃的首日创作者', 'denominator': '已成熟的首日创作者 Cohort', 'dedupe': 'user_id', 'window': '注册日分层与 D1/D7 观察日', 'scope': '普通登录用户'},
    {'metric': 'D1 / D7 留存', 'definition': '注册 Cohort 用户在注册后第 1 / 7 个自然日再次产生有效行为的 exact-day 留存。', 'numerator': '目标日活跃的 Cohort 用户', 'denominator': '对应注册日 Cohort 用户数', 'dedupe': 'user_id', 'window': '仅展示观察期已成熟 Cohort', 'scope': '普通登录用户'},
]


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

    def percentage(numerator, denominator):
        return round(numerator * 100 / denominator, 2) if denominator else 0

    active_users = events.filter(event_name__in=EFFECTIVE_EVENTS).values('user_id').distinct().count()
    interaction_users = {
        'posting': events.filter(event_name='post_create').values('user_id').distinct().count(),
        'replying': events.filter(event_name='reply_create').values('user_id').distinct().count(),
        'liking': events.filter(event_name='post_like').values('user_id').distinct().count(),
    }
    visitors = visitor_counts(start_time, end_time)
    anonymous_registrations = anonymous_registration_count(start_time, end_time)
    funnel = [
        {'name': '访问论坛', 'users': user_daily.filter(page_view_count__gt=0).values('user_id').distinct().count()},
        {'name': '浏览板块', 'users': user_daily.filter(board_view_count__gt=0).values('user_id').distinct().count()},
        {'name': '浏览帖子', 'users': user_daily.filter(post_view_count__gt=0).values('user_id').distinct().count()},
        {'name': '产生互动', 'users': events.filter(event_name__in=('post_create', 'reply_create', 'post_like')).values('user_id').distinct().count()},
    ]

    segment_counts = {'只读用户': 0, '互动用户': 0, '创作者': 0}
    user_rollups = user_daily.values('user_id').annotate(
        views=Sum('page_view_count') + Sum('board_view_count') + Sum('post_view_count'),
        posts=Sum('post_count'),
        replies=Sum('reply_count'),
        likes=Sum('like_count'),
    )
    for row in user_rollups:
        if row['posts']:
            segment_counts['创作者'] += 1
        elif row['replies'] or row['likes']:
            segment_counts['互动用户'] += 1
        elif row['views']:
            segment_counts['只读用户'] += 1

    board_rows = events.filter(board__isnull=False).values('board_id', 'board__name').annotate(
        active_users=Count('user_id', distinct=True, filter=Q(event_name__in=EFFECTIVE_EVENTS)),
        views=Count('id', filter=Q(event_name='post_view')),
        view_users=Count('user_id', distinct=True, filter=Q(event_name='post_view')),
        posts=Count('id', filter=Q(event_name='post_create')),
        posting_users=Count('user_id', distinct=True, filter=Q(event_name='post_create')),
        replies=Count('id', filter=Q(event_name='reply_create')),
        replying_users=Count('user_id', distinct=True, filter=Q(event_name='reply_create')),
        likes=Count('id', filter=Q(event_name='post_like')),
        liking_users=Count('user_id', distinct=True, filter=Q(event_name='post_like')),
        interaction_users=Count('user_id', distinct=True, filter=Q(event_name__in=('reply_create', 'post_like'))),
    ).order_by('-views')
    post_rows = list(events.filter(post__isnull=False).values('post_id', 'post__title', 'board__name').annotate(
        viewers=Count('user_id', distinct=True, filter=Q(event_name='post_view')),
        views=Count('id', filter=Q(event_name='post_view')),
        replies=Count('id', filter=Q(event_name='reply_create')),
        like_actions=Count('id', filter=Q(event_name='post_like')),
    ).filter(views__gt=0).order_by('-views')[:18])
    current_likes = {
        row['id']: row['current_likes']
        for row in Post.objects.filter(id__in=[item['post_id'] for item in post_rows]).annotate(
            current_likes=Count('likes', filter=Q(likes__is_staff=False, likes__is_superuser=False)),
        ).values('id', 'current_likes')
    }

    content_posts = list(Post.objects.filter(
        created_at__gte=start_time,
        created_at__lt=end_time,
        author__is_staff=False,
        author__is_superuser=False,
    ).annotate(
        observed_replies=Count('replies', filter=Q(
            replies__created_at__lt=end_time,
            replies__author__is_staff=False,
            replies__author__is_superuser=False,
        )),
        first_reply_at=Min('replies__created_at', filter=Q(
            replies__created_at__lt=end_time,
            replies__author__is_staff=False,
            replies__author__is_superuser=False,
        )),
    ).values('id', 'created_at', 'observed_replies', 'first_reply_at'))
    first_reply_hours = [
        (row['first_reply_at'] - row['created_at']).total_seconds() / 3600
        for row in content_posts if row['first_reply_at'] is not None
    ]
    post_count = len(content_posts)
    content_health = {
        'postCount': post_count,
        'repliesPerPost': round(sum(row['observed_replies'] for row in content_posts) / post_count, 2) if post_count else None,
        'zeroReplyRate': round(sum(row['observed_replies'] == 0 for row in content_posts) * 100 / post_count, 2) if post_count else None,
        'medianFirstReplyHours': round(median(first_reply_hours), 2) if first_reply_hours else None,
        'repliedPosts': len(first_reply_hours),
    }

    behavior_rows = BehaviorRetentionCohort.objects.filter(
        cohort_date__gte=start_date,
        cohort_date__lte=end_date,
        retention_day__in=(1, 7),
    )
    segment_labels = dict(BehaviorRetentionCohort.Segment.choices)
    behavior_retention = []
    for segment, label in segment_labels.items():
        item = {'segment': segment, 'name': label}
        for retention_day in (1, 7):
            totals = behavior_rows.filter(first_day_segment=segment, retention_day=retention_day).aggregate(
                cohort_size=Sum('cohort_size'),
                retained_users=Sum('retained_users'),
            )
            size = totals['cohort_size'] or 0
            item[f'd{retention_day}CohortSize'] = size
            item[f'd{retention_day}RetainedUsers'] = totals['retained_users'] or 0
            item[f'd{retention_day}'] = percentage(totals['retained_users'] or 0, size)
        behavior_retention.append(item)

    period_totals = {
        'sessions': sum(row.session_count for row in metrics),
        'postViews': sum(row.post_views for row in metrics),
        'posts': sum(row.posts_created for row in metrics),
        'replies': sum(row.replies_created for row in metrics),
        'likes': sum(row.likes_created for row in metrics),
        'unlikes': sum(row.unlikes_created for row in metrics),
        'newUsers': sum(row.new_users for row in metrics),
        'activatedNewUsers': sum(row.activated_new_users for row in metrics),
    }
    period_totals.update({
        'netLikes': period_totals['likes'] - period_totals['unlikes'],
        'currentLikes': Post.objects.aggregate(
            total=Count('likes', filter=Q(likes__is_staff=False, likes__is_superuser=False)),
        )['total'],
        **visitors,
    })
    activation_rate = percentage(period_totals['activatedNewUsers'], period_totals['newUsers'])
    anonymous_registration_rate = percentage(anonymous_registrations, visitors['anonymous_uv'])
    creator_retention = next((row for row in behavior_retention if row['segment'] == 'creator'), {'d1': 0, 'd7': 0})

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
            'allVisitors': visitors['all_visitors'],
            'loggedVisitors': visitors['logged_visitors'],
            'anonymousVisitors': visitors['anonymous_visitors'],
            'anonymousUv': visitors['anonymous_uv'],
            'anonymousRegistrations': anonymous_registrations,
            'anonymousRegistrationRate': anonymous_registration_rate,
            'activatedNewUsers': period_totals['activatedNewUsers'],
            'activationRate': activation_rate,
            'creatorD1Retention': creator_retention['d1'],
            'creatorD7Retention': creator_retention['d7'],
            'creatorD1CohortSize': creator_retention.get('d1CohortSize', 0),
            'creatorD7CohortSize': creator_retention.get('d7CohortSize', 0),
            'postingUsers': interaction_users['posting'],
            'replyingUsers': interaction_users['replying'],
            'likeActions': period_totals['likes'],
            'likingUsers': interaction_users['liking'],
            'netLikes': period_totals['netLikes'],
            'currentLikes': period_totals['currentLikes'],
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
            'netLikes': row.likes_created - row.unlikes_created,
            'loggedVisitors': row.page_view_users, 'allVisitors': row.page_view_users + row.anonymous_visitors,
            'anonymousVisitors': row.anonymous_visitors, 'anonymousPageViews': row.anonymous_page_views,
            'anonymousUv': row.anonymous_uv, 'anonymousRegistrations': row.anonymous_registrations,
            'anonymousRegistrationRate': percentage(row.anonymous_registrations, row.anonymous_uv),
            'activationRate': percentage(row.activated_new_users, row.new_users),
            'readOnlyUsers': row.read_only_users, 'interactionUsers': row.interaction_users, 'creatorUsers': row.creator_users,
        } for row in metrics],
        'cohorts': list(cohort_map.values()),
        'funnel': funnel,
        'segments': [{'name': name, 'value': value} for name, value in segment_counts.items()],
        'boards': [{'id': row['board_id'], 'name': row['board__name'], 'activeUsers': row['active_users'], 'viewUsers': row['view_users'], 'views': row['views'], 'posts': row['posts'], 'postingUsers': row['posting_users'], 'replies': row['replies'], 'replyingUsers': row['replying_users'], 'likes': row['likes'], 'likingUsers': row['liking_users'], 'interactionUsers': row['interaction_users'], 'interactionRate': percentage(row['interaction_users'], row['active_users'])} for row in board_rows],
        'posts': [{'id': row['post_id'], 'title': row['post__title'], 'board': row['board__name'], 'viewers': row['viewers'], 'views': row['views'], 'replies': row['replies'], 'likeActions': row['like_actions'], 'currentLikes': current_likes.get(row['post_id'], 0)} for row in post_rows],
        'period': {**period_totals, **interaction_users},
        'contentHealth': content_health,
        'behaviorRetention': behavior_retention,
        'meta': {'startDate': start_date.isoformat(), 'endDate': end_date.isoformat(), 'timezone': str(timezone.get_current_timezone()), 'completeDaysOnly': True, 'coreMetricScope': '普通登录用户（排除匿名、staff、superuser）'},
        'contracts': METRIC_CONTRACTS,
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
