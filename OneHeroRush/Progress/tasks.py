from datetime import timezone
from django.db import transaction
from celery import shared_task
from Users.models import User
from common.tasks import send_mail_notification


@shared_task
def calculate_offline_farm(user_id):
    '''
    Асинхронно считает оффлайн-фарм (gold/keys по времени AFK, онлайн > оффлайн бонус). Вызывается при логине/GET progress, добавляет в валюту.
    '''
    user = User.objects.get(id=user_id)
    progress = user.progress
    with transaction.atomic():
        time_offline = timezone.now() - progress.last_online
        hours = time_offline.total_seconds() / 3600
        gold_rate = 50  # Оффлайн, онлайн в реал-time +50% (в progress calc)
        keys_rate = 1
        gold = int(hours * gold_rate)
        keys = int(hours * keys_rate)
        user.gold += gold
        user.keys += keys
        progress.last_online = timezone.now()
        progress.save(update_fields=['last_online'])
        user.save(update_fields=['gold', 'keys'])
    # Уведомление, если >0
    if gold or keys:
        send_mail_notification.delay(user_id = user_id, messages=f"Оффлайн-фарм: +{gold} gold, +{keys} keys", mail_type="reward")