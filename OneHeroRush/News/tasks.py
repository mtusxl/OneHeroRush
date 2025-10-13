# tasks.py
import logging
from django.utils import timezone
from django.db import transaction
from django.core.exceptions import ObjectDoesNotExist
from celery import shared_task
from Messages.models import Messages
from .models import MailTask, MailTemplate

logger = logging.getLogger(__name__)

def send_mail_to_users(template, user_ids):
    """функция для отправки писем"""
    try:
        logger.info(f"Starting bulk mail send: template={template.name}, users_count={len(user_ids)}")
        
        batch_size = 500
        total_created = 0
        
        for i in range(0, len(user_ids), batch_size):
            batch_user_ids = user_ids[i:i + batch_size]
            
            mails = [
                Messages(
                    user_id=user_id,
                    subject=template.subject,
                    body=template.body,
                    message_type=template.mail_type,
                )
                for user_id in batch_user_ids
            ]
            
            created_count = len(Messages.objects.bulk_create(mails))
            total_created += created_count
            
            logger.debug(f"Batch {i//batch_size + 1} created: {created_count} messages")
        
        logger.info(f"Bulk mail send completed: template={template.name}, total_created={total_created}")
        return total_created
        
    except Exception as e:
        logger.error(f"Error in bulk mail send for template {template.name}: {str(e)}")
        raise


@shared_task(bind=True, max_retries=3)
def run_mail_task(self, task_id):
    """Единая задача для рассылки"""
    try:
        logger.info(f"Starting mail task: task_id={task_id}")
        
        with transaction.atomic():
            task = MailTask.objects.select_for_update().select_related("template").get(id=task_id)
            
            if task.status == 'in_progress':
                logger.warning(f"Task {task_id} is already in progress")
                return
            
            task.status = "in_progress"
            task.save(update_fields=["status"])
        
        # Получаем пользователей
        from django.contrib.auth import get_user_model
        User = get_user_model()

        qs = User.objects.all()
        filters = task.filter_query or {}  
        
        if filters:
            logger.debug(f"Applying filters: {filters}")
            qs = qs.filter(**filters)

        user_ids = list(qs.values_list('id', flat=True))
        
        logger.info(f"Task {task_id} target users: {len(user_ids)}")

        if not user_ids:
            logger.warning(f"No users found for task {task_id} with filters {filters}")
            task.status = "done"
            task.completed_at = timezone.now()
            task.save(update_fields=["status", "completed_at", "target_count"])
            return

        total_created = send_mail_to_users(task.template, user_ids)
        
        # Обновляем статус задачи
        task.status = "done"
        task.target_count = total_created
        task.completed_at = timezone.now()
        task.save(update_fields=["status", "completed_at", "target_count"])
        
        logger.info(f"Mail task completed: task_id={task_id}, users={total_created}")

    except MailTask.DoesNotExist:
        logger.error(f"MailTask not found: {task_id}")
        raise
    except Exception as e:
        logger.error(f"Error in mail task {task_id}: {str(e)}")
        
        try:
            task = MailTask.objects.get(id=task_id)
            task.status = "failed"
            task.error_message = str(e)
            task.save(update_fields=["status", "error_message"])
        except MailTask.DoesNotExist:
            pass
            
        raise self.retry(countdown=300, exc=e)