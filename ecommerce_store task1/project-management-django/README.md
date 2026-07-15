# TaskFlow — Django Backend Version

Same collaborative project management tool (projects, Kanban boards, task
assignment, comments, **real-time updates**) — **backend rebuilt in Django**,
using **Django Channels** for WebSockets instead of Node's Socket.IO.
Frontend UI/UX is unchanged; only the real-time transport (`js/api.js` and
`project.html`) was adapted from socket.io to a native `WebSocket`.

## Stack
- **Backend:** Django 5 (Python) + SQLite (ORM)
- **Real-time:** Django Channels + Daphne (ASGI) — native WebSockets, no socket.io
- **Frontend:** Vanilla HTML/CSS/JS — unchanged UI, no build step
- **Auth:** Django's built-in `django.contrib.auth` (sessions, hashed passwords)

## Setup
```bash
cd project-management-django
python -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate
pip install -r requirements.txt

python manage.py migrate
python manage.py runserver
```
Then open **http://localhost:8000** in two browser tabs (log in as two
different users) to see real-time sync in action.

(Optional) `python manage.py createsuperuser` to browse data at `/admin`.

## Why this needed Channels (not plain Django)
Plain Django (WSGI) can't push messages to the browser on its own — it only
answers when the browser asks. The Node version used Socket.IO for
live task/comment updates, so the Django rebuild needed an equivalent:
**Django Channels** adds WebSocket support on top of Django using ASGI.
`daphne` (in `INSTALLED_APPS`) makes `manage.py runserver` speak both HTTP
and WebSocket automatically — no separate server process needed for this demo.

## Project structure
```
project-management-django/
├── manage.py
├── requirements.txt
├── pm_django/                # Django project
│   ├── settings.py            # includes CHANNEL_LAYERS + ASGI_APPLICATION
│   ├── urls.py                 # /api/* + serves the static frontend
│   ├── asgi.py                  # routes HTTP -> Django, WebSocket -> Channels
│   └── wsgi.py
├── core/                      # Django app — all the logic
│   ├── models.py                # Profile, Project, ProjectMember, Task, TaskComment, Notification
│   ├── views.py                  # every REST endpoint (JsonResponse-based)
│   ├── consumers.py               # NotificationConsumer + ProjectConsumer (WebSocket)
│   ├── routing.py                  # ws/ URL patterns
│   ├── urls.py                      # /api/... route table
│   ├── admin.py
│   └── migrations/0001_initial.py
└── public/                    # frontend (adapted from the Node version)
    ├── index.html / register.html / dashboard.html   # unchanged
    ├── project.html                                    # socket.io → native WebSocket
    ├── css/style.css                                     # unchanged
    └── js/api.js                                          # socket.io → native WebSocket
```

## Real-time flow
1. On `project.html`, the browser opens `ws://.../ws/project/<id>/`.
2. `core/consumers.py`'s `ProjectConsumer` checks the user is a project
   member (via the session, courtesy of Channels' `AuthMiddlewareStack`),
   then joins the channel-layer group `project_<id>`.
3. Whenever a task/comment/member change happens via a normal `POST`/`PUT`/
   `DELETE` view in `views.py`, that view calls `broadcast_project(...)`,
   which does `channel_layer.group_send(...)` to push the update to
   everyone in that group instantly.
4. Personal notifications work the same way through a `user_<id>` group and
   `/ws/notifications/`.

## API overview (all under `/api/`)
| Method | Route | Description |
|---|---|---|
| POST | register, login, logout | Auth |
| GET | me | Current user |
| GET | users?q= | Search users to invite |
| GET/POST | notifications, notifications/read | Notifications |
| GET/POST | projects | List / create projects |
| GET/DELETE | projects/:id | Project detail / delete |
| POST/DELETE | projects/:id/members(/:userId) | Invite / remove members |
| GET/POST | projects/:id/tasks | List / create tasks |
| PUT/DELETE | tasks/:id | Update / delete a task |
| GET/POST | tasks/:id/comments | Task comments |

## A note on CSRF
Same approach as the social media Django rebuild: API views are
`@csrf_exempt` so the frontend's plain `fetch()` calls need no extra
headers. Session auth still gates every write.

## Verified but not run
No internet access in the sandbox that built this, so `channels`/`daphne`
couldn't actually be installed and booted here. Every `.py` file was
checked with `python -m py_compile`, and every frontend `fetch()`/WebSocket
URL was cross-checked against the Django URL patterns by hand. Please run
it locally and send over any error you hit — happy to fix it.
