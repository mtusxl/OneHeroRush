from rest_framework import serializers
from .models import Pet, UserPet, UserSummonConfig

class PetSerializer(serializers.ModelSerializer):
    multiplier = serializers.ReadOnlyField(source='get_multiplier')  

    class Meta:
        model = Pet
        fields = ["id", "name", "description", "image", "rarity", "multiplier", "extra_bonus",
                  "bonus_gold", "bonus_mana_regen", "bonus_spell_damage", "bonus_magic_resist",
                  "bonus_health", "bonus_hp_regen", "bonus_damage", "bonus_move_speed",
                  "bonus_attack_range", "bonus_crit_chance"]

class UserPetSerializer(serializers.ModelSerializer):
    pet = PetSerializer(read_only=True)

    class Meta:
        model = UserPet
        fields = ["id", "pet", "is_selected", "level", "created_at"]

class UserSummonConfigSerializer(serializers.ModelSerializer):
    class Meta:
        model = UserSummonConfig
        fields = ["summon_level", "summon_exp"]

class SummonPetRequestSerializer(serializers.Serializer):
    coupons = serializers.IntegerField(min_value=0, default=0)
    diamonds = serializers.IntegerField(min_value=0, default=0)  

    def validate(self, data):
        user = self.context['request'].user
        coupons = data['coupons']
        diamonds = data['diamonds']
        if coupons == 0 and diamonds == 0:
            raise serializers.ValidationError("Укажите купоны или алмазы")
        if coupons > 0 and user.soul_coupons < coupons:
            raise serializers.ValidationError({"coupons": "Недостаточно купонов"})
        if diamonds > 0:
            coupons_equiv = diamonds // 2  # 2 diamonds = 1 coupon
            if coupons_equiv == 0:
                raise serializers.ValidationError({"diamonds": "Недостаточно алмазов"})
            data['summons'] = coupons_equiv
        else:
            data['summons'] = coupons if coupons < 30 else coupons + 5  # Бонус за 30+
        return data