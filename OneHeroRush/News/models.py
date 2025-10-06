from django.db import models
from django.conf import settings
from Messages.models import Messages


User = settings.AUTH_USER_MODEL



class MailTemplate(models.Model):
    """Шаблоны рассылок — чтобы не писать вручную каждый раз"""
    name = models.CharField(max_length=100, unique=True)
    subject = models.CharField(max_length=200)
    body = models.TextField()
    mail_type = models.CharField(max_length=16, choices=Messages.TYPE_CHOICES, default="system")
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Template: {self.name}"


class MailTask(models.Model):
    """Массовая рассылка"""
    STATUS_CHOICES = [
        ("pending", "Ожидает"),
        ("in_progress", "В процессе"),
        ("done", "Завершена"),
    ]
    template = models.ForeignKey(MailTemplate, on_delete=models.CASCADE, related_name="task_templates")
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    status = models.CharField(max_length=16, choices=STATUS_CHOICES, default="pending")
    filter_query = models.JSONField(default=dict, blank=True)  # например, {"is_active": true}
    target_count = models.IntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    completed_at = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return f"Task #{self.id} ({self.template.name})"
