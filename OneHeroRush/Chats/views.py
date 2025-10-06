from .models import ChatMessage
from Messages.models import Messages
from .serializers import ChatMessageSerializer
from rest_framework import generics


class ChatHistoryView(generics.ListAPIView):
    serializer_class = ChatMessageSerializer

    def get_queryset(self):
        room = self.kwargs["room"]
        return ChatMessage.objects.filter(room=room).order_by("-created_at")[:50]
    





