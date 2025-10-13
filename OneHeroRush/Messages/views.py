import logging
from rest_framework import generics, permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView
from django.shortcuts import get_object_or_404

from .models import Messages
from .serializers import MessagesSerializer

logger = logging.getLogger(__name__)

class MailListView(generics.ListAPIView):
    """Список сообщений пользователя"""
    serializer_class = MessagesSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        try:
            user = self.request.user
            logger.info(f"Mail list request from user: {user.username}")
            
            queryset = Messages.objects.filter(user=user).select_related('user')
            
            total_count = queryset.count()
            unread_count = queryset.filter(is_read=False).count()
            logger.debug(f"User {user.username} has {total_count} messages, {unread_count} unread")
            
            return queryset
            
        except Exception as e:
            logger.error(f"Error getting mail list for user {self.request.user.username}: {str(e)}")
            return Messages.objects.none()


class MailReadView(APIView):
    """Отметить сообщение как прочитанное"""
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, id):
        try:
            user = request.user
            logger.info(f"Mark message as read request: user={user.username}, message_id={id}")
            
            mail = get_object_or_404(Messages, id=id, user=user)
            
            if not mail.is_read:
                mail.is_read = True
                mail.save(update_fields=["is_read"])
                logger.info(f"Message {id} marked as read by {user.username}")
                return Response(
                    {"status": "marked_as_read", "message_id": id}, 
                    status=status.HTTP_200_OK
                )
            else:
                logger.debug(f"Message {id} was already read by {user.username}")
                return Response(
                    {"status": "already_read", "message_id": id}, 
                    status=status.HTTP_200_OK
                )
                
        except Exception as e:
            logger.error(f"Error marking message as read: user={request.user.username}, message_id={id}, error={str(e)}")
            return Response(
                {"error": "Failed to mark message as read"}, 
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )