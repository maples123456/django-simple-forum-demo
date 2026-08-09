from django.conf import settings
from django.db import models
from django.urls import reverse


class Board(models.Model):
    name = models.CharField('名称', max_length=80, unique=True)
    description = models.TextField('简介', blank=True)
    created_at = models.DateTimeField('创建时间', auto_now_add=True)

    class Meta:
        ordering = ['name']
        verbose_name = '板块'
        verbose_name_plural = '板块'

    def __str__(self):
        return self.name


class Post(models.Model):
    board = models.ForeignKey(Board, on_delete=models.CASCADE, related_name='posts', verbose_name='板块')
    title = models.CharField('标题', max_length=160)
    content = models.TextField('内容')
    author = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='posts', verbose_name='作者')
    created_at = models.DateTimeField('发布时间', auto_now_add=True)
    updated_at = models.DateTimeField('更新时间', auto_now=True)
    likes = models.ManyToManyField(settings.AUTH_USER_MODEL, related_name='liked_posts', blank=True, verbose_name='点赞用户')

    class Meta:
        ordering = ['-created_at']
        verbose_name = '帖子'
        verbose_name_plural = '帖子'

    def __str__(self):
        return self.title

    def get_absolute_url(self):
        return reverse('forum:post_detail', args=[self.pk])


class Reply(models.Model):
    post = models.ForeignKey(Post, on_delete=models.CASCADE, related_name='replies', verbose_name='帖子')
    content = models.TextField('内容')
    author = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='replies', verbose_name='作者')
    created_at = models.DateTimeField('回复时间', auto_now_add=True)

    class Meta:
        ordering = ['created_at']
        verbose_name = '回复'
        verbose_name_plural = '回复'

    def __str__(self):
        return f'{self.author} 回复 {self.post}'

# Create your models here.
