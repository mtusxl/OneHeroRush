from rest_framework import serializers
from .models import Progress

class ProgressSerializer(serializers.ModelSerializer):
    '''
    Сериализатор прогресса: текущий статус, для GET/POST update.
    '''
    class Meta:
        model = Progress
        fields = ['location', 'act', 'stage', 'wave', 'waves_completed', 'difficulty', 'offline_gold', 'offline_keys']

class UpdateProgressSerializer(serializers.Serializer):
    '''
    Для POST update: подтверждение волны (или босса).
    '''
    wave_completed = serializers.BooleanField(default=True)  # Для простоты