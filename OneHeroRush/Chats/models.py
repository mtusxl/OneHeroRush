# models.py
import logging
from django.conf import settings
from django.db import models

logger = logging.getLogger(__name__)
User = settings.AUTH_USER_MODEL

class ChatMessage(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    room = models.CharField(max_length=100)   
    content = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"[{self.room}] {self.user}: {self.content[:30]}"

    def save(self, *args, **kwargs):
        try:
            is_new = not self.pk
            logger.debug(f"Saving ChatMessage: user={self.user.username}, room={self.room}, new={is_new}")
            
            super().save(*args, **kwargs)
            
            logger.info(f"ChatMessage saved successfully: ID={self.pk}, user={self.user.username}, room={self.room}")
            
        except Exception as e:
            logger.error(f"Error saving ChatMessage: user={self.user.username}, room={self.room}, error={str(e)}")
            raise

    def delete(self, *args, **kwargs):
        try:
            logger.debug(f"Deleting ChatMessage: ID={self.pk}, user={self.user.username}, room={self.room}")
            
            super().delete(*args, **kwargs)
            
            logger.info(f"ChatMessage deleted: ID={self.pk}")
            
        except Exception as e:
            logger.error(f"Error deleting ChatMessage ID={self.pk}: {str(e)}")
            raise