from django.utils import timezone
from django.db import transaction
from Messages.models import Messages
from .models import MailTask
from celery import shared_task



@shared_task
def send_mail_to_users(template, users):
    """Массовая вставка Mail для списка пользователей"""
    mails = [
        Messages(
            user=user,
            subject=template.subject,
            body=template.body,
            mail_type=template.mail_type,
            created_at=timezone.now()
        )
        for user in users
    ]
    Messages.objects.bulk_create(mails, batch_size=1000)  # оптимально для 10k пользователей


@shared_task
def run_mail_task(task_id):
    """Запустить рассылку по задаче"""
    from django.contrib.auth import get_user_model
    User = get_user_model()

    task = MailTask.objects.select_related("template").get(id=task_id)
    task.status = "in_progress"
    task.save(update_fields=["status"])

    qs = User.objects.all()

    # применяем фильтр, если указан
    filters = task.filter_query or {}
    if filters:
        qs = qs.filter(**filters)

    users = list(qs)
    task.target_count = len(users)
    send_mail_to_users.delay(task.template.id, [u.id for u in users])

    task.status = "done"
    task.completed_at = timezone.now()
    task.save(update_fields=["status", "completed_at", "target_count"])
    return task
