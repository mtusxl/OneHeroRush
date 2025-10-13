# tasks.py
import logging
from celery import shared_task
from django.contrib.auth import get_user_model
from django.db import transaction
from django.core.exceptions import ObjectDoesNotExist
from common.tasks import recalculate_mmr

logger = logging.getLogger(__name__)
User = get_user_model()

@shared_task
def bulk_open_chest(user_id, count):
    try:
        logger.info(f"Starting bulk chest open: user_id={user_id}, count={count}")
        
        user = User.objects.get(id=user_id)
        logger.debug(f"User found: {user.username}")

        if user.keys < count:
            logger.warning(f"Not enough keys for bulk open: user={user.username}, keys={user.keys}, needed={count}")
            raise ValueError("Not enough keys")

        # достаем первые N сундуков
        from .models import Chest
        chests = list(Chest.objects.filter(user=user)[:count])
        
        if len(chests) < count:
            logger.warning(f"Not enough chests: user={user.username}, has={len(chests)}, needed={count}")
            raise ValueError("Not enough chests")

        items = []
        with transaction.atomic():
            for chest in chests:
                try:
                    item = chest.open()
                    items.append(item.id)
                    logger.debug(f"Chest opened: {chest.id} → item {item.id}")
                except Exception as e:
                    logger.error(f"Error opening chest {chest.id}: {str(e)}")
                    raise

        logger.info(f"Bulk chest open completed: user={user.username}, items_created={len(items)}")

        recalculate_mmr.delay(user_id)
        logger.debug("MMR recalculation task queued")

        return items

    except User.DoesNotExist:
        logger.error(f"User not found for bulk chest open: {user_id}")
        raise
    except Exception as e:
        logger.error(f"Error in bulk chest open task for user {user_id}: {str(e)}")
        raise