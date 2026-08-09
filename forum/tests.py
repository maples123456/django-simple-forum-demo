from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from .models import Board, Post


class ForumViewsTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(username='alice', password='test-password')
        self.board = Board.objects.create(name='技术交流', description='讨论技术')
        self.post = Post.objects.create(board=self.board, title='第一篇帖子', content='内容', author=self.user)

    def test_board_list_is_available(self):
        response = self.client.get(reverse('forum:boards_api'))
        self.assertEqual(response.json()['boards'][0]['name'], '技术交流')

    def test_react_app_shell_is_available(self):
        response = self.client.get(reverse('forum:app'))
        self.assertContains(response, 'react/assets/app.js')

    def test_logged_in_user_can_reply_and_like(self):
        self.client.login(username='alice', password='test-password')
        self.client.get(reverse('forum:csrf'))
        self.client.post(reverse('forum:reply_api', args=[self.post.id]), data='{"content":"很好的分享"}', content_type='application/json')
        self.client.post(reverse('forum:toggle_like_api', args=[self.post.id]))
        self.post.refresh_from_db()
        self.assertEqual(self.post.replies.count(), 1)
        self.assertTrue(self.post.likes.filter(pk=self.user.pk).exists())

# Create your tests here.
