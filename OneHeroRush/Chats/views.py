# views.py
import logging
from django.core.exceptions import ObjectDoesNotExist
from rest_framework import generics
from rest_framework.response import Response
from rest_framework import status
from .models import ChatMessage
from .serializers import ChatMessageSerializer

logger = logging.getLogger(__name__)

class ChatHistoryView(generics.ListAPIView):
    serializer_class = ChatMessageSerializer

    def get_queryset(self):
        try:
            room = self.kwargs["room"]
            user = self.request.user
            
            logger.info(f"Chat history request: user={user.username}, room={room}")
            
            queryset = ChatMessage.objects.filter(room=room).order_by("-created_at")[:50]
            
            logger.debug(f"Retrieved {queryset.count()} messages for room {room}")
            return queryset
            
        except KeyError as e:
            logger.error(f"Missing room parameter in request: {str(e)}")
            return ChatMessage.objects.none()
        except Exception as e:
            logger.error(f"Error retrieving chat history for room {self.kwargs.get('room')}: {str(e)}")
            return ChatMessage.objects.none()

    def list(self, request, *args, **kwargs):
        try:
            response = super().list(request, *args, **kwargs)
            logger.info(f"Chat history response sent: room={self.kwargs['room']}, items={len(response.data)}")
            return response
            
        except Exception as e:
            logger.error(f"Error in chat history list view: {str(e)}")
            return Response(
                {"error": "Failed to retrieve chat history"}, 
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )