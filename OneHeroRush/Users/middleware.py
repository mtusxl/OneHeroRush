# Users/middleware.py
from urllib.parse import parse_qs
from channels.db import database_sync_to_async
from rest_framework.authtoken.models import Token
from django.contrib.auth.models import AnonymousUser

@database_sync_to_async
def get_user(scope):
    """Асинхронно получаем пользователя по токену из query string"""
    try:
        query_string = parse_qs(scope["query_string"].decode())
        token_key = query_string.get("token")
        
        if not token_key:
            return AnonymousUser()
            
        token_key = token_key[0]
        token = Token.objects.select_related("user").get(key=token_key)
        return token.user
        
    except Token.DoesNotExist:
        return AnonymousUser()
    except Exception:
        return AnonymousUser()

class TokenAuthMiddleware:
    """
    Middleware для авторизации по DRF токену через ?token=...
    """
    def __init__(self, inner):
        self.inner = inner

    async def __call__(self, scope, receive, send):
        scope["user"] = await get_user(scope)
        return await self.inner(scope, receive, send)

# Удобный shortcut для подключения
def TokenAuthMiddlewareStack(inner):
    from channels.auth import AuthMiddlewareStack
    return TokenAuthMiddleware(AuthMiddlewareStack(inner))


