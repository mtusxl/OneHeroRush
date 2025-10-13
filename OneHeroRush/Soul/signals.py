from django.db.models.signals import post_save
from django.dispatch import receiver
import logging
from .models import SummonLevel
from common.tasks import send_mail_notification

logger = logging.getLogger(__name__)

@receiver(post_save, sender=SummonLevel)
def notify_level_up(sender, instance, **kwargs):
    try:
        try:
            previous = SummonLevel.objects.get(pk=instance.pk)
            if previous.level < instance.level:
                message = f"Достижение: Уровень призыва душ {instance.level} - +5 душ как бонус!"
                send_mail_notification.delay(instance.user.id, message)
                logger.info(f"Level up notification sent for user {instance.user.id} to level {instance.level}")
        except SummonLevel.DoesNotExist:
            logger.warning(f"Previous SummonLevel not found for user {instance.user.id}")
            
    except Exception as e:
        logger.error(f"Error in notify_level_up for user {instance.user.id}: {str(e)}")