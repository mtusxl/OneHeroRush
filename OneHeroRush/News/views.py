from rest_framework import generics, permissions, status
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.exceptions import ValidationError
from .models import MailTemplate, MailTask
from .serializers import MailTemplateSerializer, MailTaskSerializer
from .tasks import run_mail_task

class MailTemplateListView(generics.ListCreateAPIView):
    queryset = MailTemplate.objects.all().order_by("-created_at")
    serializer_class = MailTemplateSerializer
    permission_classes = [permissions.IsAdminUser]


class MailTaskListView(generics.ListAPIView):
    queryset = MailTask.objects.all().order_by("-created_at")
    serializer_class = MailTaskSerializer
    permission_classes = [permissions.IsAdminUser]


class MailSendView(APIView):
    """Создание и запуск рассылки"""
    permission_classes = [permissions.IsAdminUser]

    def post(self, request):
        template_id = request.data.get("template_id")
        filters = request.data.get("filters", {})
        if not MailTemplate.objects.filter(id=template_id).exists():
            raise ValidationError({"detail": "Template not found"})

        task = MailTask.objects.create(
            template_id=template_id,
            created_by=request.user,
            filter_query=filters
        )

        run_mail_task.delay(task.id)
        return Response({"status": "started", "task_id": task.id}, status=status.HTTP_201_CREATED)
