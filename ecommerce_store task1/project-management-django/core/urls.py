from django.urls import path

from . import views

urlpatterns = [
    path('register', views.register),
    path('login', views.login_view),
    path('logout', views.logout_view),
    path('me', views.me),
    path('users', views.search_users),

    path('notifications', views.list_notifications),
    path('notifications/read', views.mark_notifications_read),

    path('projects', views.list_projects_or_create),
    path('projects/<int:project_id>', views.project_detail),
    path('projects/<int:project_id>/members', views.add_member),
    path('projects/<int:project_id>/members/<int:user_id>', views.remove_member),
    path('projects/<int:project_id>/tasks', views.project_tasks),

    path('tasks/<int:task_id>', views.task_detail),
    path('tasks/<int:task_id>/comments', views.task_comments),
]
