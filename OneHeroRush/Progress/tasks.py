from datetime import timedelta
from django.db import transaction
from celery import shared_task
from django.utils import timezone
import logging
from Users.models import User
from .models import Progress
from common.tasks import send_mail_notification

logger = logging.getLogger(__name__)

@shared_task(bind=True, max_retries=3)
def calculate_offline_farm(self, user_id):
    '''
    Асинхронно считает оффлайн-фарм и сбрасывает его после начисления
    '''
    try:
        logger.info(f"Starting offline farm calculation for user {user_id}")
        
        user = User.objects.select_related('progress').get(id=user_id)
        
        if not hasattr(user, 'progress'):
            logger.error(f"User {user_id} has no progress record")
            return
            
        with transaction.atomic():
            # Блокируем запись для предотвращения race condition
            locked_user = User.objects.select_for_update().get(id=user_id)
            locked_progress = Progress.objects.select_for_update().get(user=locked_user)
            
            current_time = timezone.now()
            time_offline = current_time - locked_progress.last_online
            
            # Защита от отрицательного времени
            if time_offline.total_seconds() < 0:
                logger.warning(f"Negative offline time for user {user_id}, resetting to 0")
                time_offline = timedelta(0)
            
            # Ограничиваем максимальное время оффлайн-фарма (24 часа)
            max_offline_time = timedelta(hours=24)
            if time_offline > max_offline_time:
                time_offline = max_offline_time
                logger.info(f"Offline time capped at 24 hours for user {user_id}")
            
            hours_offline = time_offline.total_seconds() / 3600
            
            # Рассчитываем награды
            gold_rate = 50
            keys_rate = 1
            
            gold_earned = int(hours_offline * gold_rate)
            keys_earned = int(hours_offline * keys_rate)
            
            if gold_earned > 0 or keys_earned > 0:
                # Обновляем валюту пользователя
                locked_user.gold += gold_earned
                locked_user.keys += keys_earned
                
                # СБРАСЫВАЕМ оффлайн-фарм после начисления
                locked_progress.offline_gold = 0
                locked_progress.offline_keys = 0
                locked_progress.last_online = current_time
                
                # Сохраняем изменения
                locked_progress.save(update_fields=['last_online', 'offline_gold', 'offline_keys'])
                locked_user.save(update_fields=['gold', 'keys'])
                
                logger.info(f"Offline farm completed for user {user_id}: +{gold_earned} gold, +{keys_earned} keys for {hours_offline:.2f} hours offline")
                
                # Отправляем уведомление
                try:
                    send_mail_notification.delay(
                        user_id=user_id,
                        message=f"Оффлайн-фарм: +{gold_earned} gold, +{keys_earned} keys",
                        mail_type="reward"
                    )
                    logger.debug(f"Notification sent for offline farm to user {user_id}")
                except Exception as e:
                    logger.error(f"Failed to send notification for user {user_id}: {str(e)}")
                    
            else:
                logger.debug(f"No offline farm rewards for user {user_id}: only {hours_offline:.2f} hours offline")
                # Обновляем только время последнего онлайна
                locked_progress.last_online = current_time
                locked_progress.save(update_fields=['last_online'])
                
    except User.DoesNotExist:
        logger.error(f"User {user_id} not found for offline farm calculation")
        return
    except Progress.DoesNotExist:
        logger.error(f"Progress record not found for user {user_id}")
        return
    except Exception as e:
        logger.error(f"Error calculating offline farm for user {user_id}: {str(e)}")
        raise self.retry(countdown=60, exc=e)