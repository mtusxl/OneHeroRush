from rest_framework import generics, permissions, status
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.throttling import UserRateThrottle

from django.shortcuts import get_object_or_404
from django.db import transaction, DatabaseError
from django.core.cache import cache
from django.db.models import Prefetch
import random
import logging

from .models import Pet, UserPet, UserSummonConfig, RarityChoices
from .serializers import UserPetSerializer, PetSerializer, UserSummonConfigSerializer, SummonPetRequestSerializer
from Characters.models import Character
from Leaderboard.signals import update_hero_leaderboard

logger = logging.getLogger(__name__)

class SummonThrottle(UserRateThrottle):
    rate = '5/minute'

class UserPetListView(generics.ListAPIView):
    serializer_class = UserPetSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        try:
            return UserPet.objects.filter(user=self.request.user).select_related('pet')
        except Exception as e:
            logger.error(f"Error fetching user pets for user {self.request.user.id}: {str(e)}")
            return UserPet.objects.none()

class SelectPetView(APIView):
    """Выбрать активного питомца для аккаунта"""
    
    def post(self, request, pet_id):
        try:
            with transaction.atomic():
                user_pet = get_object_or_404(UserPet, id=pet_id, user=request.user)
                
                # Снимаем выделение со всех питомцев пользователя
                updated_count = UserPet.objects.filter(
                    user=request.user, 
                    is_selected=True
                ).update(is_selected=False)
                
                if updated_count > 0:
                    logger.info(f"Deselected {updated_count} pets for user {request.user.id}")
                
                # Выбираем нового питомца
                user_pet.is_selected = True
                user_pet.save()
                
                logger.info(f"User {request.user.id} selected pet {pet_id} ({user_pet.pet.name})")
                
                # Обновляем рейтинги героев пользователя
                try:
                    characters = Character.objects.filter(user=request.user)
                    for character in characters:
                        update_hero_leaderboard(Character, character)
                    logger.info(f"Updated leaderboard for {characters.count()} characters of user {request.user.id}")
                except Exception as e:
                    logger.error(f"Error updating leaderboard for user {request.user.id}: {str(e)}")
                
                return Response({"status": "ok", "selected_pet": user_pet.pet.name})
                
        except DatabaseError as e:
            logger.error(f"Database error selecting pet {pet_id} for user {request.user.id}: {str(e)}")
            return Response(
                {"error": "Database error occurred"}, 
                status=status.HTTP_503_SERVICE_UNAVAILABLE
            )
        except Exception as e:
            logger.error(f"Unexpected error selecting pet {pet_id} for user {request.user.id}: {str(e)}")
            return Response(
                {"error": "Internal server error"}, 
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

class SummonPetView(APIView):
    permission_classes = [permissions.IsAuthenticated]
    throttle_classes = [SummonThrottle]

    @transaction.atomic
    def post(self, request):
        try:
            serializer = SummonPetRequestSerializer(data=request.data, context={'request': request})
            serializer.is_valid(raise_exception=True)
            data = serializer.validated_data
            user = request.user
            coupons = data['coupons']
            diamonds = data['diamonds']
            summons = data['summons']
            
            logger.info(f"Summon attempt by user {user.id}: coupons={coupons}, diamonds={diamonds}, summons={summons}")

            summon_config, _ = UserSummonConfig.objects.get_or_create(user=user)

            # Трата валюты с проверкой
            if coupons > 0 and user.soul_coupons < coupons:
                logger.warning(f"User {user.id} attempted summon with insufficient coupons: {user.soul_coupons} < {coupons}")
                return Response(
                    {"error": "Недостаточно купонов"}, 
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            if diamonds > 0 and user.diamonds < diamonds:
                logger.warning(f"User {user.id} attempted summon with insufficient diamonds: {user.diamonds} < {diamonds}")
                return Response(
                    {"error": "Недостаточно алмазов"}, 
                    status=status.HTTP_400_BAD_REQUEST
                )

            # Выполняем списание
            if coupons > 0:
                user.soul_coupons -= coupons
            if diamonds > 0:
                user.diamonds -= diamonds
            
            update_fields = []
            if coupons > 0:
                update_fields.append('soul_coupons')
            if diamonds > 0:
                update_fields.append('diamonds')
            
            user.save(update_fields=update_fields)
            logger.info(f"User {user.id} currency spent: coupons={coupons}, diamonds={diamonds}")

            # Кэширование питомцев с группировкой по редкости
            cache_key = 'all_pets_by_rarity'
            pets_by_rarity = cache.get(cache_key)
            
            if not pets_by_rarity:
                logger.debug("Pets cache miss, building cache")
                pets_by_rarity = {}
                all_pets = Pet.objects.all()
                for pet in all_pets:
                    if pet.rarity not in pets_by_rarity:
                        pets_by_rarity[pet.rarity] = []
                    pets_by_rarity[pet.rarity].append(pet)
                cache.set(cache_key, pets_by_rarity, timeout=3600)
                logger.debug(f"Cached {len(all_pets)} pets by rarity")

            # Получаем ID уже имеющихся питомцев пользователя
            owned_pet_ids = set(UserPet.objects.filter(user=user).values_list('pet_id', flat=True))
            logger.debug(f"User {user.id} has {len(owned_pet_ids)} unique pets")

            # Создаем список доступных питомцев по редкости
            available_by_rarity = {}
            for rarity, pets in pets_by_rarity.items():
                available_pets = [p for p in pets if p.id not in owned_pet_ids]
                if available_pets:
                    available_by_rarity[rarity] = available_pets

            if not available_by_rarity:
                logger.info(f"User {user.id} attempted summon but has all pets")
                return Response(
                    {"error": "У вас уже есть все питомцы"}, 
                    status=status.HTTP_400_BAD_REQUEST
                )

            # Настройка шансов с учетом уровня призыва
            level_bonus = summon_config.summon_level * 0.5
            chances = {
                RarityChoices.COMMON: max(45 - level_bonus, 20),
                RarityChoices.SUPERIOR: 30,
                RarityChoices.EXCELLENT: 15,
                RarityChoices.RARE: 5 + (level_bonus * 0.4),
                RarityChoices.UNIQUE: 3 + (level_bonus * 0.3),
                RarityChoices.EPIC: 1 + (level_bonus * 0.15),
                RarityChoices.LEGENDARY: 0.7 + (level_bonus * 0.1),
                RarityChoices.IMMORTAL: 0.3 + (level_bonus * 0.05),
            }

            # Фильтруем редкости, для которых есть доступные питомцы
            available_rarities = [r for r in chances.keys() if r in available_by_rarity]
            available_weights = [chances[r] for r in available_rarities]
            
            if not available_rarities:
                logger.warning(f"No available rarities for user {user.id}")
                return Response(
                    {"error": "Нет доступных питомцев для призыва"}, 
                    status=status.HTTP_400_BAD_REQUEST
                )

            summoned_pets = []
            for i in range(summons):
                chosen_rarity = random.choices(available_rarities, weights=available_weights)[0]
                available_pets = available_by_rarity[chosen_rarity]
                pet = random.choice(available_pets)
                
                # Создаем запись UserPet
                UserPet.objects.create(user=user, pet=pet)
                summoned_pets.append(pet)
                
                # Добавляем опыт за призыв
                summon_config.add_exp(1)
                
                logger.debug(f"Summon #{i+1} for user {user.id}: {pet.name} ({chosen_rarity})")

            logger.info(f"User {user.id} successfully summoned {len(summoned_pets)} pets")
            
            return Response({
                "status": "ok",
                "summoned_pets": PetSerializer(summoned_pets, many=True).data
            }, status=status.HTTP_201_CREATED)

        except DatabaseError as e:
            logger.error(f"Database error during summon for user {request.user.id}: {str(e)}")
            return Response(
                {"error": "Database error occurred during summon"}, 
                status=status.HTTP_503_SERVICE_UNAVAILABLE
            )
        except Exception as e:
            logger.error(f"Unexpected error during summon for user {request.user.id}: {str(e)}")
            return Response(
                {"error": "Internal server error during summon"}, 
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

class UserSummonConfigView(generics.RetrieveAPIView):
    serializer_class = UserSummonConfigSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_object(self):
        try:
            obj, created = UserSummonConfig.objects.get_or_create(user=self.request.user)
            if created:
                logger.info(f"Created new summon config for user {self.request.user.id}")
            return obj
        except Exception as e:
            logger.error(f"Error getting summon config for user {self.request.user.id}: {str(e)}")
            raise