import logging
from rest_framework import serializers
from .models import MailTemplate, MailTask

logger = logging.getLogger(__name__)

class MailTemplateSerializer(serializers.ModelSerializer):
    class Meta:
        model = MailTemplate
        fields = ["id", "name", "subject", "body", "mail_type", "created_at"]
        read_only_fields = ["id", "created_at"]

    def validate_name(self, value):
        try:
            value = value.strip()
            if len(value) < 3:
                logger.warning(f"Template name too short: {value}")
                raise serializers.ValidationError("Name must be at least 3 characters")
            return value
        except Exception as e:
            logger.error(f"Error validating template name {value}: {str(e)}")
            raise

    def validate_subject(self, value):
        try:
            if not value.strip():
                logger.warning("Empty template subject")
                raise serializers.ValidationError("Subject cannot be empty")
            return value
        except Exception as e:
            logger.error(f"Error validating template subject: {str(e)}")
            raise


class MailTaskSerializer(serializers.ModelSerializer):
    template_name = serializers.CharField(source="template.name", read_only=True)
    created_by_username = serializers.CharField(source="created_by.username", read_only=True)

    class Meta:
        model = MailTask
        fields = ["id", "template", "template_name", "status", "target_count", 
                 "created_by", "created_by_username", "created_at", "completed_at", "error_message"]
        read_only_fields = ["id", "created_at", "completed_at", "error_message", "target_count"]