from django.db import models
from django.contrib.postgres.fields import JSONField
from django.contrib.auth import get_user_model
from random import choices, uniform

from django.forms import ValidationError

User = get_user_model()

class Item(models.Model):
    '''
    Модель предмета: рандом stats (JSONB для vampirism/crit и т.д.), rarity multiplier (0.5-3.1), level. Генерируется из chest open.
    '''
    ITEM_CHOICES = [
        ('Power Treads', 'Power Treads'),
        ('Phase Boots', 'Phase Boots'),
        ('Tranquil Boots', 'Tranquil Boots'),
        ('Arcane Boots', 'Arcane Boots'),
        ('Guardian Greaves', 'Guardian Greaves'),
        ('Boots of Travel', 'Boots of Travel'),
        ('Hand of Midas', 'Hand of Midas'),
        ('Manta Style', 'Manta Style'),
        ('Blink Dagger', 'Blink Dagger'),
        ('Shadow Blade', 'Shadow Blade'),
        ('Silver Edge', 'Silver Edge'),
        ('Monkey King Bar', 'Monkey King Bar'),
        ('Battle Fury', 'Battle Fury'),
        ('Crystalys', 'Crystalys'),
        ('Daedalus', 'Daedalus'),
        ('Abyssal Blade', 'Abyssal Blade'),
        ('Magic Wand', 'Magic Wand'),
        ('Null Talisman', 'Null Talisman'),
        ('Wraith Band', 'Wraith Band'),
        ('Bracer', 'Bracer'),
        ('Ring of Basilius', 'Ring of Basilius'),
        ('Medallion of Courage', 'Medallion of Courage'),
        ('Solar Crest', 'Solar Crest'),
        ('Dragon Lance', 'Dragon Lance'),
        ('Dagon', 'Dagon'),
        ('Orchid Malevolence', 'Orchid Malevolence'),
        ('Bloodthorn', 'Bloodthorn'),
        ('Scythe of Vyse', 'Scythe of Vyse'),
        ('Shiva\'s Guard', 'Shiva\'s Guard'),
        ('Rod of Atos', 'Rod of Atos'),
        ('Glimmer Cape', 'Glimmer Cape'),
        ('Force Staff', 'Force Staff'),
        ('Mekansm', 'Mekansm'),
        ('Pipe of Insight', 'Pipe of Insight'),
        ('Urn of Shadows', 'Urn of Shadows'),
        ('Spirit Vessel', 'Spirit Vessel'),
        ('Lotus Orb', 'Lotus Orb'),
        ('Aether Lens', 'Aether Lens'),
        ('Vanguard', 'Vanguard'),
        ('Crimson Guard', 'Crimson Guard'),
        ('Hood of Defiance', 'Hood of Defiance'),
        ('Black King Bar', 'Black King Bar'),
        ('Assault Cuirass', 'Assault Cuirass'),
        ('Heart of Tarrasque', 'Heart of Tarrasque'),
        ('Blade Mail', 'Blade Mail'),
        ('Desolator', 'Desolator'),
        ('Maelstrom', 'Maelstrom'),
        ('Mjollnir', 'Mjollnir'),
        ('Armlet of Mordiggian', 'Armlet of Mordiggian'),
        ('Sange and Yasha', 'Sange and Yasha'),
        ('Heaven\'s Halberd', 'Heaven\'s Halberd'),
        ('Skull Basher', 'Skull Basher'),
        ('Echo Sabre', 'Echo Sabre'),
        ('Claymore', 'Claymore'),
        ('Broadsword', 'Broadsword'),
        ('Mithril Hammer', 'Mithril Hammer'),
        ('Javelin', 'Javelin'),
        ('Blood Grenade', 'Blood Grenade'),
        ('Gauntlets of Strength', 'Gauntlets of Strength'),
        ('Mantle of Intelligence', 'Mantle of Intelligence'),
        ('Slippers of Agility', 'Slippers of Agility'),
        ('Circlet', 'Circlet'),
    ]
    RARITY_CHOICES = [
        (0.5, 'Common'),
        (1.0, 'Uncommon'),
        (1.5, 'Rare'),
        (2.0, 'Mythical'),
        (2.5, 'Legendary'),
        (2.8, 'Ancient'),
        (3.0, 'Immortal'),
        (3.1, 'Arcana'),
    ]
    RARITY_WEIGHTS = [45, 30, 15, 5, 3, 1, 0.7, 0.3]  # Шансы по ТЗ

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='items')
    name = models.CharField(max_length=50, choices=ITEM_CHOICES)
    level = models.PositiveIntegerField(default=1)
    stats = models.JSONField(default=dict)  # Randomized: vampirism, crit и т.д.
    rarity_multiplier = models.FloatField(choices=RARITY_CHOICES, default=0.5)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        indexes = [models.Index(fields=['user', 'name'])]

    def save(self, *args, **kwargs):
        if not self.pk:
            self.randomize_stats()  # Рандом при создании
        super().save(*args, **kwargs)

    def randomize_stats(self):
        '''
        Полная рандомизация статов по ТЗ (vampirism, crit и т.д.) * rarity_multiplier.
        '''
        stats_keys = ['vampirism', 'crit', 'evasion', 'resist_magic', 'heal_reduction', 'regen_hp', 'regen_mp', 'armor', 'attack_speed', 
                      'int', 'str', 'agi', 'hp', 'mp', 'armor_reduction', 'magic_armor_reduction', 'attack_range', 'damage', 'move_speed']
        self.stats = {k: round(uniform(5, 15) * self.rarity_multiplier) for k in stats_keys}  # Пример рандом

class Chest(models.Model):
    '''
    Модель сундука: уровень для rarity шанса, открытие за keys, auto 1-20x.
    '''
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='chests')
    level = models.PositiveIntegerField(default=1)  # Влияет на rarity
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        indexes = [models.Index(fields=['user', 'level'])]

    def open(self):
        """
        Открывает сундук:
        - проверяет наличие ключей
        - списывает 1 ключ
        - генерирует предмет
        - удаляет сундук
        """
        if self.user.keys <= 0:
            raise ValidationError("Not enough keys to open the chest.")

        rarity_values = [choice[0] for choice in Item.RARITY_CHOICES]
        weights = Item.RARITY_WEIGHTS
        rarity_multiplier = choices(rarity_values, weights=weights)[0]
        name = choices([choice[0] for choice in Item.ITEM_CHOICES])[0]

        # создаем предмет
        item = Item.objects.create(
            user=self.user, 
            name=name, 
            rarity_multiplier=rarity_multiplier
        )

        # списываем ключ
        self.user.keys -= 1
        self.user.save(update_fields=['keys'])

        # удаляем сундук
        self.delete()

        return item