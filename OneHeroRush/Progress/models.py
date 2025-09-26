from django.db import models
from django.contrib.auth import get_user_model
from django.utils import timezone
from Characters.models import Character  # Для active hero buffs
# from common.tasks import recalculate_mmr

User = get_user_model()

class Progress(models.Model):
    '''
    Модель прогресса игрока: локация, акт/этап/волна, сложность, оффлайн-фарм. Связь 1:1 с User. Обновление после волн, расчёт оффлайн gold/keys.
    '''
    LOCATION_CHOICES = [
        ('heaven', 'Рай'),
        ('god_heaven', 'Рай с богом'),
        ('purgatory', 'Чистилище'),
        ('hell', 'Ад'),
        ('devil_hell', 'Ледяное Озеро Коцит'),
    ]
    DIFFICULTY_CHOICES = [
        ('easy', 'Легкий'),
        ('normal', 'Нормальный'),
        ('hard', 'Сложный'),
        ('insane', 'Нереальный'),
    ]

    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='progress')
    location = models.CharField(max_length=20, choices=LOCATION_CHOICES, default='hell')
    act = models.IntegerField(default=1)  # 1-5
    stage = models.IntegerField(default=1)  # 1-5 этапов
    wave = models.IntegerField(default=1)  # 1-5 волн
    waves_completed = models.IntegerField(default=0)  # Для MMR
    difficulty = models.CharField(max_length=20, choices=DIFFICULTY_CHOICES, default='easy')
    last_online = models.DateTimeField(default=timezone.now)  # Для оффлайн-фарма
    offline_gold = models.IntegerField(default=0)
    offline_keys = models.IntegerField(default=0)

    class Meta:
        indexes = [models.Index(fields=['user'])]

    def update_wave(self):
        '''
        Обновляет волну/этап/акт после боя. Если акт завершён — смена локации. Level_up active hero, расчёт наград, MMR async.
        '''
        self.wave += 1
        if self.wave > 5:
            self.wave = 1
            self.stage += 1
        if self.stage > 5:
            self.stage = 1
            self.act += 1
        if self.act > 5:
            self.act = 1
            # Смена локации по ТЗ: Ад -> Озеро -> Чистилище -> Рай -> Рай с богом
            locations = ['hell', 'devil_hell', 'purgatory', 'heaven', 'god_heaven']
            current_idx = locations.index(self.location)
            self.location = locations[(current_idx + 1) % 5]
        self.waves_completed += 1
        # Level_up active hero
        active_char = self.user.characters.filter(is_active=True).first()
        if active_char:
            active_char.level_up()
        # Награды (gold/keys, + босс если волна=5)
        self.user.gold += 100  # Пример
        self.user.keys += 1
        self.user.save(update_fields=['gold', 'keys'])
        self.save()
        # Async MMR
        # recalculate_mmr.delay(self.user.id)