from django.conf import settings
from django.db import models
from django.contrib.postgres.fields import JSONField
from django.contrib.auth import get_user_model
from django.utils import timezone
from django.db import transaction
from common.tasks import recalculate_mmr

User = get_user_model()

class Quest(models.Model):
    '''
    Модель квеста: тип (ежедневный/постоянный/мини), условия (JSONB для гибкости, e.g. {'defeat_enemies': 150}), награды. M2M с User для выполненных.
    '''
    TYPE_CHOICES = [
        ('daily', 'Ежедневный'),
        ('permanent', 'Постоянный'),
        ('mini', 'Мини-квест'),
    ]

    name = models.CharField(max_length=100)  # e.g. "Победить врагов 150 раз"
    type = models.CharField(max_length=20, choices=TYPE_CHOICES)
    conditions = models.JSONField(default=dict)  # e.g. {'defeat_enemies': 150, 'waves': 10}
    reward_diamonds = models.IntegerField(default=0)
    reward_souls = models.IntegerField(default=0)
    reward_gold = models.IntegerField(default=0)
    reward_keys = models.IntegerField(default=0)
    users_completed = models.ManyToManyField(User, related_name='completed_quests', blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    reset_at = models.DateTimeField(null=True, blank=True)  # Для ежедневных reset

    class Meta:
        indexes = [models.Index(fields=['type'])]

    def complete(self, user):
        '''
        Завершает квест для игрока: начисляет награды, добавляет в completed, update MMR async.
        '''
        if user not in self.users_completed.all():
            with transaction.atomic():
                user.diamonds += self.reward_diamonds
                user.souls += self.reward_souls
                user.gold += self.reward_gold
                user.keys += self.reward_keys
                user.save(update_fields=['diamonds', 'souls', 'gold', 'keys'])
                self.users_completed.add(user)
                self.save()
            # Async уведомление и MMR
            # send_mail_notification.delay(user.id, f"Квест '{self.name}' завершён! Награда: {self.reward_diamonds} алмазов + {self.reward_souls} душ")
            recalculate_mmr.delay(user.id)
class Achievement(models.Model):
    """
    Достижения (например: пройти 100 волн, убить 1000 крипов, вступить в клан).
    """
    title = models.CharField(max_length=100)
    description = models.TextField(blank=True)
    points = models.PositiveIntegerField(default=10)  # сколько очков MMR даёт достижение

    def __str__(self):
        return self.title


class UserAchievement(models.Model):
    """
    Связка: какой пользователь какое достижение получил.
    """
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="achievements")
    achievement = models.ForeignKey(Achievement, on_delete=models.CASCADE)
    earned_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ("user", "achievement")  # нельзя дважды одно и то же достижение

    def __str__(self):
        return f"{self.user} → {self.achievement}"
