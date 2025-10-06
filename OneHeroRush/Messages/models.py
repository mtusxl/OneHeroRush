from django.conf import settings
from django.db import models

User = settings.AUTH_USER_MODEL

class Messages(models.Model):
    TYPE_CHOICES = [
        ("system", "Системное"),
        ("reward", "Награда"),
        ("promo", "Промо-акция"),
        ("event", "Ивент"),
        ("admin", "Админское сообщение"),
    ]
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    subject = models.CharField(max_length=200, blank=True, null=True)
    body = models.TextField()
    is_read = models.BooleanField(default=False)
    message_type = models.CharField(max_length=16, choices=TYPE_CHOICES, default="system")
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.subject} ({self.user})"