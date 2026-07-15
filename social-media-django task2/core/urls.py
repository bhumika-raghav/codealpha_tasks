from django.urls import path

from . import views

urlpatterns = [
    path('register', views.register),
    path('login', views.login_view),
    path('logout', views.logout_view),
    path('me', views.me),

    path('users', views.search_users),
    path('users/me', views.update_me),
    path('users/<int:user_id>', views.get_user),
    path('users/<int:user_id>/posts', views.user_posts),
    path('users/<int:user_id>/follow', views.follow_user),
    path('users/<int:user_id>/unfollow', views.unfollow_user),

    path('feed', views.feed),
    path('posts/explore', views.explore_posts),
    path('posts', views.create_post),
    path('posts/<int:post_id>', views.delete_post),
    path('posts/<int:post_id>/like', views.like_post),
    path('posts/<int:post_id>/unlike', views.unlike_post),
    path('posts/<int:post_id>/comments', views.comments_view),
]
