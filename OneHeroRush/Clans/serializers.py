import logging
from rest_framework import serializers
from .models import Clan, ClanMember

logger = logging.getLogger(__name__)

class ClanSerializer(serializers.ModelSerializer):
    leader = serializers.StringRelatedField()

    class Meta:
        model = Clan
        fields = ["id", "name", "description", "leader", "members_count", "total_mmr"]

    def validate_name(self, value):
        try:
            value = value.strip()
            if len(value) < 3:
                logger.warning(f"Clan name too short: {value}")
                raise serializers.ValidationError("Название клана должно быть не менее 3 символов")
            
            if len(value) > 50:
                logger.warning(f"Clan name too long: {value}")
                raise serializers.ValidationError("Название клана должно быть не более 50 символов")
                
            logger.debug(f"Clan name validation passed: {value}")
            return value
            
        except Exception as e:
            logger.error(f"Error validating clan name {value}: {str(e)}")
            raise serializers.ValidationError("Ошибка валидации названия клана")


class ClanDetailSerializer(serializers.ModelSerializer):
    leader = serializers.StringRelatedField()
    members = serializers.SerializerMethodField()

    class Meta:
        model = Clan
        fields = ["id", "name", "description", "leader", "members", "total_mmr"]

    def get_members(self, obj):
        try:
            members = [m.user.username for m in obj.members.all()]
            logger.debug(f"Retrieved {len(members)} members for clan {obj.name}")
            return members
        except Exception as e:
            logger.error(f"Error getting members for clan {obj.id}: {str(e)}")
            return []
