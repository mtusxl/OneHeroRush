from django.conf import settings
from django.db import models

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




