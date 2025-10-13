import logging
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



logger = logging.getLogger(__name__)



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
        logger.debug(f"Getting serializer for action: {self.action}")
        if self.action == 'create':
            return CreateCharacterSerializer
        return super().get_serializer_class()

    def get_queryset(self):
        logger.debug(f"Getting character queryset for user: {self.request.user.id}")
        queryset = Character.objects.filter(user=self.request.user).prefetch_related('items').order_by('-level')
        logger.debug(f"Queryset contains {queryset.count()} characters")
        return queryset

    def perform_create(self, serializer):
        '''
        Кастомное создание героя: проверки лимита/доната, сохранение с user, уведомление, асинхронный MMR/клан.
        '''
        try:
            logger.info(f"Starting character creation for user: {self.request.user.id}")
            
            with transaction.atomic():
                user = self.request.user
                current_hero_count = user.characters.count()
                logger.debug(f"User {user.id} has {current_hero_count}/{user.max_heroes} heroes")
                
                if current_hero_count >= user.max_heroes:
                    logger.warning(f"User {user.id} reached hero limit: {current_hero_count}/{user.max_heroes}")
                    raise PermissionDenied("Лимит героев достигнут; увеличьте через донат")
                
                hero_name = serializer.validated_data['hero_name']
                logger.debug(f"Attempting to create hero: {hero_name}")
                
                donate_heroes = ['Pudge', 'Necrophos', 'Juggernaut', 'Phantom Assassin', 'Lifestealer', 'Rubick', 'Ursa', 'Axe', 'Shadow Fiend', 'Zeus']
                if hero_name in donate_heroes and hero_name not in user.purchased_heroes:
                    logger.warning(f"User {user.id} attempted to create paid hero {hero_name} without purchase")
                    raise PermissionDenied("Герой требует покупки через донат")
                
                instance = serializer.save(user=user, is_active=False)
                logger.info(f"Character created successfully: {instance.id} ({hero_name})")
                
                send_mail_notification.delay(user.id, f"Создан герой {hero_name} с бонусом {instance.race_bonus}")
                logger.debug("Creation notification sent")
            
            recalculate_mmr.delay(user.id)
            logger.debug("MMR recalculation task queued")
            
            # Безопасная проверка наличия клана
            try:
                # Проверяем наличие связи с кланом через ClanMember
                if hasattr(user, 'clan') and user.clan:
                    clan_id = user.clan.clan_id
                    update_clan_rank.delay(clan_id)
                    logger.debug(f"Clan rank update queued for clan: {clan_id}")
                else:
                    logger.debug("User has no clan, skipping clan rank update")
            except Exception as e:
                # Игнорируем ошибки связанные с отсутствием клана
                logger.debug(f"User {user.id} has no clan or error checking clan: {str(e)}")
                
        except Exception as e:
            logger.error(f"Error during character creation for user {self.request.user.id}: {str(e)}")
            raise

    @method_decorator(cache_page(60))
    def list(self, request, *args, **kwargs):
        logger.info(f"Character list requested by user: {request.user.id}")
        try:
            response = super().list(request, *args, **kwargs)
            logger.debug(f"Character list returned {len(response.data)} characters")
            return response
        except Exception as e:
            logger.error(f"Error retrieving character list for user {request.user.id}: {str(e)}")
            raise

    @method_decorator(cache_page(60))
    def retrieve(self, request, *args, **kwargs):
        character_id = kwargs.get('pk')
        logger.info(f"Character retrieve requested: {character_id} by user: {request.user.id}")
        try:
            response = super().retrieve(request, *args, **kwargs)
            logger.debug(f"Character {character_id} details retrieved successfully")
            return response
        except Exception as e:
            logger.error(f"Error retrieving character {character_id}: {str(e)}")
            raise

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def select_character(request):
    '''
    API для активации героя: деактивирует старый, активирует новый, асинхронно MMR/уведомление.
    '''
    logger.info(f"Character selection request from user: {request.user.id}")
    
    serializer = SelectCharacterSerializer(data=request.data)
    if not serializer.is_valid():
        logger.warning(f"Invalid character selection data from user {request.user.id}: {serializer.errors}")
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    try:
        with transaction.atomic():
            character_id = serializer.validated_data['character_id']
            logger.debug(f"User {request.user.id} selecting character: {character_id}")
            
            # Деактивируем текущего активного героя
            deactivated_count = Character.objects.filter(
                user=request.user, 
                is_active=True
            ).update(is_active=False)
            
            logger.debug(f"Deactivated {deactivated_count} previously active characters")
            
            # Активируем нового героя
            char = Character.objects.get(id=character_id, user=request.user)
            char.is_active = True
            char.save()
            
            logger.info(f"Character {character_id} activated for user {request.user.id}")
            
            recalculate_mmr.delay(request.user.id)
            logger.debug("MMR recalculation task queued after character selection")
            
            send_mail_notification.delay(request.user.id, f"Выбрали {char.hero_name} - бонус {char.race_bonus}")
            logger.debug("Selection notification sent")
        
        return Response({'message': 'Character selected'}, status=status.HTTP_200_OK)
        
    except Character.DoesNotExist:
        logger.error(f"Character {character_id} not found for user {request.user.id}")
        return Response(
            {'error': 'Character not found'}, 
            status=status.HTTP_404_NOT_FOUND
        )
    except Exception as e:
        logger.error(f"Error selecting character {character_id} for user {request.user.id}: {str(e)}")
        return Response(
            {'error': 'Internal server error'}, 
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )