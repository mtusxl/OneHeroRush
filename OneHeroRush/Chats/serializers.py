from rest_framework import serializers
from .models import ChatMessage, Mail

class ChatMessageSerializer(serializers.ModelSerializer):
    class Meta:
        model = ChatMessage
        fields = ["user", "room", "content", "created_at"]



class MailSerializer(serializers.ModelSerializer):
    class Meta:
        model = Mail
        fields = ["id", "subject", "body", "is_read", "created_at"]

