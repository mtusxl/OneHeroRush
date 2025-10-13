import logging
from rest_framework import serializers
from .models import Messages

logger = logging.getLogger(__name__)

class MessagesSerializer(serializers.ModelSerializer):
    class Meta:
        model = Messages
        fields = ["id", "subject", "body", "is_read", "message_type", "created_at"]
        read_only_fields = ["id", "created_at"]

    def validate_subject(self, value):
        """Валидация темы сообщения"""
        try:
            if value and len(value) > 200:
                logger.warning(f"Message subject too long: {len(value)} chars")
                raise serializers.ValidationError("Subject must be at most 200 characters")
            return value
        except Exception as e:
            logger.error(f"Error validating message subject: {str(e)}")
            raise

    def validate_body(self, value):
        """Валидация тела сообщения"""
        try:
            if not value.strip():
                logger.warning("Empty message body")
                raise serializers.ValidationError("Message body cannot be empty")
            return value
        except Exception as e:
            logger.error(f"Error validating message body: {str(e)}")
            raise