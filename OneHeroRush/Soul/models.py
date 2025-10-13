from django.db import models
from django.db import transaction
from Users.models import User  
from Characters.models import Character 
import logging

logger = logging.getLogger(__name__)

class SoulRarity(models.TextChoices):
    COMMON = 'COMMON', 'Обычный' 
    SUPERIOR = 'SUPERIOR', 'Превосходный'
    EXCELLENT = 'EXCELLENT', 'Отличный'
    RARE = 'RARE', 'Редкий'
    UNIQUE = 'UNIQUE', 'Уникальный'
    EPIC = 'EPIC', 'Эпический'
    LEGENDARY = 'LEGENDARY', 'Легендарный'
    IMMORTAL = 'IMMORTAL', 'Бессмертие'

class Soul(models.Model):
    character = models.ForeignKey(Character, on_delete=models.CASCADE, related_name='souls')  
    rarity = models.CharField(max_length=20, choices=SoulRarity.choices, default=SoulRarity.COMMON)
    open_stats = models.JSONField(default=dict)  
    hidden_stats = models.JSONField(default=dict)  
    unique_properties = models.JSONField(default=list, blank=True)  
    level = models.PositiveIntegerField(default=1) 
    multiplier = models.FloatField(default=0.5) 

    def save(self, *args, **kwargs):
        try:
            rarity_multipliers = {
                SoulRarity.COMMON: 0.5, SoulRarity.SUPERIOR: 1.0, SoulRarity.EXCELLENT: 1.5,
                SoulRarity.RARE: 2.0, SoulRarity.UNIQUE: 2.5, SoulRarity.EPIC: 2.8,
                SoulRarity.LEGENDARY: 3.0, SoulRarity.IMMORTAL: 3.1
            }
            self.multiplier = rarity_multipliers.get(self.rarity, 0.5)
            super().save(*args, **kwargs)
            logger.debug(f"Soul {self.id} saved with multiplier {self.multiplier}")
        except Exception as e:
            logger.error(f"Error saving soul: {str(e)}")
            raise

    class Meta:
        indexes = [models.Index(fields=['character', 'rarity'])] 
        constraints = [models.UniqueConstraint(fields=['character'], name='unique_soul_per_character_template')]  

class PlayerSoul(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='player_souls')
    soul = models.ForeignKey(Soul, on_delete=models.PROTECT)  
    equipped_to_character = models.ForeignKey(Character, on_delete=models.SET_NULL, null=True, blank=True, related_name='equipped_souls')  
    summon_count = models.PositiveIntegerField(default=0)

    class Meta:
        unique_together = ('user', 'equipped_to_character') 
        indexes = [models.Index(fields=['user', 'equipped_to_character'])]  

class SummonLevel(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, primary_key=True)
    level = models.PositiveIntegerField(default=1)
    experience = models.PositiveBigIntegerField(default=0)  
    rarity_chances = models.JSONField(default=dict)

    def add_experience(self, amount):
        try:
            with transaction.atomic():
                self.experience += amount
                levels_gained = 0
                
                while self.experience >= self.exp_needed_for_next_level():
                    levels_gained += 1
                    self.experience -= self.exp_needed_for_next_level()
                    self.level += 1
                    self.adjust_rarity_chances()
                    logger.info(f"Summon level up for user {self.user.id}: level {self.level}")
                
                self.save()
                
                if levels_gained > 0:
                    logger.info(f"User {self.user.id} gained {levels_gained} summon level(s), now level {self.level}")
                    
        except Exception as e:
            logger.error(f"Error adding experience to summon level for user {self.user.id}: {str(e)}")
            raise

    def exp_needed_for_next_level(self):
        return self.level * 100

    def adjust_rarity_chances(self):
        try:
            boost = self.level * 0.001
            if 'IMMORTAL' not in self.rarity_chances:
                self._initialize_rarity_chances()
            
            self.rarity_chances['IMMORTAL'] = min(0.01 + boost, 0.05)  # Cap at 5%
            self.rarity_chances['LEGENDARY'] = min(0.02 + boost, 0.08)  # Cap at 8%
            logger.debug(f"Adjusted rarity chances for user {self.user.id}: {self.rarity_chances}")
        except Exception as e:
            logger.error(f"Error adjusting rarity chances for user {self.user.id}: {str(e)}")
            raise

    def _initialize_rarity_chances(self):
        """Инициализация шансов при первом создании"""
        self.rarity_chances = {
            'COMMON': 0.45, 'SUPERIOR': 0.30, 'EXCELLENT': 0.15, 'RARE': 0.05,
            'UNIQUE': 0.03, 'EPIC': 0.02, 'LEGENDARY': 0.02, 'IMMORTAL': 0.01
        }

    def save(self, *args, **kwargs):
        try:
            if not self.rarity_chances:
                self._initialize_rarity_chances()
            super().save(*args, **kwargs)
        except Exception as e:
            logger.error(f"Error saving summon level for user {self.user.id}: {str(e)}")
            raise