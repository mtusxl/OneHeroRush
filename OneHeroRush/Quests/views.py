from rest_framework import viewsets, status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.decorators import action
from django.db import transaction
from .models import Quest
from .serializers import QuestSerializer, CompleteQuestSerializer
from common.tasks import send_mail_notification

class QuestViewSet(viewsets.ReadOnlyModelViewSet):
    '''
    ViewSet для квестов: GET список, POST complete для завершения (награды, update MMR async).
    '''
    serializer_class = QuestSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return Quest.objects.all()
    
    def get_serializer_context(self):
        context = super().get_serializer_context()
        context['request'] = self.request
        return context

    @action(detail=True, methods=['post'])
    def complete(self, request, pk=None):
        quest = self.get_object()
        serializer = CompleteQuestSerializer(data=request.data)
        if serializer.is_valid():
            if serializer.validated_data['completed']:
                quest.complete(request.user)
                send_mail_notification(pk, 'Квест завершён')
            return Response({'message': 'Квест завершён'})
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)