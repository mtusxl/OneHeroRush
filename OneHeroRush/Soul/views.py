from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from django.shortcuts import get_object_or_404
from django.db.transaction import atomic  # For atomic summons to prevent race conditions in multi-player
from .models import Soul, PlayerSoul, SummonLevel, SoulRarity
from .serializers import PlayerSoulSerializer, SummonRequestSerializer
from Users.models import UserProfile  # Assume has diamonds, soul_coupons fields
import random  # For rarity roll, but use numpy if ML-balanced in future (2025 std)
from Characters.models import Character

class SummonSoulView(APIView):
    # Throttle: inherit from global 5/min anon, but for auth users higher via Redis rate limit
    def post(self, request):
        serializer = SummonRequestSerializer(data=request.data)
        if serializer.is_valid():
            with atomic():  # Scalable transaction for 10k+ users
                profile = get_object_or_404(UserProfile, user=request.user)  # Assume UserProfile with currencies
                coupons = serializer.validated_data['coupons']
                diamonds = serializer.validated_data['diamonds']
                character = get_object_or_404(Character, id=serializer.validated_data['character_id'])

                # Calc effective coupons: 1 coupon or 2 diamonds = 1 summon unit
                if coupons > 0 and diamonds > 0:
                    return Response({'error': 'Use either coupons or diamonds'}, status=status.HTTP_400_BAD_REQUEST)
                
                if coupons:
                    if coupons not in [15, 30]:  # TZ specific batches
                        return Response({'error': 'Invalid coupon amount'}, status=status.HTTP_400_BAD_REQUEST)
                    summons = 15 if coupons == 15 else 35  # Bonus for 30
                    if profile.soul_coupons < coupons:
                        return Response({'error': 'Insufficient coupons'}, status=status.HTTP_400_BAD_REQUEST)
                    profile.soul_coupons -= coupons
                elif diamonds:
                    effective_coupons = diamonds // 2  # 1 coupon = 2 diamonds
                    summons = effective_coupons  # No batch bonus for diamonds
                    if profile.diamonds < diamonds:
                        return Response({'error': 'Insufficient diamonds'}, status=status.HTTP_400_BAD_REQUEST)
                    profile.diamonds -= diamonds
                else:
                    return Response({'error': 'Provide coupons or diamonds'}, status=status.HTTP_400_BAD_REQUEST)
                
                profile.save()
                summon_lvl, _ = SummonLevel.objects.get_or_create(user=request.user)
                
                new_souls = []
                for _ in range(summons):
                    # Roll rarity based on lvl-adjusted chances (optimized dict access)
                    chances = summon_lvl.rarity_chances
                    rarity = random.choices(list(chances.keys()), weights=list(chances.values()))[0]
                    
                    # Create or get soul template for character + rarity (cache if frequent)
                    soul, _ = Soul.objects.get_or_create(
                        character=character, rarity=rarity,
                        defaults={
                            'open_stats': self.generate_open_stats(rarity),  # Func for random stats per TZ (vampirism etc, but for souls it's character-unique)
                            'hidden_stats': self.generate_hidden_stats(),  # Admin-tuned
                            'unique_properties': self.generate_unique_props(rarity) if rarity in ['LEGENDARY', 'IMMORTAL'] else []
                        }
                    )
                    
                    player_soul = PlayerSoul.objects.create(user=request.user, soul=soul)
                    new_souls.append(player_soul)
                    summon_lvl.add_experience(1)  # 1 exp per summon unit
                
                return Response({'souls': PlayerSoulSerializer(new_souls, many=True).data}, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    def generate_open_stats(self, rarity):
        # TZ: randomized like items, but character-unique - e.g. damage, hp, etc. Multiplied by rarity later in character calc
        base_stats = {'damage': random.randint(5, 20), 'hp_regen': random.randint(1, 5)}  # Extend per character/race
        return base_stats
    
    def generate_hidden_stats(self):
        return {'balance_tweak': random.randint(-5, 5)}  # Patchnote hidden
    
    def generate_unique_props(self, rarity):
        # TZ: unique for rarest, e.g. +15% spell dmg vs specific creeps
        return ['+15% spell dmg vs Shadow Demon’s Shadow'] if rarity == 'IMMORTAL' else []