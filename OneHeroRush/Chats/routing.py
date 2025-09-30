from django.urls import path
from . import consumers

websocket_urlpatterns = [
    path("ws/chat/global/", consumers.GlobalChatConsumer.as_asgi()),            # общий чат
    path("ws/chat/clan/<int:clan_id>/", consumers.ClanChatConsumer.as_asgi()),  # клановый чат
    path("ws/chat/pm/<int:user_id>/", consumers.PrivateChatConsumer.as_asgi()), # личные
    path("ws/chat/party/<int:party_id>/", consumers.PartyChatConsumer.as_asgi())# матч на 3 игрока
]
