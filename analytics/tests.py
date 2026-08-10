import json
from datetime import timedelta

from django.contrib.auth import get_user_model
from django.db.models import Sum
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from forum.models import Board, Post

from .events import record_event
from .demo_data import DEMO_USERNAME_PREFIX, generate_demo_data
from .models import AnalyticsEvent, ProductMetricsDaily, RetentionCohort, UserActivityDaily
from .services import _day_range as services_day_range
from .services import generate_metrics


class AnalyticsTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(username='member', password='password')
        self.staff = get_user_model().objects.create_user(username='staff', password='password', is_staff=True)

    def test_browser_event_endpoint_records_event(self):
        self.client.get(reverse('forum:csrf'))
        response = self.client.post(
            reverse('analytics:track_event'),
            data=json.dumps({'eventName': 'page_view', 'anonymousId': 'anon-1', 'sessionId': 'session-1'}),
            content_type='application/json',
        )
        self.assertEqual(response.status_code, 201)
        self.assertTrue(AnalyticsEvent.objects.filter(event_name='page_view', anonymous_id='anon-1').exists())

    def test_generate_metrics_calculates_dau_and_retention(self):
        today = timezone.localdate()
        activity_day = today - timedelta(days=1)
        cohort_day = today - timedelta(days=2)
        cohort_time, _ = services_day_range(cohort_day)
        activity_time, _ = services_day_range(activity_day)
        get_user_model().objects.filter(pk=self.user.pk).update(date_joined=cohort_time)
        event = record_event('page_view', user=self.user, session_id='historical-session')
        AnalyticsEvent.objects.filter(pk=event.pk).update(occurred_at=activity_time)
        generate_metrics(cohort_day, activity_day)
        self.assertEqual(ProductMetricsDaily.objects.get(metric_date=activity_day).dau, 1)
        cohort = RetentionCohort.objects.get(cohort_date=cohort_day, retention_day=1)
        self.assertEqual(cohort.cohort_size, 1)
        self.assertEqual(cohort.retained_users, 1)
        self.assertEqual(float(cohort.retention_rate), 100.0)

    def test_dashboard_requires_staff(self):
        yesterday = timezone.localdate() - timedelta(days=1)
        ProductMetricsDaily.objects.create(metric_date=yesterday, dau=2, wau=4, mau=5)
        RetentionCohort.objects.create(cohort_date=yesterday - timedelta(days=2), retention_day=1, cohort_size=4, retained_users=1, retention_rate=25)
        RetentionCohort.objects.create(cohort_date=yesterday - timedelta(days=3), retention_day=1, cohort_size=1, retained_users=1, retention_rate=100)
        self.client.force_login(self.user)
        response = self.client.get(reverse('analytics:dashboard'))
        self.assertEqual(response.status_code, 302)
        self.client.force_login(self.staff)
        response = self.client.get(reverse('analytics:dashboard'))
        self.assertContains(response, 'react/assets/app.js')
        response = self.client.get(reverse('analytics:dashboard_api'))
        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertIn('summary', payload)
        self.assertEqual(payload['summary']['d1Retention'], 40.0)
        self.assertTrue({'trend', 'funnel', 'segments', 'boards', 'posts', 'cohorts'} <= payload.keys())
        self.assertIn('no-cache', response.headers['Cache-Control'])

    def test_dashboard_refresh_only_generates_completed_days(self):
        self.client.force_login(self.staff)
        response = self.client.post(
            reverse('analytics:refresh_metrics'),
            data=json.dumps({'days': 7}),
            content_type='application/json',
        )
        self.assertEqual(response.status_code, 200)
        self.assertFalse(ProductMetricsDaily.objects.filter(metric_date=timezone.localdate()).exists())
        self.assertTrue(ProductMetricsDaily.objects.filter(metric_date=timezone.localdate() - timedelta(days=1)).exists())

    def test_dashboard_contracts_keep_visitors_activity_and_likes_distinct(self):
        day = timezone.localdate() - timedelta(days=1)
        occurred_at, _ = services_day_range(day)
        get_user_model().objects.filter(pk=self.user.pk).update(date_joined=occurred_at)
        inactive = get_user_model().objects.create_user(username='inactive-new', password='password')
        get_user_model().objects.filter(pk=inactive.pk).update(date_joined=occurred_at)
        board = Board.objects.create(name='指标测试')
        post = Post.objects.create(board=board, author=self.user, title='口径测试', content='测试')
        post.likes.add(self.user)

        created_events = [
            record_event('page_view', anonymous_id='linked-browser'),
            record_event('page_view', anonymous_id='pure-anonymous'),
            record_event('page_view', user=self.user, anonymous_id='linked-browser'),
            record_event('post_view', user=self.user, post=post, board=board),
            record_event('post_like', user=self.user, post=post, board=board),
            record_event('post_like', user=self.user, post=post, board=board),
            record_event('post_unlike', user=self.user, post=post, board=board),
        ]
        AnalyticsEvent.objects.filter(pk__in=[event.pk for event in created_events]).update(occurred_at=occurred_at)
        generate_metrics(day, day)

        metric = ProductMetricsDaily.objects.get(metric_date=day)
        self.assertEqual(UserActivityDaily.objects.filter(activity_date=day).count(), 2)
        self.assertEqual(metric.dau, 1)
        self.assertEqual(metric.anonymous_visitors, 1)

        self.client.force_login(self.staff)
        payload = self.client.get(reverse('analytics:dashboard_api'), {'days': 7}).json()
        self.assertEqual(payload['summary']['allVisitors'], 2)
        self.assertEqual(payload['summary']['loggedVisitors'], 1)
        self.assertEqual(payload['summary']['anonymousVisitors'], 1)
        self.assertEqual(payload['summary']['likeActions'], 2)
        self.assertEqual(payload['summary']['likingUsers'], 1)
        self.assertEqual(payload['summary']['netLikes'], 1)
        self.assertEqual(payload['summary']['currentLikes'], 1)
        self.assertTrue(payload['meta']['completeDaysOnly'])
        self.assertGreaterEqual(len(payload['contracts']), 10)


class DemoDataTests(TestCase):
    def test_demo_generator_creates_business_events_and_metrics(self):
        real_user = get_user_model().objects.create_user(username='real-member', password='password')
        result = generate_demo_data(
            days=31,
            user_count=20,
            seed=42,
            end_date=timezone.localdate() - timedelta(days=1),
        )

        self.assertEqual(get_user_model().objects.filter(username__startswith=DEMO_USERNAME_PREFIX).count(), 20)
        self.assertGreater(result['events'], 100)
        self.assertGreater(result['anonymous_events'], 0)
        self.assertTrue(AnalyticsEvent.objects.filter(event_name='post_view', properties__demo=True).exists())
        self.assertTrue(AnalyticsEvent.objects.filter(event_name='post_create', properties__demo=True).exists())
        self.assertTrue(UserActivityDaily.objects.exists())
        self.assertEqual(ProductMetricsDaily.objects.filter(metric_date__range=(result['start_date'], result['end_date'])).count(), 31)
        totals = ProductMetricsDaily.objects.filter(metric_date__range=(result['start_date'], result['end_date'])).aggregate(
            board_views=Sum('board_views'),
            post_view_users=Sum('post_view_users'),
            anonymous_visitors=Sum('anonymous_visitors'),
        )
        self.assertGreater(totals['board_views'], 0)
        self.assertGreater(totals['post_view_users'], 0)
        self.assertGreater(totals['anonymous_visitors'], 0)
        self.assertTrue(RetentionCohort.objects.filter(retention_day=1).exists())

        with self.assertRaisesMessage(ValueError, '演示数据已经存在'):
            generate_demo_data(days=31, user_count=20, seed=42, end_date=result['end_date'])

        regenerated = generate_demo_data(days=31, user_count=20, seed=42, end_date=result['end_date'], reset=True)
        self.assertEqual(regenerated['users'], 20)
        self.assertEqual(get_user_model().objects.filter(username__startswith=DEMO_USERNAME_PREFIX).count(), 20)
        self.assertTrue(get_user_model().objects.filter(pk=real_user.pk).exists())
