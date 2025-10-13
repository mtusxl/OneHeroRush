from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.authtoken.models import Token
from django.contrib.auth import authenticate
from django.db import DatabaseError
from drf_yasg.utils import swagger_auto_schema
from drf_yasg import openapi
import logging
from .serializers import LoginSerializer, UserPublicSerializer
from rest_framework.permissions import AllowAny, IsAuthenticated

logger = logging.getLogger(__name__)

class LoginView(APIView):
    permission_classes = [AllowAny]

    @swagger_auto_schema(  
        request_body=LoginSerializer,
        responses={
            200: openapi.Response('Success', UserPublicSerializer),
            400: openapi.Response('Validation error'),
            401: openapi.Response('Invalid credentials'),
            403: openapi.Response('Inactive account'),
            500: openapi.Response('Internal server error'),
        },
        operation_description="Авторизация пользователя"
    )
    def post(self, request):
        try:
            serializer = LoginSerializer(data=request.data)
            if not serializer.is_valid():
                logger.warning(f"Invalid login data: {serializer.errors}")
                return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST) 

            username = serializer.validated_data['username']
            password = serializer.validated_data['password']

            logger.info(f"Login attempt for user: {username}")

            # Аутентификация пользователя
            user = authenticate(request, username=username, password=password)
            if user is None:
                logger.warning(f"Failed authentication for user: {username}")
                return Response(
                    {"detail": "Invalid username or password."}, 
                    status=status.HTTP_401_UNAUTHORIZED
                )

            if not user.is_active:
                logger.warning(f"Attempt to login to inactive account: {username}")
                return Response(
                    {"detail": "Account is inactive."}, 
                    status=status.HTTP_403_FORBIDDEN
                )

            # Создаем или получаем токен
            try:
                token, created = Token.objects.get_or_create(user=user)
                if created:
                    logger.debug(f"New token created for user: {username}")
                else:
                    logger.debug(f"Existing token used for user: {username}")
            except DatabaseError as e:
                logger.error(f"Database error creating token for user {username}: {str(e)}")
                return Response(
                    {"detail": "Authentication service temporarily unavailable."},
                    status=status.HTTP_503_SERVICE_UNAVAILABLE
                )

            # Сериализуем данные пользователя
            user_serializer = UserPublicSerializer(user)

            logger.info(f"Successful login for user: {username} (ID: {user.id})")
            
            return Response({
                'token': token.key,
                'user': user_serializer.data,
            }, status=status.HTTP_200_OK)

        except DatabaseError as e:
            logger.error(f"Database error during login for user {request.data.get('username')}: {str(e)}")
            return Response(
                {"detail": "Authentication service temporarily unavailable."},
                status=status.HTTP_503_SERVICE_UNAVAILABLE
            )
        except Exception as e:
            logger.error(f"Unexpected error during login: {str(e)}")
            return Response(
                {"detail": "Internal server error occurred."},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    

class LogoutView(APIView):
    permission_classes = [IsAuthenticated]

    def delete(self, request):
        try:
            user = request.user
            tokens_count = Token.objects.filter(user=user).count()
            
            # Удаляем все токены пользователя
            deleted_count, _ = Token.objects.filter(user=user).delete()
            
            logger.info(f"User {user.username} (ID: {user.id}) logged out. Deleted {deleted_count} tokens.")
            
            return Response(
                {"detail": "Successfully logged out.", "tokens_deleted": deleted_count}, 
                status=status.HTTP_200_OK
            )
            
        except DatabaseError as e:
            logger.error(f"Database error during logout for user {request.user.id}: {str(e)}")
            return Response(
                {"detail": "Logout service temporarily unavailable."},
                status=status.HTTP_503_SERVICE_UNAVAILABLE
            )
        except Exception as e:
            logger.error(f"Unexpected error during logout for user {request.user.id}: {str(e)}")
            return Response(
                {"detail": "Internal server error occurred during logout."},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class UserProfileView(APIView):
    """view для получения профиля пользователя"""
    permission_classes = [IsAuthenticated]

    def get(self, request):
        try:
            user_serializer = UserPublicSerializer(request.user)
            logger.debug(f"Profile data retrieved for user {request.user.id}")
            
            return Response({
                'user': user_serializer.data
            }, status=status.HTTP_200_OK)
            
        except Exception as e:
            logger.error(f"Error retrieving profile for user {request.user.id}: {str(e)}")
            return Response(
                {"detail": "Error retrieving profile data."},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )