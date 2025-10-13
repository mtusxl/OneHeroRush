from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.throttling import UserRateThrottle
from django.shortcuts import get_object_or_404
from django.db import transaction, DatabaseError
from django.core.cache import cache
import logging
import random
from .models import Soul, PlayerSoul, SummonLevel, SoulRarity
from .serializers import PlayerSoulSerializer, SummonRequestSerializer
from Users.models import UserProfile
from Characters.models import Character

logger = logging.getLogger(__name__)

class SummonThrottle(UserRateThrottle):
    rate = '10/minute'

class SummonSoulView(APIView):
    throttle_classes = [SummonThrottle]

    @transaction.atomic
    def post(self, request):
        try:
            serializer = SummonRequestSerializer(data=request.data)
            if not serializer.is_valid():
                logger.warning(f"Invalid summon request from user {request.user.id}: {serializer.errors}")
                return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

            data = serializer.validated_data
            coupons = data['coupons']
            diamonds = data['diamonds']
            character_id = data['character_id']

            logger.info(f"Summon attempt by user {request.user.id}: coupons={coupons}, diamonds={diamonds}, character_id={character_id}")

            profile = UserProfile.objects.select_for_update().get(user=request.user)
            character = get_object_or_404(Character, id=character_id)

            # Проверяем валюту
            if coupons > 0:
                if profile.soul_coupons < coupons:
                    logger.warning(f"User {request.user.id} has insufficient coupons: {profile.soul_coupons} < {coupons}")
                    return Response({'error': 'Insufficient coupons'}, status=status.HTTP_400_BAD_REQUEST)
                
                summons = 15 if coupons == 15 else 35  # Бонус за 30
                profile.soul_coupons -= coupons
                currency_type = 'coupons'
                
            else:  # diamonds
                effective_coupons = diamonds // 2
                if effective_coupons == 0:
                    logger.warning(f"User {request.user.id} provided insufficient diamonds: {diamonds}")
                    return Response({'error': 'Insufficient diamonds'}, status=status.HTTP_400_BAD_REQUEST)
                
                if profile.diamonds < diamonds:
                    logger.warning(f"User {request.user.id} has insufficient diamonds: {profile.diamonds} < {diamonds}")
                    return Response({'error': 'Insufficient diamonds'}, status=status.HTTP_400_BAD_REQUEST)
                
                summons = effective_coupons
                profile.diamonds -= diamonds
                currency_type = 'diamonds'

            
            profile.save(update_fields=[currency_type])
            logger.info(f"User {request.user.id} spent {coupons if coupons else diamonds} {currency_type} for {summons} summons")

            # Получаем или создаем уровень призыва
            summon_lvl, created = SummonLevel.objects.get_or_create(user=request.user)
            if created:
                logger.info(f"Created new summon level for user {request.user.id}")

            new_souls = []
            for i in range(summons):
                try:
                    # Бросок редкости
                    chances = summon_lvl.rarity_chances
                    rarities = list(chances.keys())
                    weights = list(chances.values())
                    rarity = random.choices(rarities, weights=weights)[0]

                    # Создаем или получаем шаблон души
                    soul, created = Soul.objects.get_or_create(
                        character=character,
                        rarity=rarity,
                        defaults={
                            'open_stats': self.generate_open_stats(rarity),
                            'hidden_stats': self.generate_hidden_stats(),
                            'unique_properties': self.generate_unique_props(rarity)
                        }
                    )

                    if created:
                        logger.debug(f"Created new soul template: character={character.id}, rarity={rarity}")

                    # Создаем душу для игрока
                    player_soul = PlayerSoul.objects.create(user=request.user, soul=soul)
                    new_souls.append(player_soul)

                    # Добавляем опыт
                    summon_lvl.add_experience(1)

                    logger.debug(f"Summon #{i+1} for user {request.user.id}: {rarity} soul")

                except Exception as e:
                    logger.error(f"Error in individual summon #{i+1} for user {request.user.id}: {str(e)}")
                    continue  # Продолжаем несмотря на ошибки в отдельных призывах

            logger.info(f"User {request.user.id} successfully summoned {len(new_souls)} souls")

            return Response({
                'souls': PlayerSoulSerializer(new_souls, many=True).data,
                'summons_count': len(new_souls)
            }, status=status.HTTP_201_CREATED)

        except UserProfile.DoesNotExist:
            logger.error(f"UserProfile not found for user {request.user.id}")
            return Response({'error': 'User profile not found'}, status=status.HTTP_404_NOT_FOUND)
        except Character.DoesNotExist:
            logger.error(f"Character {data.get('character_id')} not found for user {request.user.id}")
            return Response({'error': 'Character not found'}, status=status.HTTP_404_NOT_FOUND)
        except DatabaseError as e:
            logger.error(f"Database error during summon for user {request.user.id}: {str(e)}")
            return Response({'error': 'Database error occurred'}, status=status.HTTP_503_SERVICE_UNAVAILABLE)
        except Exception as e:
            logger.error(f"Unexpected error during summon for user {request.user.id}: {str(e)}")
            return Response({'error': 'Internal server error'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    def generate_open_stats(self, rarity):
        """Генерация открытых статов души"""
        base_stats = {
            'damage': random.randint(5, 20) * self._get_rarity_multiplier(rarity),
            'hp_regen': random.randint(1, 5) * self._get_rarity_multiplier(rarity)
        }
        return base_stats

    def generate_hidden_stats(self):
        """Генерация скрытых статов"""
        return {'balance_tweak': random.randint(-5, 5)}

    def generate_unique_props(self, rarity):
        """Генерация уникальных свойств для редких душ"""
        if rarity == 'IMMORTAL':
            return ['+15% spell dmg vs Shadow Demon\'s Shadow']
        elif rarity == 'LEGENDARY':
            return ['+10% spell dmg vs Shadow Demon\'s Shadow']
        return []

    def _get_rarity_multiplier(self, rarity):
        """Множитель для статов в зависимости от редкости"""
        multipliers = {
            'COMMON': 1.0, 'SUPERIOR': 1.2, 'EXCELLENT': 1.5,
            'RARE': 2.0, 'UNIQUE': 2.5, 'EPIC': 2.8,
            'LEGENDARY': 3.0, 'IMMORTAL': 3.1
        }
        return multipliers.get(rarity, 1.0)