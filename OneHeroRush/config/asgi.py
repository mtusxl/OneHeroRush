# config/asgi.py
import os
import django
from django.core.asgi import get_asgi_application

# Сначала настраиваем Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

# Только ПОСЛЕ django.setup() импортируем всё остальное
from channels.routing import ProtocolTypeRouter, URLRouter
from channels.security.websocket import AllowedHostsOriginValidator
from Chats.routing import websocket_urlpatterns

# Импортируем middleware ПОСЛЕ настройки Django
from Users.middleware import TokenAuthMiddleware

application = ProtocolTypeRouter({
    "http": get_asgi_application(),
    "websocket": TokenAuthMiddleware(
            URLRouter(
                websocket_urlpatterns
            ))})