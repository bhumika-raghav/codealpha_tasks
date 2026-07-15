from django.conf import settings
from django.contrib import admin
from django.urls import include, path, re_path
from django.views.static import serve

urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/', include('core.urls')),

    # Serve the frontend's root page.
    path('', serve, {'document_root': settings.FRONTEND_DIR, 'path': 'index.html'}),

    # Serve every other frontend file (feed.html, css/style.css, js/api.js, ...)
    # straight from /public, exactly like express.static() did in the Node version.
    re_path(r'^(?P<path>.*)$', serve, {'document_root': settings.FRONTEND_DIR}),
]
