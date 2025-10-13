from django.db import models, transaction
from django.conf import settings
import logging

logger = logging.getLogger(__name__)

User = settings.AUTH_USER_MODEL

class RarityChoices(models.TextChoices):
    COMMON = 'COMMON', 'Обычный'  # 0.5x
    SUPERIOR = 'SUPERIOR', 'Превосходный'  # 1.0x
    EXCELLENT = 'EXCELLENT', 'Отличный'  # 1.5x
    RARE = 'RARE', 'Редкий'  # 2.0x
    UNIQUE = 'UNIQUE', 'Уникальный'  # 2.5x
    EPIC = 'EPIC', 'Эпический'  # 2.8x
    LEGENDARY = 'LEGENDARY', 'Легендарный'  # 3.0x
    IMMORTAL = 'IMMORTAL', 'Бессмертие'  # 3.1x

class Pet(models.Model):
    """Справочник питомцев"""
    name = models.CharField(max_length=100, unique=True)
    description = models.TextField(blank=True)
    rarity = models.CharField(max_length=20, choices=RarityChoices.choices, default=RarityChoices.COMMON)
    extra_bonus = models.JSONField(default=dict, blank=True)

    # Бонусы
    bonus_gold = models.FloatField(default=0)
    bonus_mana_regen = models.FloatField(default=0)
    bonus_spell_damage = models.FloatField(default=0)
    bonus_magic_resist = models.FloatField(default=0)
    bonus_health = models.IntegerField(default=0)
    bonus_hp_regen = models.FloatField(default=0)
    bonus_damage = models.FloatField(default=0)
    bonus_move_speed = models.FloatField(default=0)
    bonus_attack_range = models.FloatField(default=0)
    bonus_crit_chance = models.FloatField(default=0)

    class Meta:
        indexes = [models.Index(fields=['rarity'])]  

    def __str__(self):
        return self.name

    def get_multiplier(self):
        multipliers = {
            RarityChoices.COMMON: 0.5,
            RarityChoices.SUPERIOR: 1.0,
            RarityChoices.EXCELLENT: 1.5,
            RarityChoices.RARE: 2.0,
            RarityChoices.UNIQUE: 2.5,
            RarityChoices.EPIC: 2.8,
            RarityChoices.LEGENDARY: 3.0,
            RarityChoices.IMMORTAL: 3.1,
        }
        return multipliers.get(self.rarity, 1.0)

class UserPet(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="user_pets")
    pet = models.ForeignKey(Pet, on_delete=models.CASCADE)
    is_selected = models.BooleanField(default=False) 
    level = models.PositiveIntegerField(default=1)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ("user", "pet")
        indexes = [models.Index(fields=['user', 'is_selected'])]

    def __str__(self):
        return f"{self.user.username} - {self.pet.name}"

class UserSummonConfig(models.Model):
    """Конфиг призыва для пользователя"""
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name="summon_config")
    summon_level = models.PositiveIntegerField(default=1)
    summon_exp = models.PositiveIntegerField(default=0)

    def add_exp(self, amount):
        try:
            with transaction.atomic():
                self.summon_exp += amount
                while self.summon_exp >= self.exp_to_next_level():
                    self.summon_exp -= self.exp_to_next_level()
                    self.summon_level += 1
                    logger.info(f"User {self.user.id} leveled up summon to {self.summon_level}")
                self.save()
        except Exception as e:
            logger.error(f"Error adding exp to user {self.user.id}: {str(e)}")
            raise

    def exp_to_next_level(self):
        return 100 * self.summon_level