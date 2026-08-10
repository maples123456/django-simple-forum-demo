import random
from dataclasses import dataclass
from datetime import datetime, time, timedelta

from django.contrib.auth import get_user_model
from django.contrib.auth.hashers import make_password
from django.db import transaction
from django.utils import timezone

from forum.models import Board, Post, Reply

from .models import AnalyticsEvent, ProductMetricsDaily
from .services import generate_metrics


DEMO_USERNAME_PREFIX = 'demo_'
DEMO_PASSWORD = 'DemoForum2026!'
BOARD_DEFINITIONS = (
    ('技术交流', '分享编程、数据和工程实践。'),
    ('产品反馈', '讨论论坛功能、体验和改进建议。'),
    ('社区生活', '轻松交流工作、学习与日常话题。'),
)
SEGMENTS = {
    'reader': {'weight': 45, 'base': 0.18, 'activate': 0.72, 'd1': 0.28, 'd7': 0.13, 'd30': 0.06},
    'liker': {'weight': 25, 'base': 0.25, 'activate': 0.82, 'd1': 0.38, 'd7': 0.22, 'd30': 0.12},
    'discusser': {'weight': 20, 'base': 0.33, 'activate': 0.90, 'd1': 0.52, 'd7': 0.34, 'd30': 0.20},
    'creator': {'weight': 10, 'base': 0.42, 'activate': 0.95, 'd1': 0.62, 'd7': 0.45, 'd30': 0.30},
}


@dataclass
class DemoProfile:
    user: object
    segment: str
    joined_on: object


def _at(day, hour, minute=0):
    value = datetime.combine(day, time(hour=hour, minute=minute))
    return timezone.make_aware(value, timezone.get_current_timezone())


def _choose_segment(rng):
    names = list(SEGMENTS)
    return rng.choices(names, weights=[SEGMENTS[name]['weight'] for name in names], k=1)[0]


def _is_active(rng, segment, age, day):
    rules = SEGMENTS[segment]
    if age == 0:
        probability = rules['activate']
    elif age in (1, 7, 30):
        probability = rules[f'd{age}']
    else:
        recency = max(0.58, 1 - age / 150)
        weekend = 1.12 if day.weekday() >= 5 else 1
        probability = min(rules['base'] * recency * weekend, 0.85)
    return rng.random() < probability


def _demo_event(event_name, occurred_at, *, user=None, session_id='', anonymous_id='', board=None, post=None, segment=None, source='django', extra=None):
    properties = {'demo': True}
    if segment:
        properties['segment'] = segment
    if extra:
        properties.update(extra)
    return AnalyticsEvent(
        event_name=event_name,
        occurred_at=occurred_at,
        user=user,
        session_id=session_id,
        anonymous_id=anonymous_id,
        board=board,
        post=post,
        properties=properties,
        source=source,
    )


def _create_post(user, board, occurred_at, index):
    titles = (
        '分享一个最近解决的问题', '这个功能可以怎样改进？', '大家平时如何安排学习时间？',
        '一个简单的数据分析思路', '新手求助：这里应该怎么理解？', '本周社区讨论汇总',
    )
    post = Post.objects.create(
        board=board,
        author=user,
        title=f'{titles[index % len(titles)]} #{index + 1}',
        content='这是用于论坛指标学习的演示内容。欢迎浏览、回复并参与讨论。',
    )
    Post.objects.filter(pk=post.pk).update(created_at=occurred_at, updated_at=occurred_at)
    post.created_at = occurred_at
    post.updated_at = occurred_at
    return post


def _create_reply(user, post, occurred_at, index):
    contents = ('这个观点很有启发，谢谢分享。', '我也遇到过类似问题，可以再补充一些细节吗？', '赞同，期待后续更新。', '这里提供了一个很好的讨论角度。')
    reply = Reply.objects.create(post=post, author=user, content=contents[index % len(contents)])
    Reply.objects.filter(pk=reply.pk).update(created_at=occurred_at)
    reply.created_at = occurred_at
    return reply


@transaction.atomic
def generate_demo_data(*, days=60, user_count=180, seed=20260810, end_date=None, reset=False):
    if days < 31:
        raise ValueError('days 至少为 31，才能生成可用于 D30 留存的注册 Cohort。')
    if user_count < 20:
        raise ValueError('user_count 至少为 20，才能形成有意义的用户分层。')

    User = get_user_model()
    existing = User.objects.filter(username__startswith=DEMO_USERNAME_PREFIX)
    old_dates = list(existing.values_list('date_joined', flat=True))
    if existing.exists() and not reset:
        raise ValueError('演示数据已经存在；如需重新生成，请使用 reset=True。')
    if reset:
        AnalyticsEvent.objects.filter(properties__demo=True).delete()
        existing.delete()

    rng = random.Random(seed)
    end_date = end_date or timezone.localdate() - timedelta(days=1)
    start_date = end_date - timedelta(days=days - 1)
    password = make_password(DEMO_PASSWORD)
    profiles_data = []
    users = []
    for index in range(user_count):
        segment = _choose_segment(rng)
        offset = 0 if index < len(BOARD_DEFINITIONS) else min(int((rng.random() ** 0.82) * days), days - 1)
        joined_on = start_date + timedelta(days=offset)
        joined_at = _at(joined_on, rng.randint(7, 22), rng.randint(0, 59))
        username = f'{DEMO_USERNAME_PREFIX}{segment}_{index + 1:03d}'
        users.append(User(username=username, email=f'{username}@example.test', password=password, date_joined=joined_at, is_active=True))
        profiles_data.append((segment, joined_on))
    users = User.objects.bulk_create(users, batch_size=500)
    profiles = [DemoProfile(user=user, segment=data[0], joined_on=data[1]) for user, data in zip(users, profiles_data)]
    profiles.sort(key=lambda item: (item.joined_on, item.user.id))

    boards = []
    for name, description in BOARD_DEFINITIONS:
        board, _ = Board.objects.get_or_create(name=name, defaults={'description': description})
        boards.append(board)

    events = []
    for profile in profiles:
        events.append(_demo_event('sign_up', profile.user.date_joined, user=profile.user, segment=profile.segment))

    posts = []
    for index, board in enumerate(boards):
        author = profiles[index % len(profiles)].user
        occurred_at = _at(start_date, 10 + index)
        post = _create_post(author, board, occurred_at, index)
        posts.append(post)
        events.append(_demo_event('post_create', occurred_at, user=author, session_id=f'demo-initial-{index}', board=board, post=post, segment=profiles[index].segment))

    liked_pairs = set()
    post_index = len(posts)
    reply_index = 0
    day = start_date
    while day <= end_date:
        available_profiles = [profile for profile in profiles if profile.joined_on <= day]
        for profile in available_profiles:
            age = (day - profile.joined_on).days
            if not _is_active(rng, profile.segment, age, day):
                continue
            session_total = 2 if rng.random() < {'reader': 0.08, 'liker': 0.12, 'discusser': 0.18, 'creator': 0.24}[profile.segment] else 1
            viewed_posts = []
            last_session_id = ''
            for session_number in range(session_total):
                session_id = f'demo-{day:%Y%m%d}-{profile.user.id}-{session_number + 1}'
                last_session_id = session_id
                hour = min(8 + rng.randint(0, 13) + session_number, 23)
                base_time = _at(day, hour, rng.randint(0, 50))
                events.append(_demo_event('login', base_time, user=profile.user, session_id=session_id, segment=profile.segment))
                events.append(_demo_event('page_view', base_time + timedelta(minutes=1), user=profile.user, session_id=session_id, segment=profile.segment, source='react', extra={'device': rng.choice(('desktop', 'mobile'))}))
                if rng.random() < 0.90:
                    board = rng.choice(boards)
                    events.append(_demo_event('board_view', base_time + timedelta(minutes=2), user=profile.user, session_id=session_id, board=board, segment=profile.segment, source='react'))
                view_total = rng.randint(1, {'reader': 5, 'liker': 5, 'discusser': 4, 'creator': 4}[profile.segment])
                for view_number in range(view_total):
                    post = rng.choice(posts)
                    viewed_posts.append(post)
                    events.append(_demo_event('post_view', base_time + timedelta(minutes=3 + view_number), user=profile.user, session_id=session_id, board=post.board, post=post, segment=profile.segment, source='react'))

            action_time = _at(day, min(21 + session_total, 23), rng.randint(0, 45))
            probabilities = {
                'reader': (0.01, 0.01, 0.03),
                'liker': (0.02, 0.05, 0.55),
                'discusser': (0.06, 0.48, 0.32),
                'creator': (0.32, 0.38, 0.28),
            }
            post_probability, reply_probability, like_probability = probabilities[profile.segment]
            if rng.random() < post_probability:
                board = rng.choice(boards)
                post = _create_post(profile.user, board, action_time, post_index)
                post_index += 1
                posts.append(post)
                events.append(_demo_event('post_create', action_time, user=profile.user, session_id=last_session_id, board=board, post=post, segment=profile.segment))
            if viewed_posts and rng.random() < reply_probability:
                post = rng.choice(viewed_posts)
                _create_reply(profile.user, post, action_time + timedelta(minutes=1), reply_index)
                reply_index += 1
                events.append(_demo_event('reply_create', action_time + timedelta(minutes=1), user=profile.user, session_id=last_session_id, board=post.board, post=post, segment=profile.segment))
            if viewed_posts and rng.random() < like_probability:
                post = rng.choice(viewed_posts)
                pair = (profile.user.id, post.id)
                if pair in liked_pairs and rng.random() < 0.22:
                    liked_pairs.remove(pair)
                    post.likes.remove(profile.user)
                    event_name = 'post_unlike'
                elif pair not in liked_pairs:
                    liked_pairs.add(pair)
                    post.likes.add(profile.user)
                    event_name = 'post_like'
                else:
                    event_name = None
                if event_name:
                    events.append(_demo_event(event_name, action_time + timedelta(minutes=2), user=profile.user, session_id=last_session_id, board=post.board, post=post, segment=profile.segment))

        anonymous_total = rng.randint(8, 18)
        for anonymous_index in range(anonymous_total):
            anonymous_id = f'demo-anon-{day:%Y%m%d}-{anonymous_index:03d}'
            session_id = f'{anonymous_id}-session'
            occurred_at = _at(day, rng.randint(8, 22), rng.randint(0, 55))
            events.append(_demo_event('page_view', occurred_at, anonymous_id=anonymous_id, session_id=session_id, source='react', extra={'visitor_type': 'anonymous'}))
            if rng.random() < 0.72:
                board = rng.choice(boards)
                events.append(_demo_event('board_view', occurred_at + timedelta(minutes=1), anonymous_id=anonymous_id, session_id=session_id, board=board, source='react', extra={'visitor_type': 'anonymous'}))
            if posts and rng.random() < 0.55:
                post = rng.choice(posts)
                events.append(_demo_event('post_view', occurred_at + timedelta(minutes=2), anonymous_id=anonymous_id, session_id=session_id, board=post.board, post=post, source='react', extra={'visitor_type': 'anonymous'}))
        day += timedelta(days=1)

    AnalyticsEvent.objects.bulk_create(events, batch_size=1000)

    affected_start = start_date
    affected_end = end_date
    if old_dates:
        old_local_dates = [timezone.localtime(value).date() for value in old_dates]
        affected_start = min(affected_start, min(old_local_dates))
        affected_end = max(affected_end, max(old_local_dates))
    generate_metrics(affected_start, affected_end)

    latest = ProductMetricsDaily.objects.get(metric_date=end_date)
    return {
        'start_date': start_date,
        'end_date': end_date,
        'users': len(users),
        'boards': len(boards),
        'posts': len(posts),
        'replies': reply_index,
        'events': len(events),
        'anonymous_events': sum(1 for event in events if event.user_id is None),
        'dau': latest.dau,
        'wau': latest.wau,
        'mau': latest.mau,
        'new_users': latest.new_users,
    }
