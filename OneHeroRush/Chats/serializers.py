import logging
from rest_framework import serializers
from .models import ChatMessage

logger = logging.getLogger(__name__)

class ChatMessageSerializer(serializers.ModelSerializer):
    class Meta:
        model = ChatMessage
        fields = ["user", "room", "content", "created_at"]

    def validate_content(self, value):
        try:
            content = value.strip()
            if not content:
                logger.warning("Empty message content validation failed")
                raise serializers.ValidationError("Message cannot be empty")
            
            if len(content) > 1000:
                logger.warning("too big message content validation failed")
                raise serializers.ValidationError("Message too big")
        except Exception as e:
            raise f"Error Chat serializer - {e}"





