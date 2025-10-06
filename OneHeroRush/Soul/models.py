from django.db import models
from Users.models import User  
from Characters.models import Character 

class SoulRarity(models.TextChoices):
    COMMON = 'COMMON', 'Обычный' 
    SUPERIOR = 'SUPERIOR', 'Превосходный'  # 1.0
    EXCELLENT = 'EXCELLENT', 'Отличный'  # 1.5
    RARE = 'RARE', 'Редкий'  # 2.0
    UNIQUE = 'UNIQUE', 'Уникальный'  # 2.5
    EPIC = 'EPIC', 'Эпический'  # 2.8
    LEGENDARY = 'LEGENDARY', 'Легендарный'  # 3.0, unique props
    IMMORTAL = 'IMMORTAL', 'Бессмертие'  # 3.1, highest unique

class Soul(models.Model):
    character = models.ForeignKey(Character, on_delete=models.CASCADE, related_name='souls')  
    rarity = models.CharField(max_length=20, choices=SoulRarity.choices, default=SoulRarity.COMMON)
    open_stats = models.JSONField(default=dict)  
    hidden_stats = models.JSONField(default=dict)  
    unique_properties = models.JSONField(models.CharField(max_length=100), blank=True, default=list)  
    level = models.PositiveIntegerField(default=1) 
    multiplier = models.FloatField(default=0.5) 

    def save(self, *args, **kwargs):
        # Auto-set multiplier based on rarity (optimized, no extra queries)
        rarity_multipliers = {
            SoulRarity.COMMON: 0.5, SoulRarity.SUPERIOR: 1.0, SoulRarity.EXCELLENT: 1.5,
            SoulRarity.RARE: 2.0, SoulRarity.UNIQUE: 2.5, SoulRarity.EPIC: 2.8,
            SoulRarity.LEGENDARY: 3.0, SoulRarity.IMMORTAL: 3.1
        }
        self.multiplier = rarity_multipliers.get(self.rarity, 0.5)
        super().save(*args, **kwargs)

    class Meta:
        indexes = [models.Index(fields=['character', 'rarity'])] 
        constraints = [models.UniqueConstraint(fields=['character'], name='unique_soul_per_character_template')]  

class PlayerSoul(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='player_souls')
    soul = models.ForeignKey(Soul, on_delete=models.PROTECT)  
    equipped_to_character = models.ForeignKey(Character, on_delete=models.SET_NULL, null=True, blank=True, related_name='equipped_souls')  
    summon_count = models.PositiveIntegerField(default=0)  # Track for exp to summon_lvl

    class Meta:
        unique_together = ('user', 'equipped_to_character') 
        indexes = [models.Index(fields=['user', 'equipped_to_character'])]  

class SummonLevel(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, primary_key=True)
    level = models.PositiveIntegerField(default=1)
    experience = models.PositiveBigIntegerField(default=0)  

    rarity_chances = models.JSONField(default=dict)

    def add_experience(self, amount):
        self.experience += amount
        while self.experience >= self.exp_needed_for_next_level():
            self.level += 1
            self.experience -= self.exp_needed_for_next_level()  
            self.adjust_rarity_chances()  
        self.save()

    def exp_needed_for_next_level(self):
        return self.level * 100  

    def adjust_rarity_chances(self):
        boost = self.level * 0.001
        self.rarity_chances['IMMORTAL'] += boost
        self.rarity_chances['LEGENDARY'] += boost

    def save(self, *args, **kwargs):
        # Автоматически заполняем при создании
        if not self.rarity_chances:  # Если пустой
            self.rarity_chances = {
                'COMMON': 0.45, 'SUPERIOR': 0.30, 'EXCELLENT': 0.15, 'RARE': 0.05,
                'UNIQUE': 0.03, 'EPIC': 0.}