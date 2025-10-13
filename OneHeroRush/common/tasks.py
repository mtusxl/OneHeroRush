from celery import shared_task
from django.db import transaction
from django.db.models import Sum
from django.contrib.auth import get_user_model
from django.core.exceptions import ObjectDoesNotExist
import logging
from Clans.models import Clan, ClanMember
from Messages.models import Messages
from channels.layers import get_channel_layer
from asgiref.sync import async_to_sync

logger = logging.getLogger(__name__)
User = get_user_model()

@shared_task(bind=True, max_retries=3)
def recalculate_mmr(self, user_id):
    """
    Пересчёт MMR игрока:
    - волны (прогресс)
    - достижения
    - мощь героев
    """
    try:
        logger.info(f"Starting MMR recalculation for user {user_id}")
        
        # Используем select_related и prefetch_related для оптимизации запросов
        user = User.objects.select_related('progress').prefetch_related(
            'achievements__achievement', 
            'characters'
        ).get(id=user_id)

        # Расчет волн
        waves_completed = 0
        if user.progress:
            waves_completed = user.progress.waves_completed
        else:
            logger.warning(f"User {user_id} has no progress record")

        # Расчет достижений
        achievements_points = user.achievements.aggregate(
            total_points=Sum('achievement__points')
        )['total_points'] or 0

        # Расчет мощи героев
        total_power = sum(char.compute_power() for char in user.characters.all())

        # Итоговый MMR
        new_mmr = waves_completed + achievements_points + total_power
        
        # Сохраняем только если изменился
        if user.mmr != new_mmr:
            user.mmr = new_mmr
            user.save(update_fields=["mmr"])
            logger.info(f"MMR updated for user {user_id}: {new_mmr} (waves: {waves_completed}, achievements: {achievements_points}, power: {total_power})")
        else:
            logger.debug(f"MMR unchanged for user {user_id}: {new_mmr}")

        # Обновляем рейтинг клана, если пользователь состоит в нём
        try:
            clan_member = ClanMember.objects.select_related('clan').get(user=user)
            clan_member.clan.recalc_total_mmr()
            logger.debug(f"Clan MMR recalc triggered for user {user_id}")
        except ClanMember.DoesNotExist:
            logger.debug(f"User {user_id} is not in a clan, skipping clan update")
            
        return f"MMR recalculated for user {user_id}: {new_mmr}"

    except User.DoesNotExist:
        logger.error(f"User {user_id} not found for MMR recalculation")
        return f"User {user_id} not found"
    except Exception as e:
        logger.error(f"Error recalculating MMR for user {user_id}: {str(e)}")
        # Повторяем задачу через 30 секунд
        raise self.retry(countdown=30, exc=e)

@shared_task(bind=True, max_retries=3)
def update_clan_rank(self, clan_id):
    '''
    Асинхронно обновляет ранг клана (сумма MMR членов), лимит участников (30 + бонус).
    '''
    try:
        logger.info(f"Starting clan rank update for clan {clan_id}")
        
        with transaction.atomic():
            # Блокируем клан для предотвращения race condition
            clan = Clan.objects.select_for_update().get(id=clan_id)
            
            # Оптимизированный запрос для подсчета MMR
            total_mmr_result = ClanMember.objects.filter(
                clan=clan
            ).aggregate(
                total_mmr=Sum('user__mmr')
            )
            total_mmr = total_mmr_result['total_mmr'] or 0
            
            # Расчет максимального количества участников
            max_members = 30 + (total_mmr // 1000)
            
            # Сохраняем только если есть изменения
            if clan.rank != total_mmr or clan.max_members != max_members:
                clan.rank = total_mmr
                clan.max_members = max_members
                clan.save(update_fields=['rank', 'max_members'])
                logger.info(f"Clan {clan_id} rank updated: MMR={total_mmr}, max_members={max_members}")
            else:
                logger.debug(f"Clan {clan_id} rank unchanged: MMR={total_mmr}")
                
        return f"Clan {clan_id} rank updated to {total_mmr}"

    except Clan.DoesNotExist:
        logger.error(f"Clan {clan_id} not found for rank update")
        return f"Clan {clan_id} not found"
    except Exception as e:
        logger.error(f"Error updating clan rank for clan {clan_id}: {str(e)}")
        raise self.retry(countdown=30, exc=e)

@shared_task(bind=True, max_retries=3)
def send_mail_notification(self, user_id: int, message: str, subject: str = "Уведомление", mail_type: str = "system"):
    """
    Асинхронно создаёт запись в Messages (почта/уведомление)
    и отправляет WebSocket-ивент пользователю.
    """
    try:
        logger.info(f"Sending notification to user {user_id}: {subject}")
        
        user = User.objects.get(id=user_id)

        with transaction.atomic():
            
            message_obj = Messages.objects.create(
                user=user,
                subject=subject,
                body=message,
                is_read=False,
                message_type=mail_type,
            )
            logger.debug(f"Message created for user {user_id}: ID {message_obj.id}")

        # Отправка WS-уведомления
        try:
            channel_layer = get_channel_layer()
            async_to_sync(channel_layer.group_send)(
                f"user_{user_id}",
                {
                    "type": "notification",
                    "message": {
                        "subject": subject,
                        "body": message,
                        "mail_type": mail_type,
                        "message_id": message_obj.id
                    },
                },
            )
            logger.debug(f"WebSocket notification sent to user {user_id}")
            
        except Exception as e:
            logger.error(f"Failed to send WebSocket notification to user {user_id}: {str(e)}")
            

        logger.info(f"Notification successfully sent to user {user_id}")
        return f"Notification sent to user {user_id}"

    except User.DoesNotExist:
        logger.error(f"User {user_id} not found for notification")
        return f"User {user_id} not found"
    except Exception as e:
        logger.error(f"Error sending notification to user {user_id}: {str(e)}")
        raise self.retry(countdown=30, exc=e)

