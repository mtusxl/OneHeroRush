from celery import shared_task
from django.utils import timezone
from .models import Quest
from django.db import transaction

@shared_task
def reset_daily_quests():
    '''
    Celery beat задача: reset ежедневных квестов (удаляет completed users, обновляет reset_at). Запускается ежедневно по crontab в settings.
    '''
    daily_quests = Quest.objects.filter(type='daily', reset_at__lt=timezone.now())
    for quest in daily_quests:
        with transaction.atomic():
            quest.users_completed.clear()
            quest.reset_at = timezone.now() + timezone.timedelta(days=1)
            quest.save()