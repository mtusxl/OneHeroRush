import logging
from django.conf import settings
from django.db import models

logger = logging.getLogger(__name__)
User = settings.AUTH_USER_MODEL

class Messages(models.Model):
    TYPE_CHOICES = [
        ("system", "Системное"),
        ("reward", "Награда"),
        ("promo", "Промо-акция"),
        ("event", "Ивент"),
        ("admin", "Админское сообщение"),
    ]
    
    user = models.ForeignKey(User, on_delete=models.CASCADE, db_index=True)
    subject = models.CharField(max_length=200, blank=True, null=True)
    body = models.TextField()
    is_read = models.BooleanField(default=False, db_index=True)
    message_type = models.CharField(max_length=16, choices=TYPE_CHOICES, default="system")
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        indexes = [
            models.Index(fields=['user', '-created_at']),
            models.Index(fields=['user', 'is_read']),
        ]
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.subject} ({self.user})"

    def save(self, *args, **kwargs):
        try:
            is_new = not self.pk
            logger.debug(f"Saving message: user={self.user.username}, type={self.message_type}, new={is_new}")
            
            super().save(*args, **kwargs)
            
            logger.info(f"Message saved: ID={self.pk}, user={self.user.username}")
            
        except Exception as e:
            logger.error(f"Error saving message for user {self.user.username}: {str(e)}")
            raise

    def mark_as_read(self):
        """Пометить сообщение как прочитанное"""
        try:
            if not self.is_read:
                self.is_read = True
                self.save(update_fields=["is_read"])
                logger.info(f"Message marked as read: ID={self.pk}, user={self.user.username}")
                return True
            return False
        except Exception as e:
            logger.error(f"Error marking message as read {self.pk}: {str(e)}")
            return False