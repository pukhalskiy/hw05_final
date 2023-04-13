from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.shortcuts import get_object_or_404, redirect, render

from .forms import CommentForm, PostForm
from .models import Comment, Follow, Group, Post, User

POSTS_COUNT = 10


def index(request):
    posts = Post.objects.select_related('author', 'group').all()
    paginator = Paginator(posts, POSTS_COUNT)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    context = {
        'page_obj': page_obj,
    }
    return render(request, 'posts/index.html', context)


def group_posts(request, slug):
    group = get_object_or_404(Group, slug=slug)
    posts = group.posts.select_related('group').all()
    paginator = Paginator(posts, POSTS_COUNT)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    context = {
        'page_obj': page_obj,
        'group': group
    }
    return render(request, 'posts/group_list.html', context)


def profile(request, username):
    author_username = get_object_or_404(User, username=username)
    posts = author_username.posts.select_related('author', 'group').all()
    posts_count = posts.count()
    paginator = Paginator(posts, POSTS_COUNT)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    if request.user.is_authenticated:
        following = Follow.objects.filter(user=request.user,
                                          author=author_username
                                          ).exists()
    else:
        following = False
    context = {
        'page_obj': page_obj,
        'count': posts_count,
        'author': author_username,
        'following': following
    }
    return render(request, 'posts/profile.html', context)


def post_detail(request, post_id):
    post = get_object_or_404(Post, id=post_id)
    form = CommentForm(request.POST or None)
    comments = Comment.objects.filter(post=post)
    author = post.author
    posts_count = Post.objects.filter(author=author).count()
    context = {
        'post': post,
        'posts': posts_count,
        'form': form,
        'comments': comments
    }
    return render(request, 'posts/post_detail.html', context)


@login_required
def post_create(request):
    form = PostForm(request.POST or None, files=request.FILES or None)
    if request.method == 'POST':
        if form.is_valid():
            post = form.save(commit=False)
            post.author = request.user
            post.save()
            return redirect('posts:profile', username=request.user)
        return render(request, 'posts/create_post.html', {'form': form})
    context = {
        'form': form,
        'title': 'Новый пост'
    }
    return render(request, 'posts/create_post.html', context)


def post_edit(request, post_id):
    post = get_object_or_404(Post, id=post_id)
    form = PostForm(request.POST or None, instance=post,
                    files=request.FILES or None)
    if post.author != request.user:
        return redirect('posts:post_detail', post_id)
    if request.method == 'POST':
        form.save()
        return redirect('posts:post_detail', post_id)
    context = {
        'is_edit': True,
        'form': form,
        'title': 'Редактировать пост'
    }
    return render(request, 'posts/create_post.html', context)


@login_required
def add_comment(request, post_id):
    post = get_object_or_404(Post, id=post_id)
    form = CommentForm(request.POST or None)
    if form.is_valid():
        comment = form.save(commit=False)
        comment.author = request.user
        comment.post = post
        comment.save()
    return redirect('posts:post_detail', post_id=post_id)


@login_required
def follow_index(request):
    authors = request.user.follower.values('author')
    posts = Post.objects.filter(author__in=authors)
    paginator = Paginator(posts, POSTS_COUNT)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    context = {
        'page_obj': page_obj
    }
    return render(request, 'posts/follows.html', context)


@login_required
def profile_follow(request, username):
    author = get_object_or_404(User, username=username)
    if author == request.user:
        return redirect('posts:profile', username)
    following, created = Follow.objects.get_or_create(
        user=request.user,
        author=author
    )
    if not created and following:
        pass
    return redirect('posts:profile', username)


@login_required
def profile_unfollow(request, username):
    author = get_object_or_404(User, username=username)
    following = Follow.objects.filter(user=request.user,
                                      author=author)
    if following.exists():
        following.delete()
    return redirect('posts:profile', username)
