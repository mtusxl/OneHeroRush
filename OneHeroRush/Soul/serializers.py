from rest_framework import serializers
from .models import Soul, PlayerSoul, SummonLevel

class SoulSerializer(serializers.ModelSerializer):
    class Meta:
        model = Soul
        fields = ['id', 'character', 'rarity', 'open_stats', 'unique_properties', 'level', 'multiplier']  # Hide hidden_stats

class PlayerSoulSerializer(serializers.ModelSerializer):
    soul = SoulSerializer(read_only=True)

    class Meta:
        model = PlayerSoul
        fields = ['id', 'soul', 'equipped_to_character']

class SummonLevelSerializer(serializers.ModelSerializer):
    class Meta:
        model = SummonLevel
        fields = ['level', 'experience']

class SummonRequestSerializer(serializers.Serializer):
    coupons = serializers.IntegerField(min_value=0, required=False, default=0)
    diamonds = serializers.IntegerField(min_value=0, required=False, default=0)
    character_id = serializers.IntegerField(required=True)