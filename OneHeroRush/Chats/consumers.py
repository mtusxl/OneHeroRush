import json
from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async
from django.contrib.auth import get_user_model
from .models import ChatMessage

User = get_user_model()

# ---- Базовый Consumer ----
class BaseChatConsumer(AsyncWebsocketConsumer):
    group_name = None  # будет задаваться в наследниках

    async def connect(self):
        if not self.scope["user"].is_authenticated:
            await self.close()
            return

        await self.channel_layer.group_add(self.group_name, self.channel_name)
        await self.accept()

    async def disconnect(self, close_code):
        await self.channel_layer.group_discard(self.group_name, self.channel_name)

    async def receive(self, text_data):
        """Получаем сообщение от клиента"""
        data = json.loads(text_data)
        message = data.get("message")

        if not message:
            return

        # сохраняем сообщение в БД
        await self.save_message(self.scope["user"], message)

        # рассылаем в группу
        await self.channel_layer.group_send(
            self.group_name,
            {"type": "chat_message", "user": self.scope["user"].username, "message": message}
        )

    async def chat_message(self, event):
        """Отправляем сообщение клиенту"""
        await self.send(text_data=json.dumps({
            "user": event["user"],
            "message": event["message"],
        }))

    # ---- сохранение в БД через ORM ----
    @database_sync_to_async
    def save_message(self, user, message):
        obj = ChatMessage.objects.create(user=user, room=self.group_name, content=message)

        # ограничиваем историю до 100 сообщений
        qs = ChatMessage.objects.filter(room=self.group_name).order_by("-created_at")
        if qs.count() > 100:
            # удалить всё, кроме последних 100
            ids_to_delete = qs.values_list("id", flat=True)[100:]
            ChatMessage.objects.filter(id__in=ids_to_delete).delete()
            
        return obj

# ---- Наследники ----

class GlobalChatConsumer(BaseChatConsumer):
    async def connect(self):
        self.group_name = "global_chat"
        await super().connect()

class ClanChatConsumer(BaseChatConsumer):
    async def connect(self):
        self.clan_id = self.scope["url_route"]["kwargs"]["clan_id"]
        self.group_name = f"clan_{self.clan_id}"
        await super().connect()

class PrivateChatConsumer(BaseChatConsumer):
    async def connect(self):
        target_user_id = self.scope["url_route"]["kwargs"]["user_id"]
        me = self.scope["user"].id

        # нормализуем порядок id, чтобы обе стороны подключались в одну и ту же группу
        users = sorted([me, target_user_id])
        self.group_name = f"pm_{users[0]}_{users[1]}"
        await super().connect()

class PartyChatConsumer(BaseChatConsumer):
    async def connect(self):
        self.party_id = self.scope["url_route"]["kwargs"]["party_id"]
        self.group_name = f"party_{self.party_id}"
        await super().connect()
