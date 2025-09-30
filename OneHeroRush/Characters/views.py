from rest_framework import viewsets, status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.throttling import UserRateThrottle
from rest_framework.decorators import api_view, permission_classes
from rest_framework.mixins import CreateModelMixin
from django.utils.decorators import method_decorator
from django.views.decorators.cache import cache_page
from django.db import transaction
from django.core.exceptions import PermissionDenied
from .models import Character
from .serializers import CharacterSerializer, CreateCharacterSerializer, SelectCharacterSerializer
from common.tasks import recalculate_mmr , update_clan_rank , send_mail_notification

class CharacterThrottle(UserRateThrottle):
    rate = '10/min'

class CharacterViewSet(CreateModelMixin, viewsets.ReadOnlyModelViewSet):
    '''
    ViewSet для героев: список/детали (с кэшем), создание с проверками (лимит/донат). Авто-расчёт MMR асинхронно.
    '''
    serializer_class = CharacterSerializer
    permission_classes = [IsAuthenticated]
    throttle_classes = [CharacterThrottle]

    def get_serializer_class(self):
        if self.action == 'create':
            return CreateCharacterSerializer
        return super().get_serializer_class()

    def get_queryset(self):
        return Character.objects.filter(user=self.request.user).prefetch_related('items').order_by('-level')

    def perform_create(self, serializer):
        '''
        Кастомное создание героя: проверки лимита/доната, сохранение с user, уведомление, асинхронный MMR/клан.
        '''
        with transaction.atomic():
            user = self.request.user
            if user.characters.count() >= user.max_heroes:
                raise PermissionDenied("Лимит героев достигнут; увеличьте через донат")
            hero_name = serializer.validated_data['hero_name']
            donate_heroes = ['Pudge', 'Necrophos', 'Juggernaut', 'Phantom Assassin', 'Lifestealer', 'Rubick', 'Ursa', 'Axe', 'Shadow Fiend', 'Zeus']
            if hero_name in donate_heroes and hero_name not in user.purchased_heroes:
                raise PermissionDenied("Герой требует покупки через донат")
            instance = serializer.save(user=user, is_active=False)
            send_mail_notification.delay(user.id, f"Создан герой {hero_name} с бонусом {instance.race_bonus}")
        recalculate_mmr.delay(user.id)
        if user.clan:
            update_clan_rank.delay(user.clan.id)

    @method_decorator(cache_page(60))
    def list(self, request, *args, **kwargs):
        return super().list(request, *args, **kwargs)

    @method_decorator(cache_page(60))
    def retrieve(self, request, *args, **kwargs):
        return super().retrieve(request, *args, **kwargs)

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def select_character(request):
    '''
    API для активации героя: деактивирует старый, активирует новый, асинхронно MMR/уведомление.
    '''
    serializer = SelectCharacterSerializer(data=request.data)
    if serializer.is_valid():
        with transaction.atomic():
            Character.objects.filter(user=request.user, is_active=True).update(is_active=False)
            char = Character.objects.get(id=serializer.validated_data['character_id'], user=request.user)
            char.is_active = True
            char.save()
            recalculate_mmr.delay(request.user.id)
            send_mail_notification.delay(request.user.id, f"Выбрали {char.hero_name} - бонус {char.race_bonus}")
        return Response({'message': 'Character selected'}, status=status.HTTP_200_OK)
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)