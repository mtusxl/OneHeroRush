# models.py
import logging
from django.db import models
from django.conf import settings
from Messages.models import Messages

logger = logging.getLogger(__name__)
User = settings.AUTH_USER_MODEL

class MailTemplate(models.Model):
    """Шаблоны рассылок — чтобы не писать вручную каждый раз"""
    name = models.CharField(max_length=100, unique=True, db_index=True)
    subject = models.CharField(max_length=200)
    body = models.TextField()
    mail_type = models.CharField(max_length=16, choices=Messages.TYPE_CHOICES, default="system")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        indexes = [
            models.Index(fields=['name']),
        ]

    def __str__(self):
        return f"Template: {self.name}"

    def save(self, *args, **kwargs):
        try:
            is_new = not self.pk
            logger.debug(f"Saving mail template: {self.name}, new={is_new}")
            
            super().save(*args, **kwargs)
            
            logger.info(f"Mail template saved: ID={self.pk}, name={self.name}")
            
        except Exception as e:
            logger.error(f"Error saving mail template {self.name}: {str(e)}")
            raise


class MailTask(models.Model):
    """Массовая рассылка"""
    STATUS_CHOICES = [
        ("pending", "Ожидает"),
        ("in_progress", "В процессе"),
        ("done", "Завершена"),
        ("failed", "Ошибка"),
    ]
    
    template = models.ForeignKey(MailTemplate, on_delete=models.CASCADE, related_name="task_templates")
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    status = models.CharField(max_length=16, choices=STATUS_CHOICES, default="pending", db_index=True)
    filter_query = models.JSONField(default=dict, blank=True)
    target_count = models.IntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    error_message = models.TextField(blank=True, null=True)

    class Meta:
        indexes = [
            models.Index(fields=['status', 'created_at']),
        ]
        ordering = ['-created_at']

    def __str__(self):
        return f"Task #{self.id} ({self.template.name})"

    def save(self, *args, **kwargs):
        try:
            logger.debug(f"Saving mail task: template={self.template_id}, status={self.status}")
            
            super().save(*args, **kwargs)
            
            logger.info(f"Mail task saved: ID={self.pk}, template={self.template_id}, status={self.status}")
            
        except Exception as e:
            logger.error(f"Error saving mail task: {str(e)}")
            raise