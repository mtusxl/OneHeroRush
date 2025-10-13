from rest_framework import viewsets, status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.decorators import action
from django.db import transaction, DatabaseError
import logging
from .models import Quest
from .serializers import QuestSerializer, CompleteQuestSerializer
from common.tasks import send_mail_notification

logger = logging.getLogger(__name__)

class QuestViewSet(viewsets.ReadOnlyModelViewSet):
    '''
    ViewSet для квестов: GET список, POST complete для завершения (награды, update MMR async).
    '''
    serializer_class = QuestSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        try:
            # Оптимизация: prefetch связанных пользователей для проверки завершения
            return Quest.objects.prefetch_related('users_completed').all()
        except Exception as e:
            logger.error(f"Error getting quests queryset for user {self.request.user.id}: {str(e)}")
            return Quest.objects.none()
    
    def get_serializer_context(self):
        context = super().get_serializer_context()
        context['request'] = self.request
        return context

    def list(self, request, *args, **kwargs):
        try:
            logger.info(f"User {request.user.id} requested quests list")
            response = super().list(request, *args, **kwargs)
            logger.debug(f"Returned {len(response.data)} quests to user {request.user.id}")
            return response
        except Exception as e:
            logger.error(f"Error listing quests for user {request.user.id}: {str(e)}")
            return Response(
                {"error": "Error retrieving quests"}, 
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    @action(detail=True, methods=['post'])
    def complete(self, request, pk=None):
        try:
            quest = self.get_object()
            serializer = CompleteQuestSerializer(data=request.data)
            
            if not serializer.is_valid():
                logger.warning(f"Invalid complete data from user {request.user.id}: {serializer.errors}")
                return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
            
            if not serializer.validated_data['completed']:
                logger.warning(f"User {request.user.id} attempted to complete quest {pk} with completed=False")
                return Response(
                    {"error": "Completed must be true"}, 
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            logger.info(f"User {request.user.id} attempting to complete quest {pk}")
            
            # Пытаемся завершить квест
            success = quest.complete(request.user)
            
            if success:
                logger.info(f"Quest {pk} successfully completed by user {request.user.id}")
                return Response({'message': 'Квест завершён', 'rewards': {
                    'diamonds': quest.reward_diamonds,
                    'souls': quest.reward_souls,
                    'gold': quest.reward_gold,
                    'keys': quest.reward_keys
                }})
            else:
                logger.warning(f"Quest {pk} already completed by user {request.user.id}")
                return Response(
                    {"error": "Квест уже завершён"}, 
                    status=status.HTTP_400_BAD_REQUEST
                )
                
        except Quest.DoesNotExist:
            logger.error(f"Quest {pk} not found for user {request.user.id}")
            return Response(
                {"error": "Квест не найден"}, 
                status=status.HTTP_404_NOT_FOUND
            )
        except DatabaseError as e:
            logger.error(f"Database error completing quest {pk} for user {request.user.id}: {str(e)}")
            return Response(
                {"error": "Database error occurred"}, 
                status=status.HTTP_503_SERVICE_UNAVAILABLE
            )
        except Exception as e:
            logger.error(f"Unexpected error completing quest {pk} for user {request.user.id}: {str(e)}")
            return Response(
                {"error": "Internal server error"}, 
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

