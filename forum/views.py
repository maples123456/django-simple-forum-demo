import json

from django.contrib.auth.decorators import login_required
from django.db.models import Count, Prefetch
from django.http import HttpResponseBadRequest, JsonResponse
from django.middleware.csrf import get_token
from django.views.decorators.http import require_GET, require_POST
from django.shortcuts import get_object_or_404, render
from .models import Board, Post, Reply


def app(request):
    return render(request, 'forum/react_index.html')


def _payload(request):
    try:
        return json.loads(request.body)
    except (json.JSONDecodeError, UnicodeDecodeError):
        return None


def _post_data(post, user=None, include_content=True):
    data = {
        'id': post.id,
        'title': post.title,
        'author': post.author.username,
        'createdAt': post.created_at.isoformat(),
        'likeCount': post.likes.count(),
        'liked': bool(user and user.is_authenticated and post.likes.filter(pk=user.pk).exists()),
    }
    if include_content:
        data['content'] = post.content
    return data


@require_GET
def csrf(request):
    return JsonResponse({'csrfToken': get_token(request)})


@require_GET
def boards_api(request):
    boards = Board.objects.annotate(post_count=Count('posts'))
    return JsonResponse({'boards': [{'id': board.id, 'name': board.name, 'description': board.description, 'postCount': board.post_count} for board in boards]})


@require_GET
def posts_api(request, board_id):
    board = get_object_or_404(Board, pk=board_id)
    posts = board.posts.select_related('author').annotate(reply_count=Count('replies'))
    return JsonResponse({'board': {'id': board.id, 'name': board.name, 'description': board.description}, 'posts': [{**_post_data(post, request.user, include_content=False), 'replyCount': post.reply_count} for post in posts]})


@require_POST
@login_required
def create_post_api(request, board_id):
    data = _payload(request)
    if not data or not data.get('title', '').strip() or not data.get('content', '').strip():
        return HttpResponseBadRequest('标题和内容不能为空。')
    board = get_object_or_404(Board, pk=board_id)
    post = Post.objects.create(board=board, author=request.user, title=data['title'].strip(), content=data['content'].strip())
    return JsonResponse({'post': _post_data(post, request.user)}, status=201)


@require_GET
def post_api(request, post_id):
    post = get_object_or_404(Post.objects.select_related('author', 'board').prefetch_related(Prefetch('replies', queryset=Reply.objects.select_related('author'))), pk=post_id)
    return JsonResponse({'post': {**_post_data(post, request.user), 'board': {'id': post.board.id, 'name': post.board.name}, 'replies': [{'id': reply.id, 'content': reply.content, 'author': reply.author.username, 'createdAt': reply.created_at.isoformat()} for reply in post.replies.all()]}})


@require_POST
@login_required
def reply_api(request, post_id):
    data = _payload(request)
    if not data or not data.get('content', '').strip():
        return HttpResponseBadRequest('回复内容不能为空。')
    post = get_object_or_404(Post, pk=post_id)
    reply = Reply.objects.create(post=post, author=request.user, content=data['content'].strip())
    return JsonResponse({'reply': {'id': reply.id, 'content': reply.content, 'author': reply.author.username, 'createdAt': reply.created_at.isoformat()}}, status=201)


@require_POST
@login_required
def toggle_like_api(request, post_id):
    post = get_object_or_404(Post, pk=post_id)
    if post.likes.filter(pk=request.user.pk).exists():
        post.likes.remove(request.user)
    else:
        post.likes.add(request.user)
    return JsonResponse({'likeCount': post.likes.count(), 'liked': post.likes.filter(pk=request.user.pk).exists()})
