import logging
from django.db import models
from django.contrib.postgres.fields import JSONField
from django.contrib.auth import get_user_model
from random import choices, uniform
from django.forms import ValidationError

logger = logging.getLogger(__name__)


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
    RARITY_WEIGHTS = [45, 30, 15, 5, 3, 1, 0.7, 0.3]  # Шансы 

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='items')
    name = models.CharField(max_length=50, choices=ITEM_CHOICES)
    level = models.PositiveIntegerField(default=1)
    stats = models.JSONField(default=dict) 
    rarity_multiplier = models.FloatField(choices=RARITY_CHOICES, default=0.5)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        indexes = [models.Index(fields=['user', 'name'])]

    def save(self, *args, **kwargs):
        try:
            is_new = not self.pk
            logger.debug(f"Saving item: user={self.user.username}, name={self.name}, new={is_new}")
            
            if is_new:
                self.randomize_stats()
                
            super().save(*args, **kwargs)
            
            logger.info(f"Item saved successfully: ID={self.pk}, user={self.user.username}, name={self.name}")
            
        except Exception as e:
            logger.error(f"Error saving item for user {self.user.username}: {str(e)}")
            raise

    def randomize_stats(self):
        '''
        Полная рандомизация статов по ТЗ (vampirism, crit и т.д.) * rarity_multiplier.
        '''
        try:
            logger.debug(f"Randomizing stats for item: {self.name}, rarity={self.rarity_multiplier}")
            
            stats_keys = ['vampirism', 'crit', 'evasion', 'resist_magic', 'heal_reduction', 'regen_hp', 'regen_mp', 'armor', 'attack_speed', 
                         'int', 'str', 'agi', 'hp', 'mp', 'armor_reduction', 'magic_armor_reduction', 'attack_range', 'damage', 'move_speed']
            
            self.stats = {k: round(uniform(5, 15) * self.rarity_multiplier) for k in stats_keys}
            
            logger.info(f"Stats randomized for {self.name}: {self.stats}")
            
        except Exception as e:
            logger.error(f"Error randomizing stats for item {self.name}: {str(e)}")
            raise

    def delete(self, *args, **kwargs):
        try:
            logger.info(f"Deleting item: ID={self.pk}, user={self.user.username}, name={self.name}")
            
            super().delete(*args, **kwargs)
            
            logger.info(f"Item deleted: ID={self.pk}")
            
        except Exception as e:
            logger.error(f"Error deleting item {self.pk}: {str(e)}")
            raise

class Chest(models.Model):
    '''
    Модель сундука: уровень для rarity шанса, открытие за keys, auto 1-20x.
    '''
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='chests')
    level = models.PositiveIntegerField(default=1)
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
        try:
            logger.info(f"Opening chest: ID={self.pk}, user={self.user.username}, level={self.level}")

            if self.user.keys <= 0:
                logger.warning(f"Not enough keys to open chest: user={self.user.username}, keys={self.user.keys}")
                raise ValidationError("Not enough keys to open the chest.")

            # Выбор редкости с весами
            rarity_values = [choice[0] for choice in Item.RARITY_CHOICES]
            weights = Item.RARITY_WEIGHTS
            rarity_multiplier = choices(rarity_values, weights=weights)[0]
            
            # Выбор имени предмета
            name_choices = [choice[0] for choice in Item.ITEM_CHOICES]
            name = choices(name_choices)[0]

            logger.debug(f"Generated item: name={name}, rarity={rarity_multiplier}")

            # Создание предмета
            item = Item.objects.create(
                user=self.user, 
                name=name, 
                rarity_multiplier=rarity_multiplier
            )

            # Списание ключа
            old_keys = self.user.keys
            self.user.keys -= 1
            self.user.save(update_fields=['keys'])
            logger.info(f"Key spent: {old_keys} → {self.user.keys}")

            # Удаление сундука
            self.delete()
            logger.info(f"Chest opened and deleted: ID={self.pk}, item_created={item.id}")

            return item

        except Exception as e:
            logger.error(f"Error opening chest {self.pk}: {str(e)}")
            raise