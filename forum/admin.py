from django.contrib import admin

from .models import Board, Post, Reply


@admin.register(Board)
class BoardAdmin(admin.ModelAdmin):
    list_display = ('name', 'description', 'created_at')
    search_fields = ('name',)


@admin.register(Post)
class PostAdmin(admin.ModelAdmin):
    list_display = ('title', 'board', 'author', 'created_at', 'like_count')
    list_filter = ('board', 'created_at')
    search_fields = ('title', 'content', 'author__username')

    @admin.display(description='点赞数')
    def like_count(self, post):
        return post.likes.count()


@admin.register(Reply)
class ReplyAdmin(admin.ModelAdmin):
    list_display = ('post', 'author', 'created_at')
    search_fields = ('content', 'author__username')

# Register your models here.
