from django.db.models.signals import post_save
from django.dispatch import receiver
from .models import SummonLevel
from common.tasks import send_mail_notification  # Импорт из вашего модуля tasks, где @shared_task def send_mail_notification(user_id, message):

@receiver(post_save, sender=SummonLevel)
def notify_level_up(sender, instance, **kwargs):
    #if kwargs.get('created'): return
    user_id = instance.user.id
    message = f"Достижение: Уровень призыва душ {instance.level} - +5 душ как бонус!"  # По ТЗ, адаптировать под новости/достижения
    send_mail_notification.delay(user_id, message)