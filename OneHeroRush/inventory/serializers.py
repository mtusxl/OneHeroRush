from rest_framework import serializers
from .models import Item, Chest

class ItemSerializer(serializers.ModelSerializer):
    '''
    Сериализатор предмета: для list/equip/sell.
    '''
    class Meta:
        model = Item
        fields = ['id', 'name', 'level', 'stats', 'rarity_multiplier']

class ChestSerializer(serializers.ModelSerializer):
    '''
    Сериализатор сундука: для list/open.
    '''
    class Meta:
        model = Chest
        fields = ['id', 'level']

class OpenChestSerializer(serializers.Serializer):
    '''
    Для POST open: количество открытий (1-20 auto).
    '''
    count = serializers.IntegerField(min_value=1, max_value=20, default=1)