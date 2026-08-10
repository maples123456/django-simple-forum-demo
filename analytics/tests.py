import json
from datetime import timedelta

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

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
        self.client.force_login(self.user)
        response = self.client.get(reverse('analytics:dashboard'))
        self.assertEqual(response.status_code, 302)
        self.client.force_login(self.staff)
        response = self.client.get(reverse('analytics:dashboard'))
        self.assertContains(response, 'react/assets/app.js')
        response = self.client.get(reverse('analytics:dashboard_api'))
        self.assertEqual(response.status_code, 200)
        self.assertIn('summary', response.json())


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
        self.assertTrue(RetentionCohort.objects.filter(retention_day=1).exists())

        with self.assertRaisesMessage(ValueError, '演示数据已经存在'):
            generate_demo_data(days=31, user_count=20, seed=42, end_date=result['end_date'])

        regenerated = generate_demo_data(days=31, user_count=20, seed=42, end_date=result['end_date'], reset=True)
        self.assertEqual(regenerated['users'], 20)
        self.assertEqual(get_user_model().objects.filter(username__startswith=DEMO_USERNAME_PREFIX).count(), 20)
        self.assertTrue(get_user_model().objects.filter(pk=real_user.pk).exists())
