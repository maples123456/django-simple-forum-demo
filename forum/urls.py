from django.urls import path

from . import views

app_name = 'forum'

urlpatterns = [
    path('', views.app, name='app'),
    path('api/csrf/', views.csrf, name='csrf'),
    path('api/boards/', views.boards_api, name='boards_api'),
    path('api/boards/<int:board_id>/posts/', views.posts_api, name='posts_api'),
    path('api/boards/<int:board_id>/posts/create/', views.create_post_api, name='create_post_api'),
    path('api/posts/<int:post_id>/', views.post_api, name='post_api'),
    path('api/posts/<int:post_id>/replies/', views.reply_api, name='reply_api'),
    path('api/posts/<int:post_id>/like/', views.toggle_like_api, name='toggle_like_api'),
]
