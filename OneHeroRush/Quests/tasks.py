from celery import shared_task
from django.utils import timezone
from django.db import transaction
import logging
from .models import Quest

logger = logging.getLogger(__name__)

@shared_task(bind=True, max_retries=3)
def reset_daily_quests(self):
    '''
    Celery beat задача: reset ежедневных квестов (удаляет completed users, обновляет reset_at). Запускается ежедневно по crontab в settings.
    '''
    try:
        logger.info("Starting daily quests reset")
        
        from datetime import timedelta
        current_time = timezone.now()
        
        # Получаем квесты, которые нужно сбросить
        daily_quests = Quest.objects.filter(type='daily')
        
        reset_count = 0
        for quest in daily_quests:
            try:
                with transaction.atomic():
                    users_count_before = quest.users_completed.count()
                    quest.users_completed.clear()
                    quest.reset_at = current_time + timedelta(days=1)
                    quest.save()
                    
                    reset_count += 1
                    logger.debug(f"Reset quest {quest.id}: cleared {users_count_before} users")
                    
            except Exception as e:
                logger.error(f"Error resetting quest {quest.id}: {str(e)}")
                continue
        
        logger.info(f"Daily quests reset completed. Reset {reset_count} quests")
        
    except Exception as e:
        logger.error(f"Error in reset_daily_quests task: {str(e)}")
        raise self.retry(countdown=300, exc=e)  # Повтор через 5 минут