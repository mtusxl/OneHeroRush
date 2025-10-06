from django.db import models
from django.conf import settings
from django.db.models import Window, F
from django.db.models.functions import Rank

class LeaderboardEntry(models.Model):
    """Глобальный рейтинг игроков (MMR)"""
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    mmr = models.IntegerField(default=0)

    def __str__(self):
        return f"{self.user.username} - {self.mmr}"

    @classmethod
    def get_ranked(cls):
        """Вернуть queryset с вычисленным местом (rank)"""
        return cls.objects.annotate(
            rank=Window(
                expression=Rank(),
                order_by=F("mmr").desc()
            )
        )


class HeroLeaderboardEntry(models.Model):
    """Рейтинг по героям"""
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    hero_name = models.CharField(max_length=100)
    power = models.IntegerField(default=0)

    class Meta:
        unique_together = ("user", "hero_name")

    def __str__(self):
        return f"{self.hero_name}: {self.user.username} - {self.power}"

    @classmethod
    def get_ranked(cls, hero=None):
        """Вернуть рейтинг по героям с местами"""
        qs = cls.objects.annotate(
            rank=Window(
                expression=Rank(),
                order_by=F("power").desc()
            )
        )
        if hero:
            qs = qs.filter(hero_name=hero)
        return qs


class ClanLeaderboardEntry(models.Model):
    """Рейтинг кланов"""
    clan = models.OneToOneField("Clans.Clan", on_delete=models.CASCADE)  # у тебя есть модель клана
    points = models.IntegerField(default=0)

    def __str__(self):
        return f"{self.clan.name} - {self.points}"

    @classmethod
    def get_ranked(cls):
        """Вернуть рейтинг кланов с местами"""
        return cls.objects.annotate(
            rank=Window(
                expression=Rank(),
                order_by=F("points").desc()
            )
        )
