from rest_framework import generics, permissions, status
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.throttling import UserRateThrottle

from django.shortcuts import get_object_or_404
from django.db import transaction
from django.core.cache import cache
from .models import Pet, UserPet, UserSummonConfig, RarityChoices
from .serializers import UserPetSerializer, PetSerializer, UserSummonConfigSerializer, SummonPetRequestSerializer
import random

from Characters.models import Character
from Leaderboard.signals import update_hero_leaderboard

class SummonThrottle(UserRateThrottle):
    rate = '5/minute'

class UserPetListView(generics.ListAPIView):
    serializer_class = UserPetSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return UserPet.objects.filter(user=self.request.user).select_related('pet')

class SelectPetView(APIView):
    """Выбрать активного питомца для аккаунта"""
    def post(self, request, pet_id):
        user_pet = get_object_or_404(UserPet, id=pet_id, user=request.user)
        UserPet.objects.filter(user=request.user, is_selected=True).update(is_selected=False)
        
        # Выбираем нового
        user_pet.is_selected = True
        user_pet.save()
        
        # Обновляем рейтинги ВСЕХ героев пользователя
     
        
        for character in Character.objects.filter(user=request.user):
            update_hero_leaderboard(Character, character)
        
        return Response({"status": "ok", "selected_pet": user_pet.pet.name})

class SummonPetView(APIView):
    permission_classes = [permissions.IsAuthenticated]
    throttle_classes = [SummonThrottle]

    @transaction.atomic
    def post(self, request):
        serializer = SummonPetRequestSerializer(data=request.data, context={'request': request})
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        user = request.user
        coupons = data['coupons']
        diamonds = data['diamonds']
        summons = data['summons']
        summon_config, _ = UserSummonConfig.objects.get_or_create(user=user)

        # Трата валюты
        if coupons > 0:
            user.soul_coupons -= coupons
        if diamonds > 0:
            user.diamonds -= diamonds
        user.save(update_fields=['soul_coupons', 'diamonds'] if coupons > 0 and diamonds > 0 else ['soul_coupons'] if coupons > 0 else ['diamonds'])

        # Cache all_pets grouped by rarity (Redis dict)
        cache_key = 'all_pets_by_rarity'
        pets_by_rarity = cache.get(cache_key)
        if not pets_by_rarity:
            pets_by_rarity = {}
            for pet in Pet.objects.all():
                pets_by_rarity[pet.rarity].append(pet)
            cache.set(cache_key, pets_by_rarity, timeout=3600)

        owned_pet_ids = UserPet.objects.filter(user=user).values_list('pet_id', flat=True)
        available_by_rarity = {
            rarity: [p for p in pets if p.id not in owned_pet_ids]
            for rarity, pets in pets_by_rarity.items()
        }

        if all(len(pets) == 0 for pets in available_by_rarity.values()):
            return Response({"error": "У вас уже есть все питомцы"}, status=status.HTTP_400_BAD_REQUEST)

        # Базовые шансы (%) + модификатор от lvl (shift 0.5% per level от common к rare+)
        level_bonus = summon_config.summon_level * 0.5
        chances = {
            RarityChoices.COMMON: max(45 - level_bonus, 20),  # Cap min 20% для баланса
            RarityChoices.SUPERIOR: 30,
            RarityChoices.EXCELLENT: 15,
            RarityChoices.RARE: 5 + (level_bonus * 0.4),
            RarityChoices.UNIQUE: 3 + (level_bonus * 0.3),
            RarityChoices.EPIC: 1 + (level_bonus * 0.15),
            RarityChoices.LEGENDARY: 0.7 + (level_bonus * 0.1),
            RarityChoices.IMMORTAL: 0.3 + (level_bonus * 0.05),
        }
        total = sum(chances.values())
        normalized_chances = {k: v / total * 100 for k, v in chances.items()}  # Нормализация к 100%

        summoned_pets = []
        rarities = list(chances.keys())
        weights = list(chances.values())
        for _ in range(summons):
            chosen_rarity = random.choices(rarities, weights=weights)[0]
            available = available_by_rarity.get(chosen_rarity, [])
            if not available:
                # Fallback to common if no available in rarity (rare case)
                chosen_rarity = RarityChoices.COMMON
                available = available_by_rarity[chosen_rarity]
            pet = random.choice(available)
            if chosen_rarity in [RarityChoices.UNIQUE, RarityChoices.EPIC, RarityChoices.LEGENDARY, RarityChoices.IMMORTAL] and random.random() < 0.1:
                pet.extra_bonus = {"spell_dmg_boost": 15}  # Unique по ТЗ, save if needed (but Pet shared, clone if unique per user?)
                # Если unique per drop: create new Pet instance, but ТЗ fixed 5 pets, so update extra_bonus dynamically
            user_pet = UserPet.objects.create(user=user, pet=pet)
            summoned_pets.append(pet)
            summon_config.add_exp(1)

        return Response({
            "status": "ok",
            "summoned_pets": PetSerializer(summoned_pets, many=True).data
        }, status=status.HTTP_201_CREATED)

class UserSummonConfigView(generics.RetrieveAPIView):
    serializer_class = UserSummonConfigSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_object(self):
        obj, _ = UserSummonConfig.objects.get_or_create(user=self.request.user)
        return obj