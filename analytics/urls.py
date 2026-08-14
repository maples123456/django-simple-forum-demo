from django.urls import path

from . import views

app_name = 'analytics'

urlpatterns = [
    path('', views.dashboard, name='dashboard'),
    path('api/events/', views.track_event, name='track_event'),
    path('api/dashboard/', views.dashboard_api, name='dashboard_api'),
    path('api/refresh/', views.refresh_metrics, name='refresh_metrics'),
]
