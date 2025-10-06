from random import uniform
from django.db import models
from django.contrib.postgres.fields import JSONField
from django.contrib.auth import get_user_model
from common.tasks import send_mail_notification

User = get_user_model() 

class Character(models.Model):
    '''
    Модель героя для игры. Хранит данные о герое: имя, уровень, статы (JSONB для рандома), бонусы расы, предметы, душу. 
    Авто-расчёт бонусов и статов при создании, эволюция при level_up. 
    Используется для выбора/активации, расчёта мощи для MMR/лидеров.
    '''
    HERO_CHOICES = [
        ('Pudge', 'Pudge'),
        ('Necrophos', 'Necrophos'),
        ('Juggernaut', 'Juggernaut'),
        ('Phantom Assassin', 'Phantom Assassin'),
        ('Lifestealer', 'Lifestealer'),
        ('Rubick', 'Rubick'),
        ('Ursa', 'Ursa'),
        ('Axe', 'Axe'),
        ('Shadow Fiend', 'Shadow Fiend'),
        ('Zeus', 'Zeus'),
        ('Lion', 'Lion'),
        ('Legion Commander', 'Legion Commander'),
        ('Sniper', 'Sniper'),
        ('Invoker', 'Invoker'),
        ('Crystal Maiden', 'Crystal Maiden'),
        ('Windranger', 'Windranger'),
        ('Ogre Magi', 'Ogre Magi'),
        ('Witch Doctor', 'Witch Doctor'),
        ('Drow Ranger', 'Drow Ranger'),
        ('Vengeful Spirit', 'Vengeful Spirit'),
        ('Lich', 'Lich'),
        ('Tidehunter', 'Tidehunter'),
        ('Slark', 'Slark'),
        ('Mirana', 'Mirana'),
        ('Bounty Hunter', 'Bounty Hunter'),
        ('Riki', 'Riki'),
        ('Spirit Breaker', 'Spirit Breaker'),
    ]
    RACE_BONUSES = {
        'Humans': {'damage_to_creeps': 0.15, 'mana_regen': 2},
        'Undead': {'health': 150, 'health_regen': 0.10},
        'Ogres': {'health': 0.20, 'damage_to_creeps': 0.10},
        'Trolls': {'spell_damage_to_creeps': 0.15, 'movement_speed': 0.03},
        'Demons': {'physical_damage': 15, 'spell_damage': 0.10},
        'Elves': {'crit_chance_to_creeps': 0.10, 'mana_regen': 3},  # crit 1.5x implied in logic
        'Sea Creatures': {'armor': 3, 'health_regen': 0.10},
        'Mythical Creatures': {'spell_damage_to_creeps': 0.15, 'cooldown_reduction': 0.05},
        'Beasts': {'damage_to_creeps': 0.20, 'health': 0.10},
        'Kin': {'attack_range': 0.10, 'damage_to_creeps': 0.10},
        'Red Mist': {'armor': 3, 'damage_to_creeps': 0.15},
        'Arcane Masters': {'spell_damage_to_creeps': 0.15, 'mana_regen': 3},
        'Shadow Satyrs': {'damage_to_creeps': 0.15, 'evasion': 0.05},
    }

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='characters')
    hero_name = models.CharField(max_length=50, choices=HERO_CHOICES)
    level = models.PositiveIntegerField(default=1)
    stats = models.JSONField(default=dict) 
    race_bonus = models.JSONField(default=dict) 
    items = models.ManyToManyField('inventory.Item', related_name='characters', blank=True) 
    soul = models.ForeignKey('Soul.Soul', on_delete=models.SET_NULL, null=True, blank=True, related_name="character_souls")  
    is_active = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)


    class Meta:
        indexes = [
            models.Index(fields=['user', 'hero_name']),
            models.Index(fields=['user', 'is_active']),
        ]
        unique_together = ['user', 'hero_name']  # Один герой на юзера

    def randomize_base_stats(self):
        '''
        Рандомизирует базовые статы героя (±10% от Dota-значений) для разнообразия при создании.
        '''
        base_stats = {
            'Pudge': {'str': 25, 'agi': 17, 'int': 16, 'hp': 700, 'mp': 267, 'armor': 1, 'damage': 55, 'move_speed': 280, 'attack_range': 175, 'regen_hp': 3.5, 'regen_mp': 0.8, 'vampirism': 0, 'crit': 0, 'evasion': 0, 'resist_magic': 0.25, 'heal_reduction': 0, 'armor_reduction': 0, 'magic_armor_reduction': 0},
            'Necrophos': {'str': 18, 'agi': 15, 'int': 21, 'hp': 560, 'mp': 327, 'armor': 1, 'damage': 48, 'move_speed': 280, 'attack_range': 550, 'regen_hp': 1.7, 'regen_mp': 1.05, 'vampirism': 0, 'crit': 0, 'evasion': 0, 'resist_magic': 0.25, 'heal_reduction': 0, 'armor_reduction': 0, 'magic_armor_reduction': 0},
            'Juggernaut': {'str': 20, 'agi': 36, 'int': 14, 'hp': 600, 'mp': 243, 'armor': 4.76, 'damage': 58, 'move_speed': 305, 'attack_range': 150, 'regen_hp': 1.5, 'regen_mp': 0.7, 'vampirism': 0, 'crit': 0, 'evasion': 0, 'resist_magic': 0.25, 'heal_reduction': 0, 'armor_reduction': 0, 'magic_armor_reduction': 0},
            'Phantom Assassin': {'str': 21, 'agi': 23, 'int': 15, 'hp': 620, 'mp': 255, 'armor': 3.68, 'damage': 49, 'move_speed': 305, 'attack_range': 150, 'regen_hp': 1.55, 'regen_mp': 0.75, 'vampirism': 0, 'crit': 0, 'evasion': 0, 'resist_magic': 0.25, 'heal_reduction': 0, 'armor_reduction': 0, 'magic_armor_reduction': 0},
            'Lifestealer': {'str': 25, 'agi': 19, 'int': 15, 'hp': 700, 'mp': 255, 'armor': 2.04, 'damage': 52, 'move_speed': 320, 'attack_range': 150, 'regen_hp': 2.25, 'regen_mp': 0.75, 'vampirism': 0, 'crit': 0, 'evasion': 0, 'resist_magic': 0.25, 'heal_reduction': 0, 'armor_reduction': 0, 'magic_armor_reduction': 0},
            'Rubick': {'str': 21, 'agi': 23, 'int': 25, 'hp': 620, 'mp': 375, 'armor': 2.68, 'damage': 50, 'move_speed': 290, 'attack_range': 550, 'regen_hp': 1.55, 'regen_mp': 1.25, 'vampirism': 0, 'crit': 0, 'evasion': 0, 'resist_magic': 0.25, 'heal_reduction': 0, 'armor_reduction': 0, 'magic_armor_reduction': 0},
            'Ursa': {'str': 25, 'agi': 18, 'int': 16, 'hp': 700, 'mp': 267, 'armor': 3.88, 'damage': 47, 'move_speed': 310, 'attack_range': 150, 'regen_hp': 2.25, 'regen_mp': 0.8, 'vampirism': 0, 'crit': 0, 'evasion': 0, 'resist_magic': 0.25, 'heal_reduction': 0, 'armor_reduction': 0, 'magic_armor_reduction': 0},
            'Axe': {'str': 25, 'agi': 20, 'int': 18, 'hp': 700, 'mp': 291, 'armor': 1.2, 'damage': 52, 'move_speed': 310, 'attack_range': 150, 'regen_hp': 4.25, 'regen_mp': 0.9, 'vampirism': 0, 'crit': 0, 'evasion': 0, 'resist_magic': 0.25, 'heal_reduction': 0, 'armor_reduction': 0, 'magic_armor_reduction': 0},
            'Shadow Fiend': {'str': 19, 'agi': 20, 'int': 18, 'hp': 580, 'mp': 291, 'armor': 2.2, 'damage': 39, 'move_speed': 300, 'attack_range': 500, 'regen_hp': 1.35, 'regen_mp': 0.9, 'vampirism': 0, 'crit': 0, 'evasion': 0, 'resist_magic': 0.25, 'heal_reduction': 0, 'armor_reduction': 0, 'magic_armor_reduction': 0},
            'Zeus': {'str': 19, 'agi': 11, 'int': 22, 'hp': 580, 'mp': 339, 'armor': 1.76, 'damage': 51, 'move_speed': 315, 'attack_range': 380, 'regen_hp': 1.35, 'regen_mp': 1.1, 'vampirism': 0, 'crit': 0, 'evasion': 0, 'resist_magic': 0.25, 'heal_reduction': 0, 'armor_reduction': 0, 'magic_armor_reduction': 0},
            'Lion': {'str': 18, 'agi': 18, 'int': 20, 'hp': 560, 'mp': 315, 'armor': 1.88, 'damage': 49, 'move_speed': 290, 'attack_range': 600, 'regen_hp': 1.7, 'regen_mp': 1, 'vampirism': 0, 'crit': 0, 'evasion': 0, 'resist_magic': 0.25, 'heal_reduction': 0, 'armor_reduction': 0, 'magic_armor_reduction': 0},
            'Legion Commander': {'str': 25, 'agi': 18, 'int': 20, 'hp': 700, 'mp': 315, 'armor': 1.88, 'damage': 57, 'move_speed': 330, 'attack_range': 150, 'regen_hp': 2.25, 'regen_mp': 1, 'vampirism': 0, 'crit': 0, 'evasion': 0, 'resist_magic': 0.25, 'heal_reduction': 0, 'armor_reduction': 0, 'magic_armor_reduction': 0},
            'Sniper': {'str': 19, 'agi': 27, 'int': 15, 'hp': 580, 'mp': 255, 'armor': 2.32, 'damage': 40, 'move_speed': 285, 'attack_range': 550, 'regen_hp': 1.35, 'regen_mp': 0.75, 'vampirism': 0, 'crit': 0, 'evasion': 0, 'resist_magic': 0.25, 'heal_reduction': 0, 'armor_reduction': 0, 'magic_armor_reduction': 0},
            'Invoker': {'str': 18, 'agi': 14, 'int': 15, 'hp': 560, 'mp': 255, 'armor': 1.24, 'damage': 42, 'move_speed': 280, 'attack_range': 600, 'regen_hp': 1.7, 'regen_mp': 0.75, 'vampirism': 0, 'crit': 0, 'evasion': 0, 'resist_magic': 0.25, 'heal_reduction': 0, 'armor_reduction': 0, 'magic_armor_reduction': 0},
            'Crystal Maiden': {'str': 17, 'agi': 18, 'int': 18, 'hp': 540, 'mp': 291, 'armor': 1.88, 'damage': 46, 'move_speed': 280, 'attack_range': 625, 'regen_hp': 1.65, 'regen_mp': 0.9, 'vampirism': 0, 'crit': 0, 'evasion': 0, 'resist_magic': 0.25, 'heal_reduction': 0, 'armor_reduction': 0, 'magic_armor_reduction': 0},
            'Windranger': {'str': 17, 'agi': 17, 'int': 21, 'hp': 540, 'mp': 327, 'armor': 2.72, 'damage': 45, 'move_speed': 290, 'attack_range': 600, 'regen_hp': 1.65, 'regen_mp': 1.05, 'vampirism': 0, 'crit': 0, 'evasion': 0, 'resist_magic': 0.25, 'heal_reduction': 0, 'armor_reduction': 0, 'magic_armor_reduction': 0},
            'Ogre Magi': {'str': 23, 'agi': 14, 'int': 15, 'hp': 660, 'mp': 255, 'armor': 4.24, 'damage': 58, 'move_speed': 290, 'attack_range': 150, 'regen_hp': 5.82, 'regen_mp': 0.75, 'vampirism': 0, 'crit': 0, 'evasion': 0, 'resist_magic': 0.25, 'heal_reduction': 0, 'armor_reduction': 0, 'magic_armor_reduction': 0},
            'Witch Doctor': {'str': 18, 'agi': 13, 'int': 22, 'hp': 560, 'mp': 339, 'armor': 1.08, 'damage': 51, 'move_speed': 300, 'attack_range': 600, 'regen_hp': 1.7, 'regen_mp': 1.1, 'vampirism': 0, 'crit': 0, 'evasion': 0, 'resist_magic': 0.25, 'heal_reduction': 0, 'armor_reduction': 0, 'magic_armor_reduction': 0},
            'Drow Ranger': {'str': 16, 'agi': 28, 'int': 15, 'hp': 520, 'mp': 255, 'armor': 2.48, 'damage': 49, 'move_speed': 285, 'attack_range': 625, 'regen_hp': 1.6, 'regen_mp': 0.75, 'vampirism': 0, 'crit': 0, 'evasion': 0, 'resist_magic': 0.25, 'heal_reduction': 0, 'armor_reduction': 0, 'magic_armor_reduction': 0},
            'Vengeful Spirit': {'str': 20, 'agi': 21, 'int': 19, 'hp': 600, 'mp': 303, 'armor': 2.36, 'damage': 47, 'move_speed': 295, 'attack_range': 400, 'regen_hp': 1.5, 'regen_mp': 0.95, 'vampirism': 0, 'crit': 0, 'evasion': 0, 'resist_magic': 0.25, 'heal_reduction': 0, 'armor_reduction': 0, 'magic_armor_reduction': 0},
            'Lich': {'str': 20, 'agi': 16, 'int': 20, 'hp': 600, 'mp': 315, 'armor': 1.56, 'damage': 48, 'move_speed': 295, 'attack_range': 550, 'regen_hp': 1.5, 'regen_mp': 1, 'vampirism': 0, 'crit': 0, 'evasion': 0, 'resist_magic': 0.25, 'heal_reduction': 0, 'armor_reduction': 0, 'magic_armor_reduction': 0},
            'Tidehunter': {'str': 25, 'agi': 15, 'int': 18, 'hp': 700, 'mp': 291, 'armor': 2.4, 'damage': 53, 'move_speed': 300, 'attack_range': 150, 'regen_hp': 2.25, 'regen_mp': 0.9, 'vampirism': 0, 'crit': 0, 'evasion': 0, 'resist_magic': 0.25, 'heal_reduction': 0, 'armor_reduction': 0, 'magic_armor_reduction': 0},
            'Slark': {'str': 21, 'agi': 21, 'int': 16, 'hp': 620, 'mp': 267, 'armor': 2.36, 'damage': 56, 'move_speed': 300, 'attack_range': 150, 'regen_hp': 1.55, 'regen_mp': 0.8, 'vampirism': 0, 'crit': 0, 'evasion': 0, 'resist_magic': 0.25, 'heal_reduction': 0, 'armor_reduction': 0, 'magic_armor_reduction': 0},
            'Mirana': {'str': 18, 'agi': 24, 'int': 19, 'hp': 560, 'mp': 303, 'armor': 1.84, 'damage': 46, 'move_speed': 290, 'attack_range': 630, 'regen_hp': 1.7, 'regen_mp': 0.95, 'vampirism': 0, 'crit': 0, 'evasion': 0, 'resist_magic': 0.25, 'heal_reduction': 0, 'armor_reduction': 0, 'magic_armor_reduction': 0},
            'Bounty Hunter': {'str': 19, 'agi': 21, 'int': 22, 'hp': 580, 'mp': 339, 'armor': 4.36, 'damage': 52, 'move_speed': 325, 'attack_range': 150, 'regen_hp': 2.35, 'regen_mp': 1.1, 'vampirism': 0, 'crit': 0, 'evasion': 0, 'resist_magic': 0.25, 'heal_reduction': 0, 'armor_reduction': 0, 'magic_armor_reduction': 0},
            'Riki': {'str': 18, 'agi': 30, 'int': 14, 'hp': 560, 'mp': 243, 'armor': 4.8, 'damage': 52, 'move_speed': 315, 'attack_range': 150, 'regen_hp': 2.7, 'regen_mp': 0.7, 'vampirism': 0, 'crit': 0, 'evasion': 0, 'resist_magic': 0.25, 'heal_reduction': 0, 'armor_reduction': 0, 'magic_armor_reduction': 0},
            'Spirit Breaker': {'str': 28, 'agi': 17, 'int': 14, 'hp': 760, 'mp': 243, 'armor': 3.72, 'damage': 57, 'move_speed': 290, 'attack_range': 150, 'regen_hp': 2.5, 'regen_mp': 0.7, 'vampirism': 0, 'crit': 0, 'evasion': 0, 'resist_magic': 0.25, 'heal_reduction': 0, 'armor_reduction': 0, 'magic_armor_reduction': 0},
        }.get(self.hero_name, {})
        self.stats = {k: round(v * uniform(0.9, 1.1)) for k, v in base_stats.items()}  

    def level_up(self):
        '''
        Увеличивает уровень героя и эволюционирует статы (+10% каждые 10 уровней). 
        Вызывается из progress после волны, уведомление по почте.
        '''
        self.level += 1  
        if self.level % 10 == 0:  
            self.stats = {k: round(v * 1.1) for k, v in self.stats.items()} 
            send_mail_notification.delay(self.user.id, f"Reached level {self.level} on {self.hero_name} — +5 souls reward")
        self.save(update_fields=['level', 'stats']) 

    def save(self, *args, **kwargs):
        if not self.pk: 
            race = self.get_race()
            self.race_bonus = self.RACE_BONUSES.get(race, {})
            self.randomize_base_stats()
        super().save(*args, **kwargs)

    def get_race(self):
        '''
        Возвращает расу героя по имени для авто-бонусов. Hardcode dict для скорости.
        '''
        hero_to_race = {
            'Pudge': 'Undead',
            'Necrophos': 'Undead',
            'Juggernaut': 'Humans',
            'Phantom Assassin': 'Humans',
            'Lifestealer': 'Undead',
            'Rubick': 'Arcane Masters',
            'Ursa': 'Beasts',
            'Axe': 'Red Mist',
            'Shadow Fiend': 'Demons',
            'Zeus': 'Mythical Creatures',
            'Lion': 'Humans',
            'Legion Commander': 'Humans',
            'Sniper': 'Kin',  # Специфическая раса из ТЗ, приоритет над Humans
            'Invoker': 'Elves',
            'Crystal Maiden': 'Humans',
            'Windranger': 'Humans',
            'Ogre Magi': 'Ogres',
            'Witch Doctor': 'Trolls',
            'Drow Ranger': 'Elves',
            'Vengeful Spirit': 'Demons',
            'Lich': 'Undead',
            'Tidehunter': 'Sea Creatures',
            'Slark': 'Sea Creatures',
            'Mirana': 'Humans',
            'Bounty Hunter': 'Kin',  # Специфическая раса из ТЗ, приоритет над Humans
            'Riki': 'Shadow Satyrs',
            'Spirit Breaker': 'Mythical Creatures',
        }
        return hero_to_race.get(self.hero_name, 'Unknown')

    def compute_power(self):
        '''
        Рассчитывает мощь героя для MMR/лидеров (уровень + предметы * редкость + душа). 
        Вызывается в сериализаторе и задачах.
        '''
        # Для рейтинга (4): level + sum(item levels * rarity) + soul.level if soul
        power = self.level
        for item in self.items.all():
            power += item.level * item.rarity_multiplier
        if self.soul:
            power += self.soul.level
        return power