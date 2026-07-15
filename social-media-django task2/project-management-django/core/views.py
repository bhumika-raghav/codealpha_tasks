import json
import random

from channels.layers import get_channel_layer
from asgiref.sync import async_to_sync
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.models import User
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods

from .models import Notification, Project, ProjectMember, Task, TaskComment

COLORS = ['#6c5ce7', '#00b894', '#0984e3', '#e17055', '#d63031', '#fdcb6e', '#e84393', '#00cec9']

# NOTE ON CSRF: same reasoning as the social media project — these are a
# small JSON API called by fetch(), exempted from CSRF checks so the plain
# frontend JS doesn't need to juggle tokens. Session auth still gates access.


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
        'avatar_color': profile.avatar_color,
    }


def is_member(project_id, user_id):
    return ProjectMember.objects.filter(project_id=project_id, user_id=user_id).exists()


def notify(user_id, message, link=None):
    Notification.objects.create(user_id=user_id, message=message, link=link)
    channel_layer = get_channel_layer()
    async_to_sync(channel_layer.group_send)(
        f'user_{user_id}',
        {'type': 'notify', 'message': message, 'link': link},
    )


def broadcast_project(project_id, event_type, payload):
    channel_layer = get_channel_layer()
    async_to_sync(channel_layer.group_send)(
        f'project_{project_id}',
        {'type': 'project_event', 'event_type': event_type, 'payload': payload},
    )


def task_dict(task):
    return {
        'id': task.id,
        'project_id': task.project_id,
        'title': task.title,
        'description': task.description,
        'status': task.status,
        'assignee_id': task.assignee_id,
        'assignee_username': task.assignee.username if task.assignee_id else None,
        'assignee_name': (task.assignee.profile.display_name or task.assignee.username) if task.assignee_id else None,
        'assignee_color': task.assignee.profile.avatar_color if task.assignee_id else None,
        'due_date': task.due_date.isoformat() if task.due_date else None,
        'position': task.position,
        'created_at': task.created_at.isoformat(),
        'commentCount': task.comments.count(),
    }


def comment_dict(comment):
    profile = comment.user.profile
    return {
        'id': comment.id,
        'task_id': comment.task_id,
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
    profile = user.profile  # auto-created by the post_save signal
    profile.display_name = display_name or username
    profile.avatar_color = random.choice(COLORS)
    profile.save()

    login(request, user)
    return JsonResponse({'user': public_user(user)})


@csrf_exempt
@require_http_methods(['POST'])
def login_view(request):
    data = _body(request)
    user = authenticate(request, username=data.get('username') or '', password=data.get('password') or '')
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


def search_users(request):
    if not request.user.is_authenticated:
        return JsonResponse({'error': 'Not logged in'}, status=401)
    q = request.GET.get('q', '')
    users = User.objects.filter(username__icontains=q).select_related('profile')[:10]
    return JsonResponse({'users': [public_user(u) for u in users]})


# ---------------- notifications ----------------

def list_notifications(request):
    if not request.user.is_authenticated:
        return JsonResponse({'error': 'Not logged in'}, status=401)
    notifs = Notification.objects.filter(user=request.user)[:30]
    return JsonResponse({'notifications': [{
        'id': n.id, 'message': n.message, 'link': n.link,
        'read': n.read, 'created_at': n.created_at.isoformat(),
    } for n in notifs]})


@csrf_exempt
@require_http_methods(['POST'])
def mark_notifications_read(request):
    if not request.user.is_authenticated:
        return JsonResponse({'error': 'Not logged in'}, status=401)
    Notification.objects.filter(user=request.user).update(read=True)
    return JsonResponse({'ok': True})


# ---------------- projects ----------------

@csrf_exempt
@require_http_methods(['GET', 'POST'])
def list_projects_or_create(request):
    if not request.user.is_authenticated:
        return JsonResponse({'error': 'Not logged in'}, status=401)

    if request.method == 'POST':
        data = _body(request)
        name = (data.get('name') or '').strip()
        if not name:
            return JsonResponse({'error': 'Project name required'}, status=400)
        project = Project.objects.create(name=name, description=data.get('description') or '', owner=request.user)
        ProjectMember.objects.create(project=project, user=request.user, role='owner')
        return JsonResponse({'project': {
            'id': project.id, 'name': project.name, 'description': project.description,
            'owner_id': project.owner_id, 'created_at': project.created_at.isoformat(),
        }})

    memberships = ProjectMember.objects.filter(user=request.user).select_related('project')
    projects = []
    for m in memberships:
        p = m.project
        projects.append({
            'id': p.id, 'name': p.name, 'description': p.description,
            'owner_id': p.owner_id, 'created_at': p.created_at.isoformat(),
            'taskCount': p.tasks.count(), 'memberCount': p.members.count(),
        })
    projects.sort(key=lambda x: x['created_at'], reverse=True)
    return JsonResponse({'projects': projects})


@require_http_methods(['GET', 'DELETE'])
def project_detail(request, project_id):
    if not request.user.is_authenticated:
        return JsonResponse({'error': 'Not logged in'}, status=401)
    project = Project.objects.filter(id=project_id).first()
    if not project:
        return JsonResponse({'error': 'Not found'}, status=404)

    if request.method == 'DELETE':
        if project.owner_id != request.user.id:
            return JsonResponse({'error': 'Only the owner can delete this project'}, status=403)
        project.delete()
        return JsonResponse({'ok': True})

    if not is_member(project.id, request.user.id):
        return JsonResponse({'error': 'Not a member'}, status=403)

    members = ProjectMember.objects.filter(project=project).select_related('user__profile')
    return JsonResponse({
        'project': {
            'id': project.id, 'name': project.name, 'description': project.description,
            'owner_id': project.owner_id, 'created_at': project.created_at.isoformat(),
        },
        'members': [{
            'id': m.user_id, 'username': m.user.username,
            'display_name': m.user.profile.display_name or m.user.username,
            'avatar_color': m.user.profile.avatar_color, 'role': m.role,
        } for m in members],
    })


@csrf_exempt
@require_http_methods(['POST'])
def add_member(request, project_id):
    if not request.user.is_authenticated:
        return JsonResponse({'error': 'Not logged in'}, status=401)
    project = Project.objects.filter(id=project_id).first()
    if not project:
        return JsonResponse({'error': 'Not found'}, status=404)
    if not is_member(project.id, request.user.id):
        return JsonResponse({'error': 'Not a member'}, status=403)

    username = (_body(request).get('username') or '').strip()
    target = User.objects.filter(username=username).first()
    if not target:
        return JsonResponse({'error': 'User not found'}, status=404)
    if is_member(project.id, target.id):
        return JsonResponse({'error': 'Already a member'}, status=400)

    ProjectMember.objects.create(project=project, user=target, role='member')
    notify(target.id, f'You were added to project "{project.name}"', f'/project.html?id={project.id}')
    broadcast_project(project.id, 'member-added', {'projectId': project.id})
    return JsonResponse({'ok': True})


@csrf_exempt
@require_http_methods(['DELETE'])
def remove_member(request, project_id, user_id):
    if not request.user.is_authenticated:
        return JsonResponse({'error': 'Not logged in'}, status=401)
    project = Project.objects.filter(id=project_id).first()
    if not project:
        return JsonResponse({'error': 'Not found'}, status=404)
    if project.owner_id != request.user.id:
        return JsonResponse({'error': 'Only the owner can remove members'}, status=403)
    if int(user_id) == project.owner_id:
        return JsonResponse({'error': "Can't remove the owner"}, status=400)
    ProjectMember.objects.filter(project=project, user_id=user_id).delete()
    return JsonResponse({'ok': True})


# ---------------- tasks ----------------

@require_http_methods(['GET', 'POST'])
def project_tasks(request, project_id):
    if not request.user.is_authenticated:
        return JsonResponse({'error': 'Not logged in'}, status=401)
    project = Project.objects.filter(id=project_id).first()
    if not project:
        return JsonResponse({'error': 'Not found'}, status=404)
    if not is_member(project.id, request.user.id):
        return JsonResponse({'error': 'Not a member'}, status=403)

    if request.method == 'GET':
        tasks = Task.objects.filter(project=project).select_related('assignee__profile')
        return JsonResponse({'tasks': [task_dict(t) for t in tasks]})

    data = _body(request)
    title = (data.get('title') or '').strip()
    if not title:
        return JsonResponse({'error': 'Task title required'}, status=400)
    assignee_id = data.get('assignee_id') or None
    if assignee_id and not is_member(project.id, assignee_id):
        return JsonResponse({'error': 'Assignee must be a project member'}, status=400)

    max_pos = Task.objects.filter(project=project, status='todo').count()
    task = Task.objects.create(
        project=project, title=title, description=data.get('description') or '',
        assignee_id=assignee_id, created_by=request.user, due_date=data.get('due_date') or None,
        position=max_pos + 1,
    )
    if assignee_id and int(assignee_id) != request.user.id:
        notify(assignee_id, f'You were assigned task "{task.title}"', f'/project.html?id={project.id}')
    payload = task_dict(task)
    broadcast_project(project.id, 'task-created', payload)
    return JsonResponse({'task': payload})


@csrf_exempt
@require_http_methods(['PUT', 'DELETE'])
def task_detail(request, task_id):
    if not request.user.is_authenticated:
        return JsonResponse({'error': 'Not logged in'}, status=401)
    task = Task.objects.filter(id=task_id).first()
    if not task:
        return JsonResponse({'error': 'Not found'}, status=404)
    if not is_member(task.project_id, request.user.id):
        return JsonResponse({'error': 'Not a member'}, status=403)

    if request.method == 'DELETE':
        project_id = task.project_id
        task.delete()
        broadcast_project(project_id, 'task-deleted', {'id': int(task_id)})
        return JsonResponse({'ok': True})

    data = _body(request)
    old_status = task.status
    old_assignee_id = task.assignee_id

    if 'title' in data:
        task.title = data['title']
    if 'description' in data:
        task.description = data['description']
    if 'status' in data:
        task.status = data['status']
    if 'assignee_id' in data:
        task.assignee_id = data['assignee_id'] or None
    if 'due_date' in data:
        task.due_date = data['due_date'] or None
    if 'position' in data:
        task.position = data['position']
    task.save()

    if 'status' in data and data['status'] != old_status and task.assignee_id and task.assignee_id != request.user.id:
        notify(task.assignee_id, f'Task "{task.title}" moved to {data["status"]}', f'/project.html?id={task.project_id}')
    if 'assignee_id' in data and task.assignee_id != old_assignee_id and task.assignee_id and task.assignee_id != request.user.id:
        notify(task.assignee_id, f'You were assigned task "{task.title}"', f'/project.html?id={task.project_id}')

    payload = task_dict(task)
    broadcast_project(task.project_id, 'task-updated', payload)
    return JsonResponse({'task': payload})


# ---------------- task comments ----------------

@csrf_exempt
@require_http_methods(['GET', 'POST'])
def task_comments(request, task_id):
    if not request.user.is_authenticated:
        return JsonResponse({'error': 'Not logged in'}, status=401)
    task = Task.objects.filter(id=task_id).first()
    if not task:
        return JsonResponse({'error': 'Not found'}, status=404)
    if not is_member(task.project_id, request.user.id):
        return JsonResponse({'error': 'Not a member'}, status=403)

    if request.method == 'GET':
        comments = TaskComment.objects.filter(task=task).select_related('user__profile')
        return JsonResponse({'comments': [comment_dict(c) for c in comments]})

    content = (_body(request).get('content') or '').strip()
    if not content:
        return JsonResponse({'error': 'Comment required'}, status=400)
    comment = TaskComment.objects.create(task=task, user=request.user, content=content)

    if task.assignee_id and task.assignee_id != request.user.id:
        notify(task.assignee_id, f'New comment on task "{task.title}"', f'/project.html?id={task.project_id}')

    payload = comment_dict(comment)
    broadcast_project(task.project_id, 'comment-added', {'taskId': task.id, 'comment': payload})
    return JsonResponse({'comment': payload})
