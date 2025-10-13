# views.py
import logging
from rest_framework import generics, permissions, status
from rest_framework.views import APIView
from rest_framework.response import Response
from django.shortcuts import get_object_or_404

from .models import MailTemplate, MailTask
from .serializers import MailTemplateSerializer, MailTaskSerializer
from .tasks import run_mail_task

logger = logging.getLogger(__name__)

class MailTemplateListView(generics.ListCreateAPIView):
    """Список и создание шаблонов рассылок"""
    serializer_class = MailTemplateSerializer
    permission_classes = [permissions.IsAdminUser]

    def get_queryset(self):
        try:
            logger.info("Mail templates list request")
            queryset = MailTemplate.objects.all().order_by("-created_at")
            logger.debug(f"Returning {queryset.count()} templates")
            return queryset
        except Exception as e:
            logger.error(f"Error getting mail templates: {str(e)}")
            return MailTemplate.objects.none()

    def perform_create(self, serializer):
        try:
            template = serializer.save()
            logger.info(f"Mail template created: ID={template.pk}, name={template.name}")
        except Exception as e:
            logger.error(f"Error creating mail template: {str(e)}")
            raise


class MailTaskListView(generics.ListAPIView):
    """Список задач рассылок"""
    serializer_class = MailTaskSerializer
    permission_classes = [permissions.IsAdminUser]

    def get_queryset(self):
        try:
            logger.info("Mail tasks list request")
            queryset = MailTask.objects.all().select_related('template', 'created_by').order_by("-created_at")
            logger.debug(f"Returning {queryset.count()} tasks")
            return queryset
        except Exception as e:
            logger.error(f"Error getting mail tasks: {str(e)}")
            return MailTask.objects.none()


class MailSendView(APIView):
    """Создание и запуск рассылки"""
    permission_classes = [permissions.IsAdminUser]

    def post(self, request):
        try:
            user = request.user
            template_id = request.data.get("template_id")
            filters = request.data.get("filters", {})
            
            logger.info(f"Mail send request: user={user.username}, template_id={template_id}, filters={filters}")

            if not template_id:
                logger.warning("Missing template_id in mail send request")
                return Response(
                    {"error": "template_id is required"}, 
                    status=status.HTTP_400_BAD_REQUEST
                )

            # Проверяем существование шаблона
            template = get_object_or_404(MailTemplate, id=template_id)
            logger.debug(f"Template found: {template.name}")


            task = MailTask.objects.create(
                template=template,
                created_by=user,
                filter_query=filters
            )
            
            logger.info(f"Mail task created: ID={task.pk}")

            # Запускаем асинхронно
            run_mail_task.delay(task.id)
            logger.debug(f"Celery task started for mail task {task.pk}")

            return Response(
                {
                    "status": "started", 
                    "task_id": task.id,
                    "template": template.name
                }, 
                status=status.HTTP_201_CREATED
            )

        except Exception as e:
            logger.error(f"Error creating mail task: user={request.user.username}, error={str(e)}")
            return Response(
                {"error": "Failed to create mail task"}, 
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
