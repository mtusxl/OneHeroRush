from .models import ChatMessage, Mail
from .serializers import ChatMessageSerializer, MailSerializer
from rest_framework import generics, permissions, status
from rest_framework.response import Response
from django.shortcuts import get_object_or_404


class ChatHistoryView(generics.ListAPIView):
    serializer_class = ChatMessageSerializer

    def get_queryset(self):
        room = self.kwargs["room"]
        return ChatMessage.objects.filter(room=room).order_by("-created_at")[:50]
    



# Список писем игрока
class MailListView(generics.ListAPIView):
    serializer_class = MailSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return Mail.objects.filter(user=self.request.user).order_by("-created_at")


# Отметить письмо как прочитанное
class MailReadView(generics.UpdateAPIView):
    serializer_class = MailSerializer
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, id):
        mail = get_object_or_404(Mail, id=id, user=request.user)
        if not mail.is_read:
            mail.is_read = True
            mail.save(update_fields=["is_read"])
        return Response({"status": "ok"}, status=status.HTTP_200_OK)

