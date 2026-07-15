from django.conf import settings
from django.contrib import admin
from django.urls import include, path, re_path
from django.views.static import serve

urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/', include('core.urls')),

    path('', serve, {'document_root': settings.FRONTEND_DIR, 'path': 'index.html'}),
    re_path(r'^(?P<path>.*)$', serve, {'document_root': settings.FRONTEND_DIR}),
]
