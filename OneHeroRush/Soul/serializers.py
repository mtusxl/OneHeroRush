from rest_framework import serializers
from .models import Soul, PlayerSoul, SummonLevel

class SoulSerializer(serializers.ModelSerializer):
    class Meta:
        model = Soul
        fields = ['id', 'character', 'rarity', 'open_stats', 'unique_properties', 'level', 'multiplier']

class PlayerSoulSerializer(serializers.ModelSerializer):
    soul = SoulSerializer(read_only=True)

    class Meta:
        model = PlayerSoul
        fields = ['id', 'soul', 'equipped_to_character', 'summon_count']

class SummonLevelSerializer(serializers.ModelSerializer):
    class Meta:
        model = SummonLevel
        fields = ['level', 'experience', 'rarity_chances']

class SummonRequestSerializer(serializers.Serializer):
    coupons = serializers.IntegerField(min_value=0, required=False, default=0)
    diamonds = serializers.IntegerField(min_value=0, required=False, default=0)
    character_id = serializers.IntegerField(required=True)

    def validate(self, data):
        coupons = data.get('coupons', 0)
        diamonds = data.get('diamonds', 0)
        
        if coupons == 0 and diamonds == 0:
            raise serializers.ValidationError("Provide either coupons or diamonds")
        
        if coupons > 0 and diamonds > 0:
            raise serializers.ValidationError("Use either coupons or diamonds, not both")
        
        if coupons > 0 and coupons not in [15, 30]:
            raise serializers.ValidationError("Coupons must be 15 or 30")
        
        return data