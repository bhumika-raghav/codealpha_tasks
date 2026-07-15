# SocialSphere — Django Backend Version

Same mini social media app as before (profiles, posts, comments, likes,
follow/unfollow) — **backend rebuilt in Django**, frontend kept 100%
identical (plain HTML/CSS/JS, copied byte-for-byte from the Node.js version).

## Stack
- **Backend:** Django 5 (Python) + SQLite (Django's default ORM/DB)
- **Frontend:** Vanilla HTML/CSS/JS — unchanged, no build step
- **Auth:** Django's built-in `django.contrib.auth` (session-based, hashed passwords via `User.objects.create_user`)

## Setup
```bash
cd social-media-django
python -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate
pip install -r requirements.txt

python manage.py migrate
python manage.py runserver
```
Then open **http://localhost:8000**

(Optional) create an admin login to browse data at `/admin`:
```bash
python manage.py createsuperuser
```

## Why routes look the way they do
The frontend JS (`public/js/api.js`, `public/js/posts.js`) was **not touched at
all** — it still calls things like `/api/posts/:id/like`. So `core/urls.py`
mirrors those exact paths (no trailing slashes) so nothing on the frontend
had to change.

## Project structure
```
social-media-django/
├── manage.py
├── requirements.txt
├── social_media_django/     # Django project (settings, root urls)
│   ├── settings.py
│   ├── urls.py               # wires /api/* + serves the static frontend
│   ├── wsgi.py / asgi.py
├── core/                     # Django app — all the actual logic
│   ├── models.py             # Profile, Post, Comment, Like, Follow
│   ├── views.py              # every API endpoint (JsonResponse-based)
│   ├── urls.py                # /api/... route table
│   ├── admin.py                # registers models in /admin
│   └── migrations/0001_initial.py
└── public/                   # ← identical frontend from the Node version
    ├── index.html / register.html / feed.html / explore.html / profile.html
    ├── css/style.css
    └── js/api.js, js/posts.js
```

## Models (`core/models.py`)
- `Profile` — extends Django's `User` with `display_name`, `bio`, `avatar_color` (auto-created via a `post_save` signal in `core/apps.py`)
- `Post` — `user` FK, `content`, `created_at`
- `Comment` — `post` FK, `user` FK, `content`, `created_at`
- `Like` — `post` + `user`, unique together (like/unlike toggle)
- `Follow` — `follower` + `following`, unique together

## API overview (all under `/api/`)
| Method | Route | Description |
|---|---|---|
| POST | register, login, logout | Auth (Django sessions) |
| GET | me | Current user |
| GET | users/:id | Profile + stats |
| PUT | users/me | Edit display name / bio |
| GET | users?q= | Search users |
| POST | users/:id/follow, unfollow | Follow system |
| GET | feed | Personalized feed |
| GET | posts/explore | All posts |
| POST/DELETE | posts, posts/:id | Create / delete post |
| POST | posts/:id/like, unlike | Like system |
| GET/POST | posts/:id/comments | Comments |

## A note on CSRF
These API views are decorated with `@csrf_exempt` so the frontend's plain
`fetch()` calls (copied unchanged from the Node version) keep working without
extra headers. Session auth still requires login, so this is fine for a demo
— in a production Django app you'd instead read the `csrftoken` cookie in
`api.js` and send it back as an `X-CSRFToken` header on state-changing
requests.

## Verified but not run
I don't have internet access in this sandbox to `pip install django` and
actually boot the server, so I hand-wrote the migration and double-checked
every file with `python -m py_compile` for syntax correctness. Please run
`python manage.py migrate` and `runserver` locally and let me know if
anything needs a fix.
