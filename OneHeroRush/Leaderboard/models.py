# models.py
import logging
from django.db import models
from django.conf import settings
from django.db.models import Window, F, Subquery, OuterRef
from django.db.models.functions import Rank, Coalesce

logger = logging.getLogger(__name__)

class LeaderboardEntry(models.Model):
    """Глобальный рейтинг игроков (MMR)"""
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, db_index=True)
    mmr = models.IntegerField(default=0, db_index=True)
    last_updated = models.DateTimeField(auto_now=True)

    class Meta:
        indexes = [
            models.Index(fields=['-mmr', 'user']),
        ]

    def __str__(self):
        return f"{self.user.username} - {self.mmr}"

    @classmethod
    def get_ranked(cls, limit=100, offset=0):
        """Вернуть рейтинг по героям с местами"""
        try:
            return cls.objects.select_related('user').annotate(
                rank=Window(
                    expression=Rank(),
                    order_by=F("mmr").desc()
                )
            ).order_by('-mmr')[offset:offset + limit]
        except Exception as e:
            logger.error(f"Error getting ranked leaderboard: {str(e)}")
            return cls.objects.none()



class HeroLeaderboardEntry(models.Model):
    """Рейтинг по героям"""
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, db_index=True)
    hero_name = models.CharField(max_length=100, db_index=True)
    power = models.IntegerField(default=0, db_index=True)
    last_updated = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ("user", "hero_name")
        indexes = [
            models.Index(fields=['hero_name', '-power']),
        ]

    def __str__(self):
        return f"{self.hero_name}: {self.user.username} - {self.power}"

    @classmethod
    def get_ranked(cls, hero=None, limit=100, offset=0):
        """Вернуть рейтинг по героям с местами"""
        try:
            qs = cls.objects.select_related('user')
            if hero:
                qs = qs.filter(hero_name=hero)
                
            return qs.annotate(
                rank=Window(
                    expression=Rank(),
                    order_by=F("power").desc()
                )
            ).order_by('-power')[offset:offset + limit]
        except Exception as e:
            logger.error(f"Error getting hero leaderboard for {hero}: {str(e)}")
            return cls.objects.none()


class ClanLeaderboardEntry(models.Model):
    """Рейтинг кланов"""
    clan = models.OneToOneField("Clans.Clan", on_delete=models.CASCADE, db_index=True)
    points = models.IntegerField(default=0, db_index=True)
    last_updated = models.DateTimeField(auto_now=True)

    class Meta:
        indexes = [
            models.Index(fields=['-points']),
        ]

    def __str__(self):
        return f"{self.clan.name} - {self.points}"

    @classmethod
    def get_ranked(cls, limit=100, offset=0):
        """Вернуть рейтинг кланов с местами"""
        try:
            return cls.objects.select_related('clan').annotate(
                rank=Window(
                    expression=Rank(),
                    order_by=F("points").desc()
                )
            ).order_by('-points')[offset:offset + limit]
        except Exception as e:
            logger.error(f"Error getting clan leaderboard: {str(e)}")
            return cls.objects.none()