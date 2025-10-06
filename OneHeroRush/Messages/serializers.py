from rest_framework import serializers
from .models import Messages

class MessagesSerializer(serializers.ModelSerializer):
    class Meta:
        model = Messages
        fields = ["id", "subject", "body", "is_read", "mail_type", "created_at"]