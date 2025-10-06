from django.db.models.signals import post_save
from django.dispatch import receiver
from .models import HeroLeaderboardEntry
from Characters.models import Character
from Progress.models import Progress
from common.tasks import recalculate_mmr
from Clans.models import ClanMember


@receiver(post_save, sender=Character)
def update_hero_leaderboard(sender, instance, **kwargs):
    """Обновить рейтинг героя при изменении характеристик"""
    power = HeroLeaderboardEntry.calculate_power(instance)
    HeroLeaderboardEntry.objects.update_or_create(
        user=instance.user,
        hero_name=instance.hero_name,
        defaults={'power': power}
    )

@receiver(post_save, sender=Progress)
def update_mmr_leaderboard(sender, instance, **kwargs):
    """Обновить MMR при прогрессе"""
    recalculate_mmr.delay(instance.user.id)  

@receiver(post_save, sender=ClanMember)  
def update_clan_leaderboard(sender, instance, **kwargs):
    """Обновить рейтинг клана при изменении состава"""
    from common.tasks import update_clan_rank
    update_clan_rank.delay(instance.clan.id)