from rest_framework import viewsets, status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from django.db import transaction
from .models import Progress
from .serializers import ProgressSerializer, UpdateProgressSerializer
from common.tasks import recalculate_mmr
from .tasks import calculate_offline_farm

class ProgressViewSet(viewsets.ModelViewSet):
    '''
    ViewSet для прогресса: GET текущий, POST update после волны (с level_up, наградами).
    '''
    serializer_class = ProgressSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return Progress.objects.filter(user=self.request.user)

    def perform_create(self, serializer):
        # Auto-create if none (OneToOne)
        serializer.save(user=self.request.user)

    def update(self, request, *args, **kwargs):
        progress = self.get_object()
        serializer = UpdateProgressSerializer(data=request.data)
        if serializer.is_valid():
            with transaction.atomic():
                progress.update_wave()
                # Награды, level_up
            recalculate_mmr.delay(request.user.id)
            return Response(ProgressSerializer(progress).data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def retrieve(self, request, *args, **kwargs):
        # При GET — calc offline farm async
        calculate_offline_farm.delay(request.user.id)
        return super().retrieve(request, *args, **kwargs)