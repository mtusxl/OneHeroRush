from rest_framework import serializers
from .models import MailTemplate, MailTask

class MailTemplateSerializer(serializers.ModelSerializer):
    class Meta:
        model = MailTemplate
        fields = ["id", "name", "subject", "body", "mail_type", "created_at"]


class MailTaskSerializer(serializers.ModelSerializer):
    template = MailTemplateSerializer()
    read_only_fields = ("created_at", "completed_at")

    class Meta:
        model = MailTask
        fields = ["id", "template", "status", "target_count", "created_at", "completed_at"]
