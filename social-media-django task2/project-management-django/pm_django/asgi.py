import os

import django
from channels.auth import AuthMiddlewareStack
from channels.routing import ProtocolTypeRouter, URLRouter
from django.core.asgi import get_asgi_application

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'pm_django.settings')
django.setup()

django_asgi_app = get_asgi_application()

import core.routing  # noqa: E402  (import after django.setup())

application = ProtocolTypeRouter({
    'http': django_asgi_app,
    'websocket': AuthMiddlewareStack(
        URLRouter(core.routing.websocket_urlpatterns)
    ),
})
