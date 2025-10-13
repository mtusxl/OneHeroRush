from rest_framework import viewsets, status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.decorators import action
from django.db import transaction, DatabaseError
from django.shortcuts import get_object_or_404
import logging
from .models import Progress
from .serializers import ProgressSerializer, UpdateProgressSerializer
from common.tasks import recalculate_mmr
from .tasks import calculate_offline_farm

logger = logging.getLogger(__name__)

class ProgressViewSet(viewsets.ModelViewSet):
    '''
    ViewSet для прогресса: GET текущий, POST update после волны (с level_up, наградами).
    '''
    serializer_class = ProgressSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        try:
            return Progress.objects.filter(user=self.request.user).select_related('user')
        except Exception as e:
            logger.error(f"Error getting progress queryset for user {self.request.user.id}: {str(e)}")
            return Progress.objects.none()

    def get_object(self):
        try:
            obj = get_object_or_404(Progress, user=self.request.user)
            return obj
        except Exception as e:
            logger.error(f"Error getting progress object for user {self.request.user.id}: {str(e)}")
            raise

    def perform_create(self, serializer):
        try:
            # Auto-create if none (OneToOne)
            serializer.save(user=self.request.user)
            logger.info(f"Created new progress for user {self.request.user.id}")
        except Exception as e:
            logger.error(f"Error creating progress for user {self.request.user.id}: {str(e)}")
            raise

    def update(self, request, *args, **kwargs):
        try:
            progress = self.get_object()
            serializer = UpdateProgressSerializer(data=request.data)
            
            if not serializer.is_valid():
                logger.warning(f"Invalid update data from user {request.user.id}: {serializer.errors}")
                return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
            
            logger.info(f"Wave update requested by user {request.user.id}")
            
            try:
                with transaction.atomic():
                    progress.update_wave()
                    # Награды и level_up уже обрабатываются в update_wave()
                
                # Async MMR recalculation
                recalculate_mmr.delay(request.user.id)
                logger.debug(f"MMR recalc queued for user {request.user.id}")
                
                # Возвращаем обновленные данные
                response_data = ProgressSerializer(progress).data
                return Response(response_data)
                
            except DatabaseError as e:
                logger.error(f"Database error during wave update for user {request.user.id}: {str(e)}")
                return Response(
                    {"error": "Database error occurred"}, 
                    status=status.HTTP_503_SERVICE_UNAVAILABLE
                )
                
        except Exception as e:
            logger.error(f"Unexpected error during wave update for user {request.user.id}: {str(e)}")
            return Response(
                {"error": "Internal server error"}, 
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    def retrieve(self, request, *args, **kwargs):
        try:
            # При GET — calc offline farm async
            logger.debug(f"Progress retrieve for user {request.user.id}, triggering offline farm calc")
            calculate_offline_farm.delay(request.user.id)
            
            response = super().retrieve(request, *args, **kwargs)
            return response
            
        except Exception as e:
            logger.error(f"Error retrieving progress for user {request.user.id}: {str(e)}")
            return Response(
                {"error": "Error retrieving progress"}, 
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


    @action(detail=False, methods=['get'])
    def current_location_info(self, request):
        """
        Дополнительный экшен для получения информации о текущей локации
        """
        try:
            progress = self.get_object()
            location_info = {
                'location': progress.get_location_display(),
                'act': progress.act,
                'stage': progress.stage,
                'wave': progress.wave,
                'difficulty': progress.get_difficulty_display(),
                'waves_completed': progress.waves_completed
            }
            logger.debug(f"Location info retrieved for user {request.user.id}")
            return Response(location_info)
        except Exception as e:
            logger.error(f"Error getting location info for user {request.user.id}: {str(e)}")
            return Response(
                {"error": "Error retrieving location info"}, 
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )