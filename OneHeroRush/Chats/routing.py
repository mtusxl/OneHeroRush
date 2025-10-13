from django.urls import path
from .consumers import GlobalChatConsumer, ClanChatConsumer, PrivateChatConsumer, PartyChatConsumer, NotificationConsumer

websocket_urlpatterns = [
    path("ws/chat/global/", GlobalChatConsumer.as_asgi()),            # общий чат
    path("ws/chat/clan/<int:clan_id>/", ClanChatConsumer.as_asgi()),  # клановый чат
    path("ws/chat/pm/<int:user_id>/", PrivateChatConsumer.as_asgi()), # личные
    path("ws/chat/party/<int:party_id>/", PartyChatConsumer.as_asgi()),# матч на 3 игрока
    path("ws/notifications/", NotificationConsumer.as_asgi()), # notifications
]

