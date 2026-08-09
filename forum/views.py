from django.contrib.auth.decorators import login_required
from django.db.models import Count, Prefetch
from django.http import HttpResponseForbidden
from django.shortcuts import get_object_or_404, redirect, render

from .forms import PostForm, ReplyForm
from .models import Board, Post, Reply


def board_list(request):
    boards = Board.objects.annotate(post_count=Count('posts'))
    return render(request, 'forum/board_list.html', {'boards': boards})


def post_list(request, board_id):
    board = get_object_or_404(Board, pk=board_id)
    posts = board.posts.select_related('author').annotate(reply_count=Count('replies'), like_count=Count('likes'))
    return render(request, 'forum/post_list.html', {'board': board, 'posts': posts})


def post_detail(request, post_id):
    post = get_object_or_404(
        Post.objects.select_related('author', 'board').prefetch_related(
            Prefetch('replies', queryset=Reply.objects.select_related('author')),
            'likes',
        ),
        pk=post_id,
    )
    if request.method == 'POST':
        if not request.user.is_authenticated:
            return redirect(f'/accounts/login/?next={request.path}')
        form = ReplyForm(request.POST)
        if form.is_valid():
            reply = form.save(commit=False)
            reply.post = post
            reply.author = request.user
            reply.save()
            return redirect(post)
    else:
        form = ReplyForm()
    return render(request, 'forum/post_detail.html', {'post': post, 'form': form})


@login_required
def post_create(request, board_id):
    board = get_object_or_404(Board, pk=board_id)
    form = PostForm(request.POST or None)
    if request.method == 'POST' and form.is_valid():
        post = form.save(commit=False)
        post.board = board
        post.author = request.user
        post.save()
        return redirect(post)
    return render(request, 'forum/post_form.html', {'board': board, 'form': form})


@login_required
def toggle_like(request, post_id):
    if request.method != 'POST':
        return HttpResponseForbidden('仅支持 POST 请求。')
    post = get_object_or_404(Post, pk=post_id)
    if request.user in post.likes.all():
        post.likes.remove(request.user)
    else:
        post.likes.add(request.user)
    return redirect(post)

# Create your views here.
