from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.authtoken.models import Token
from django.contrib.auth import authenticate
from .serializers import LoginSerializer, UserPublicSerializer
from rest_framework.permissions import AllowAny, IsAuthenticated

class LoginView(APIView):
    permission_classes = [AllowAny]
    throttle_classes = []  # Уже глобально в settings; здесь override если нужно

    def post(self, request):
        serializer = LoginSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)  # {"username": ["This field is required."]}

        username = serializer.validated_data['username']
        password = serializer.validated_data['password']

        user = authenticate(request, username=username, password=password)  # Django backend: хэш-чек + custom manager
        if user is None:
            return Response({"detail": "Invalid username or password."}, status=status.HTTP_401_UNAUTHORIZED)  # Не уточняем "какой" — anti-brute-force

        if not user.is_active:
            return Response({"detail": "Account is inactive."}, status=status.HTTP_403_FORBIDDEN)  # Для банов (blacklist в друзьях/чате)

        # Успех: Token (get or create — для повторных логинов)
        token, created = Token.objects.get_or_create(user=user)
        # Опционально: Лог для Prometheus (auth_success_total.inc() — добавим в middleware позже)

        user_serializer = UserPublicSerializer(user)
        return Response({
            'token': token.key,  # В headers для следующих запросов (e.g., /api/roulette/spin/ за 6-12 souls/keys/diamonds)
            'user': user_serializer.data,  # Публичка: gold etc. для HUD/квестов ("открыть сундук 30 раз" за 150 diamonds)
        }, status=status.HTTP_200_OK)
    

class LogoutView(APIView):
    permission_classes = [IsAuthenticated]  # Требует токен в headers (для security: только авторизованный юзер выходит)

    def delete(self, request):  # DELETE метод (стандарт для logout в REST; POST тоже ок, но DELETE чище)
        # Удаляем все токены юзера (на случай нескольких устройств — для сессий чата ЛС/кланового, не плодить в authtoken_token)
        Token.objects.filter(user=request.user).delete()
        # Опционально: Celery.delay(on_logout_task, request.user.id) — e.g., сброс last_login для оффлайн-фарма (+gold/keys по времени, с бонусом расы Нежить +150 HP для Lifestealer; оповещение по почте "Сессия завершена, фарм активирован!")
        # Лог для Prometheus: auth_logout_total.inc() — метрика success для Grafana (rate на 10k+ выходов/час)

        return Response({"detail": "Successfully logged out."}, status=status.HTTP_200_OK)  # Простой JSON (без user data — сессия чиста)