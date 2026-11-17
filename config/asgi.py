import os
from django.core.asgi import get_asgi_application
from channels.routing import ProtocolTypeRouter, URLRouter
from channels.auth import AuthMiddlewareStack

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings.production')

django_asgi_app = get_asgi_application()

from apps.notifications import routing as notif_routing
from apps.discussions import routing as discussion_routing

application = ProtocolTypeRouter({
    'http': django_asgi_app,
    'websocket': AuthMiddlewareStack(
        URLRouter(
            notif_routing.websocket_urlpatterns +
            discussion_routing.websocket_urlpatterns
        )
    ),
})
