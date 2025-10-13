# serializers.py
import logging
from rest_framework import serializers
from .models import Item, Chest

logger = logging.getLogger(__name__)

class ItemSerializer(serializers.ModelSerializer):
    '''
    Сериализатор предмета: для list/equip/sell.
    '''
    class Meta:
        model = Item
        fields = ['id', 'name', 'level', 'stats', 'rarity_multiplier', 'is_equipped']

    def validate_name(self, value):
        try:
            valid_names = [choice for choice in Item.ITEM_CHOICES]
            if value not in valid_names:
                logger.warning(f"Invalid item name: {value}")
                raise serializers.ValidationError("Invalid item name")
            return value
        except Exception as e:
            logger.error(f"Error validating item name {value}: {str(e)}")
            raise

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

    def validate_count(self, value):
        try:
            if value < 1 or value > 20:
                logger.warning(f"Invalid chest open count: {value}")
                raise serializers.ValidationError("Count must be between 1 and 20")
            return value
        except Exception as e:
            logger.error(f"Error validating chest count {value}: {str(e)}")
            raise