from rest_framework import serializers
from .models import Character
from inventory.models import Item  

class ItemSerializer(serializers.ModelSerializer):
    '''
    Сериализатор для предметов: базовые поля для nested в Character.
    '''
    class Meta:
        model = Item
        fields = ['id', 'name', 'level', 'stats', 'rarity_multiplier']

class CharacterSerializer(serializers.ModelSerializer):
    '''
    Полный сериализатор героя: статы, предметы, мощь (вычисляемая). Для list/retrieve.
    '''
    # items = ItemSerializer(many=True, read_only=True)
    power = serializers.SerializerMethodField()

    class Meta:
        model = Character
        fields = ['id', 'hero_name', 'level', 'stats', 'race_bonus', 'items', 'soul', 'is_active', 'power']

    def get_power(self, obj):
        return obj.compute_power()

class SelectCharacterSerializer(serializers.Serializer):
    '''
    Сериализатор для выбора героя: только ID.
    '''
    character_id = serializers.IntegerField(required=True)

class CreateCharacterSerializer(serializers.ModelSerializer):
    '''
    Сериализатор для создания героя: только имя (остальное auto).
    '''
    class Meta:
        model = Character
        fields = ['hero_name']