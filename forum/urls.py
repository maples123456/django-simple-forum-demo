from django.urls import path

from . import views

app_name = 'forum'

urlpatterns = [
    path('', views.board_list, name='board_list'),
    path('boards/<int:board_id>/', views.post_list, name='post_list'),
    path('boards/<int:board_id>/new/', views.post_create, name='post_create'),
    path('posts/<int:post_id>/', views.post_detail, name='post_detail'),
    path('posts/<int:post_id>/like/', views.toggle_like, name='toggle_like'),
]
