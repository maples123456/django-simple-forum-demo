import json
from datetime import timedelta

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from .events import record_event
from .models import AnalyticsEvent, ProductMetricsDaily, RetentionCohort
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
        yesterday = today - timedelta(days=1)
        get_user_model().objects.filter(pk=self.user.pk).update(date_joined=timezone.now() - timedelta(days=1))
        record_event('page_view', user=self.user, session_id='today-session')
        generate_metrics(yesterday, today)
        self.assertEqual(ProductMetricsDaily.objects.get(metric_date=today).dau, 1)
        cohort = RetentionCohort.objects.get(cohort_date=yesterday, retention_day=1)
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
