import json
import random

from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.models import User
from django.db.models import Q
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods

from .models import Comment, Follow, Like, Post, Profile

COLORS = ['#6c5ce7', '#00b894', '#0984e3', '#e17055', '#d63031', '#fdcb6e', '#e84393', '#00cec9']

# NOTE ON CSRF: these endpoints are called via fetch() as a small JSON API,
# the same way the original Express version worked (session cookie only,
# no CSRF token dance). To keep the frontend 100% unchanged we exempt these
# views from Django's CSRF check. In a production deployment you'd instead
# read the csrftoken cookie in api.js and send it as an X-CSRFToken header.


def _body(request):
    try:
        return json.loads(request.body or b'{}')
    except (json.JSONDecodeError, UnicodeDecodeError):
        return {}


def public_user(user):
    if not user:
        return None
    profile = user.profile
    return {
        'id': user.id,
        'username': user.username,
        'display_name': profile.display_name or user.username,
        'bio': profile.bio,
        'avatar_color': profile.avatar_color,
        'created_at': user.date_joined.isoformat(),
    }


def post_dict(post, viewer):
    liked_by_me = False
    if viewer is not None and viewer.is_authenticated:
        liked_by_me = post.likes.filter(user=viewer).exists()
    profile = post.user.profile
    return {
        'id': post.id,
        'user_id': post.user_id,
        'content': post.content,
        'created_at': post.created_at.isoformat(),
        'username': post.user.username,
        'display_name': profile.display_name or post.user.username,
        'avatar_color': profile.avatar_color,
        'likeCount': post.likes.count(),
        'commentCount': post.comments.count(),
        'likedByMe': liked_by_me,
    }


def comment_dict(comment):
    profile = comment.user.profile
    return {
        'id': comment.id,
        'post_id': comment.post_id,
        'user_id': comment.user_id,
        'content': comment.content,
        'created_at': comment.created_at.isoformat(),
        'username': comment.user.username,
        'display_name': profile.display_name or comment.user.username,
        'avatar_color': profile.avatar_color,
    }


# ---------------- auth ----------------

@csrf_exempt
@require_http_methods(['POST'])
def register(request):
    data = _body(request)
    username = (data.get('username') or '').strip()
    password = data.get('password') or ''
    display_name = (data.get('display_name') or '').strip()

    if len(username) < 3 or len(password) < 4:
        return JsonResponse({'error': 'Username (3+ chars) and password (4+ chars) required'}, status=400)
    if User.objects.filter(username=username).exists():
        return JsonResponse({'error': 'Username already taken'}, status=400)

    user = User.objects.create_user(username=username, password=password)
    # Profile is auto-created by the post_save signal in core/apps.py; fill it in.
    profile, _ = Profile.objects.get_or_create(user=user)
    profile.display_name = display_name or username
    profile.avatar_color = random.choice(COLORS)
    profile.save()

    login(request, user)
    return JsonResponse({'user': public_user(user)})


@csrf_exempt
@require_http_methods(['POST'])
def login_view(request):
    data = _body(request)
    username = data.get('username') or ''
    password = data.get('password') or ''
    user = authenticate(request, username=username, password=password)
    if not user:
        return JsonResponse({'error': 'Invalid username or password'}, status=401)
    login(request, user)
    return JsonResponse({'user': public_user(user)})


@csrf_exempt
@require_http_methods(['POST'])
def logout_view(request):
    logout(request)
    return JsonResponse({'ok': True})


def me(request):
    if not request.user.is_authenticated:
        return JsonResponse({'user': None})
    return JsonResponse({'user': public_user(request.user)})


# ---------------- users / profiles ----------------

def get_user(request, user_id):
    user = User.objects.filter(id=user_id).first()
    if not user:
        return JsonResponse({'error': 'User not found'}, status=404)

    follower_count = Follow.objects.filter(following=user).count()
    following_count = Follow.objects.filter(follower=user).count()
    post_count = Post.objects.filter(user=user).count()

    is_following = False
    is_self = False
    if request.user.is_authenticated:
        is_following = Follow.objects.filter(follower=request.user, following=user).exists()
        is_self = request.user.id == user.id

    return JsonResponse({
        'user': public_user(user),
        'followerCount': follower_count,
        'followingCount': following_count,
        'postCount': post_count,
        'isFollowing': is_following,
        'isSelf': is_self,
    })


@csrf_exempt
@require_http_methods(['PUT'])
def update_me(request):
    if not request.user.is_authenticated:
        return JsonResponse({'error': 'Not logged in'}, status=401)
    data = _body(request)
    profile = request.user.profile
    profile.display_name = data.get('display_name') or ''
    profile.bio = data.get('bio') or ''
    profile.save()
    return JsonResponse({'user': public_user(request.user)})


def user_posts(request, user_id):
    posts = Post.objects.filter(user_id=user_id).select_related('user__profile')
    return JsonResponse({'posts': [post_dict(p, request.user) for p in posts]})


@csrf_exempt
@require_http_methods(['POST'])
def follow_user(request, user_id):
    if not request.user.is_authenticated:
        return JsonResponse({'error': 'Not logged in'}, status=401)
    if int(user_id) == request.user.id:
        return JsonResponse({'error': "Can't follow yourself"}, status=400)
    target = User.objects.filter(id=user_id).first()
    if not target:
        return JsonResponse({'error': 'User not found'}, status=404)
    Follow.objects.get_or_create(follower=request.user, following=target)
    return JsonResponse({'ok': True})


@csrf_exempt
@require_http_methods(['POST'])
def unfollow_user(request, user_id):
    if not request.user.is_authenticated:
        return JsonResponse({'error': 'Not logged in'}, status=401)
    Follow.objects.filter(follower=request.user, following_id=user_id).delete()
    return JsonResponse({'ok': True})


def search_users(request):
    q = request.GET.get('q', '')
    users = User.objects.filter(
        Q(username__icontains=q) | Q(profile__display_name__icontains=q)
    ).select_related('profile')[:20]
    return JsonResponse({'users': [public_user(u) for u in users]})


# ---------------- posts / feed ----------------

@require_http_methods(['GET'])
def feed(request):
    if not request.user.is_authenticated:
        return JsonResponse({'error': 'Not logged in'}, status=401)
    following_ids = Follow.objects.filter(follower=request.user).values_list('following_id', flat=True)
    posts = Post.objects.filter(
        Q(user=request.user) | Q(user_id__in=following_ids)
    ).select_related('user__profile')[:100]
    return JsonResponse({'posts': [post_dict(p, request.user) for p in posts]})


def explore_posts(request):
    posts = Post.objects.select_related('user__profile').all()[:50]
    return JsonResponse({'posts': [post_dict(p, request.user) for p in posts]})


@csrf_exempt
@require_http_methods(['POST'])
def create_post(request):
    if not request.user.is_authenticated:
        return JsonResponse({'error': 'Not logged in'}, status=401)
    data = _body(request)
    content = (data.get('content') or '').strip()
    if not content:
        return JsonResponse({'error': 'Post content required'}, status=400)
    post = Post.objects.create(user=request.user, content=content)
    return JsonResponse({'post': post_dict(post, request.user)})


@csrf_exempt
@require_http_methods(['DELETE'])
def delete_post(request, post_id):
    if not request.user.is_authenticated:
        return JsonResponse({'error': 'Not logged in'}, status=401)
    post = Post.objects.filter(id=post_id).first()
    if not post:
        return JsonResponse({'error': 'Not found'}, status=404)
    if post.user_id != request.user.id:
        return JsonResponse({'error': 'Not your post'}, status=403)
    post.delete()
    return JsonResponse({'ok': True})


@csrf_exempt
@require_http_methods(['POST'])
def like_post(request, post_id):
    if not request.user.is_authenticated:
        return JsonResponse({'error': 'Not logged in'}, status=401)
    post = Post.objects.filter(id=post_id).first()
    if not post:
        return JsonResponse({'error': 'Not found'}, status=404)
    Like.objects.get_or_create(post=post, user=request.user)
    return JsonResponse({'ok': True})


@csrf_exempt
@require_http_methods(['POST'])
def unlike_post(request, post_id):
    if not request.user.is_authenticated:
        return JsonResponse({'error': 'Not logged in'}, status=401)
    Like.objects.filter(post_id=post_id, user=request.user).delete()
    return JsonResponse({'ok': True})


# ---------------- comments ----------------

@csrf_exempt
@require_http_methods(['GET', 'POST'])
def comments_view(request, post_id):
    if request.method == 'GET':
        comments = Comment.objects.filter(post_id=post_id).select_related('user__profile')
        return JsonResponse({'comments': [comment_dict(c) for c in comments]})

    # POST
    if not request.user.is_authenticated:
        return JsonResponse({'error': 'Not logged in'}, status=401)
    data = _body(request)
    content = (data.get('content') or '').strip()
    if not content:
        return JsonResponse({'error': 'Comment content required'}, status=400)
    post = Post.objects.filter(id=post_id).first()
    if not post:
        return JsonResponse({'error': 'Not found'}, status=404)
    comment = Comment.objects.create(post=post, user=request.user, content=content)
    return JsonResponse({'comment': comment_dict(comment)})
