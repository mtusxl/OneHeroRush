from django.conf import settings
from django.db import models
from django.contrib.auth import get_user_model
from django.utils import timezone
from django.db import transaction
from common.tasks import recalculate_mmr, send_mail_notification
import logging

logger = logging.getLogger(__name__)

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

    name = models.CharField(max_length=100)
    type = models.CharField(max_length=20, choices=TYPE_CHOICES)
    conditions = models.JSONField(default=dict)
    reward_diamonds = models.IntegerField(default=0)
    reward_souls = models.IntegerField(default=0)
    reward_gold = models.IntegerField(default=0)
    reward_keys = models.IntegerField(default=0)
    users_completed = models.ManyToManyField(User, related_name='completed_quests', blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    reset_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        indexes = [models.Index(fields=['type'])]

    def complete(self, user):
        '''
        Завершает квест для игрока: начисляет награды, добавляет в completed, update MMR async.
        '''
        try:
            if user in self.users_completed.all():
                logger.warning(f"User {user.id} already completed quest {self.id}")
                return False

            with transaction.atomic():
                user.diamonds += self.reward_diamonds
                user.souls += self.reward_souls
                user.gold += self.reward_gold
                user.keys += self.reward_keys
                
                update_fields = []
                if self.reward_diamonds > 0:
                    update_fields.append('diamonds')
                if self.reward_souls > 0:
                    update_fields.append('souls')
                if self.reward_gold > 0:
                    update_fields.append('gold')
                if self.reward_keys > 0:
                    update_fields.append('keys')
                
                user.save(update_fields=update_fields)
                self.users_completed.add(user)
                
                logger.info(f"Quest {self.id} completed by user {user.id}. Rewards: {self.reward_diamonds} diamonds, {self.reward_souls} souls, {self.reward_gold} gold, {self.reward_keys} keys")

            # Async уведомление и MMR
            try:
                send_mail_notification.delay(
                    user.id,
                    f"Квест '{self.name}' завершён! Награда: {self.reward_diamonds} алмазов + {self.reward_souls} душ",
                    "Награда за квест",  
                    "reward"             
                )
                logger.debug(f"Notification sent for quest completion to user {user.id}")
            except Exception as e:
                logger.error(f"Failed to send notification for user {user.id}: {str(e)}")

            recalculate_mmr.delay(user.id)
            return True

        except Exception as e:
            logger.error(f"Error completing quest {self.id} for user {user.id}: {str(e)}")
            return False

    def __str__(self):
        return f"{self.name} ({self.type})"

class Achievement(models.Model):
    """
    Достижения (например: пройти 100 волн, убить 1000 крипов, вступить в клан).
    """
    title = models.CharField(max_length=100)
    description = models.TextField(blank=True)
    points = models.PositiveIntegerField(default=10)

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
        unique_together = ("user", "achievement")

    def __str__(self):
        return f"{self.user} → {self.achievement}"