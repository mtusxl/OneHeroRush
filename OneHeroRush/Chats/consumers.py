from datetime import timedelta
from django.utils import timezone
import json
import logging
from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async
from django.contrib.auth import get_user_model
from django.core.exceptions import PermissionDenied, ObjectDoesNotExist
from django.db import transaction
from .models import ChatMessage
from Clans.models import Clan, ClanMember

logger = logging.getLogger(__name__)
User = get_user_model()

# ---- Базовый Consumer ----
class BaseChatConsumer(AsyncWebsocketConsumer):
    group_name = None

    async def connect(self):
        try:
            user = self.scope["user"]
            logger.info(f"WebSocket connection attempt from user: {user.username if user.is_authenticated else 'anonymous'} ({user.id if user.is_authenticated else 'N/A'})")
            
            if not user.is_authenticated:
                logger.warning(f"Unauthorized connection attempt from anonymous user")
                await self.close(code=4001) 
                return

            await self.channel_layer.group_add(self.group_name, self.channel_name)
            await self.accept()
            
            logger.info(f"WebSocket connected successfully: user={user.username}, group={self.group_name}, channel={self.channel_name}")
            
        except Exception as e:
            logger.error(f"Error during WebSocket connection for user {self.scope.get('user', 'unknown')}: {str(e)}")
            await self.close()

    async def disconnect(self, close_code):
        try:
            await self.channel_layer.group_discard(self.group_name, self.channel_name)
            logger.info(f"WebSocket disconnected: user={self.scope['user'].username}, group={self.group_name}, code={close_code}")
        except Exception as e:
            logger.error(f"Error during WebSocket disconnect: {str(e)}")

    async def receive(self, text_data):
        """Получаем сообщение от клиента"""
        try:
            user = self.scope["user"]
            logger.debug(f"Message received from user {user.username}: {text_data[:100]}...")
            
            data = json.loads(text_data)
            message = data.get("message", "").strip()

            if not message:
                logger.warning(f"Empty message from user {user.username}")
                await self.send(text_data=json.dumps({"error": "Message cannot be empty"}))
                return

            if len(message) > 1000:
                logger.warning(f"Message too long from user {user.username}: {len(message)} chars")
                await self.send(text_data=json.dumps({"error": "Message too long (max 1000 chars)"}))
                return

            # Дополнительная проверка на спам/флуд (можно расширить с Redis counter)
            if await self._is_spamming(user):
                logger.warning(f"Spam detected from user {user.username}")
                await self.send(text_data=json.dumps({"error": "Message rate limit exceeded"}))
                return

            # сохраняем сообщение в БД
            saved_message = await self.save_message(user, message)
            logger.debug(f"Message saved to DB with ID: {saved_message.id}")

            # рассылаем в группу
            await self.channel_layer.group_send(
                self.group_name,
                {
                    "type": "chat_message", 
                    "user": user.username, 
                    "user_id": user.id,
                    "message": message,
                    "timestamp": saved_message.created_at.isoformat()
                }
            )
            
            logger.info(f"Message broadcasted to group {self.group_name} from user {user.username}")

        except json.JSONDecodeError as e:
            logger.error(f"Invalid JSON received from user {self.scope['user'].username}: {text_data}")
            await self.send(text_data=json.dumps({"error": "Invalid message format"}))
        except Exception as e:
            logger.error(f"Error processing message from user {self.scope['user'].username}: {str(e)}")
            await self.send(text_data=json.dumps({"error": "Internal server error"}))

    async def chat_message(self, event):
        """Отправляем сообщение клиенту"""
        try:
            message_data = {
                "user": event["user"],
                "user_id": event.get("user_id"),
                "message": event["message"],
                "timestamp": event.get("timestamp")
            }
            
            await self.send(text_data=json.dumps(message_data, ensure_ascii=False))
            logger.debug(f"Message sent to client: {event['user']}: {event['message'][:50]}...")
            
        except Exception as e:
            logger.error(f"Error sending message to client: {str(e)}")

    # ---- Проверка на спам (stub, реализуйте с Redis) ----
    @database_sync_to_async
    def _is_spamming(self, user):
        now  = timezone.now() 
        recent_count = ChatMessage.objects.filter(
            user=user,
            room=self.group_name,
            created_at__gte=now - timedelta(seconds=60)
        ).count()
        
        if recent_count >= 5:
            return True
        return False

    # ---- сохранение в БД через ORM ----
    @database_sync_to_async
    def save_message(self, user, message):
        try:
            
            logger.debug(f"Saving message to DB: user={user.username}, room={self.group_name}")
            
            obj = ChatMessage.objects.create(
                user=user, 
                room=self.group_name, 
                content=message
            )
            logger.info(f"Message saved successfully: ID={obj.id}")

            # ограничиваем историю до 100 сообщений
            self._cleanup_old_messages()
            
            return obj
            
        except Exception as e:
            logger.error(f"Error saving message to DB: user={user.username}, error={str(e)}")
        raise

    def _cleanup_old_messages(self):
        """Очистка старых сообщений"""
        try:
            qs = ChatMessage.objects.filter(room=self.group_name).order_by("-created_at")
            total_messages = qs.count()
            
            if total_messages <= 100:
                logger.debug(f"No cleanup needed for room {self.group_name}: {total_messages} messages")
                return
                
            ids_to_delete = qs.values_list("id", flat=True)[100:]
            deleted_count, _ = ChatMessage.objects.filter(id__in=ids_to_delete).delete()
            logger.info(f"Cleaned up {deleted_count} old messages from room {self.group_name}")
                
        except Exception as e:
            logger.error(f"Error cleaning up old messages in room {self.group_name}: {str(e)}")

# ---- Наследники ----

class GlobalChatConsumer(BaseChatConsumer):
    async def connect(self):
        try:
            self.group_name = "global_chat"
            logger.info(f"Global chat connection attempt from user: {self.scope['user'].username}")
            await super().connect()
        except Exception as e:
            logger.error(f"Error in GlobalChatConsumer connect: {str(e)}")
            await self.close()

class ClanChatConsumer(BaseChatConsumer):
    async def connect(self):
        try:
            self.clan_id = int(self.scope["url_route"]["kwargs"]["clan_id"])  # Приведение к int для безопасности
            self.group_name = f"clan_{self.clan_id}"
            
            user = self.scope["user"]
            logger.info(f"Clan chat connection attempt: user={user.username}, clan_id={self.clan_id}")
            
            if not await self._clan_exists():
                logger.warning(f"Clan does not exist: clan_id={self.clan_id}")
                await self.close(code=4004)  # Custom code for not found
                return

            # Проверка принадлежности пользователя к клану и отсутствие бана
            membership_status = await self._check_clan_membership()
            if membership_status == "not_member":
                logger.warning(f"User {user.username} attempted to access clan chat without membership: clan_id={self.clan_id}")
                await self.close(code=4003)
                return
            elif membership_status == "banned":
                logger.warning(f"User {user.username} is banned from clan chat: clan_id={self.clan_id}")
                await self.close(code=4003)
                return
                
            await super().connect()
            
        except (KeyError, ValueError) as e:
            logger.error(f"Invalid or missing clan_id in URL route: {str(e)}")
            await self.close()
        except Exception as e:
            logger.error(f"Error in ClanChatConsumer connect: {str(e)}")
            await self.close()

    @database_sync_to_async
    def _clan_exists(self):
        try:
            exists = Clan.objects.filter(id=self.clan_id).exists()
            logger.debug(f"Clan existence check for ID {self.clan_id}: {exists}")
            return exists
        except Exception as e:
            logger.error(f"Error checking clan existence: {str(e)}")
            return False

    @database_sync_to_async
    def _check_clan_membership(self):
        """Получаем информацию о членстве пользователя в клане"""
        try:
            user = self.scope["user"]
    
            clan_member = ClanMember.objects.filter(
                user=user, 
                clan_id=self.clan_id
            ).first()
            
            if clan_member:
                logger.debug(f"Clan membership found for user {user.username}: clan_id={self.clan_id}, officer={clan_member.is_officer}")
            else:
                logger.debug(f"No clan membership found for user {user.username} in clan {self.clan_id}")
                
            return clan_member
            
        except Exception as e:
            logger.error(f"Error getting clan membership for user {self.scope['user'].username}: {str(e)}")
            return None

class PrivateChatConsumer(BaseChatConsumer):
    async def connect(self):
        try:
            target_user_id = int(self.scope["url_route"]["kwargs"]["user_id"]) 
            me = self.scope["user"].id

            if me == target_user_id:
                logger.warning(f"Self-chat attempt by user {me}")
                await self.close(code=4005)  
                return

            logger.info(f"Private chat connection: user_id={me}, target_user_id={target_user_id}")

            # Проверка существования целевого пользователя
            if not await self._check_user_exists(target_user_id):
                logger.warning(f"Target user does not exist: user_id={target_user_id}")
                await self.close(code=4004)
                return


            # нормализуем порядок id
            users = sorted([me, target_user_id])
            self.group_name = f"pm_{users[0]}_{users[1]}"
            
            logger.debug(f"Private chat group name: {self.group_name}")
            await super().connect()
            
        except (KeyError, ValueError) as e:
            logger.error(f"Invalid user_id format: {str(e)}")
            await self.close()
        except Exception as e:
            logger.error(f"Error in PrivateChatConsumer connect: {str(e)}")
            await self.close()

    @database_sync_to_async
    def _check_user_exists(self, user_id):
        """Проверка существования пользователя"""
        try:
            exists = User.objects.filter(id=user_id).exists()
            logger.debug(f"User existence check for ID {user_id}: {exists}")
            return exists
        except Exception as e:
            logger.error(f"Error checking user existence: {str(e)}")
            return False

class PartyChatConsumer(BaseChatConsumer):
    async def connect(self):
        try:
            self.party_id = int(self.scope["url_route"]["kwargs"]["party_id"])  # Приведение к int
            self.group_name = f"party_{self.party_id}"
            logger.info(f"Party chat connection attempt: party_id={self.party_id}, user={self.scope['user'].username}")
            await super().connect()
        except (KeyError, ValueError) as e:
            logger.error(f"Invalid party_id: {str(e)}")
            await self.close()
        except Exception as e:
            logger.error(f"Error in PartyChatConsumer connect: {str(e)}")
            await self.close()

#_______________________________________________________________________________
# Notifications

class NotificationConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        try:
            user = self.scope["user"]
            logger.info(f"WebSocket connection attempt: user={user.username if user.is_authenticated else 'anonymous'}")
            
            # ВРЕМЕННО: разрешаем подключение без проверки аутентификации
            # if user.is_anonymous:
            #     logger.warning("WebSocket connection rejected: anonymous user")
            #     await self.close(code=4001)
            #     return

            # Каждому пользователю — отдельная группа для уведомлений
            self.group_name = f"user_{user.id}"
            await self.channel_layer.group_add(self.group_name, self.channel_name)

            await self.accept()
            logger.info(f"✅ WebSocket connected successfully: user={user.username}, group={self.group_name}")
            
        except Exception as e:
            logger.error(f"Error during WebSocket connection: {str(e)}")
            await self.close()

    async def notification(self, event):
        """Отправляем уведомление пользователю"""
        try:
            await self.send(text_data=json.dumps(event["message"]))
            logger.debug(f"Notification sent to {self.scope['user'].username}: {event['message']}")
        except Exception as e:
            logger.error(f"Error sending WS notification to {self.scope['user'].username}: {str(e)}")

