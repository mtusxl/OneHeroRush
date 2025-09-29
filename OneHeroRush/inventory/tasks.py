# Если нужно bulk open async, но для простоты в view (если count большой, перемести в Celery)
from celery import shared_task
from django.contrib.auth import get_user_model
from django.db import transaction
from common.tasks import recalculate_mmr


User = get_user_model()  

@shared_task
def bulk_open_chest(user_id, count):
    from .models import Chest
    user = User.objects.get(id=user_id)

    if user.keys < count:
        raise ValueError("Not enough keys")

    # достаем первые N сундуков
    chests = list(Chest.objects.filter(user=user)[:count])
    if len(chests) < count:
        raise ValueError("Not enough chests")

    items = []
    with transaction.atomic():
        for chest in chests:
            item = chest.open()
            items.append(item.id)

    recalculate_mmr.delay(user_id)
    return items
