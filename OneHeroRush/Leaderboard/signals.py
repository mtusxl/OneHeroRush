# signals.py
import logging
from django.db.models.signals import post_save
from django.dispatch import receiver
from .models import HeroLeaderboardEntry
from Characters.models import Character
from Progress.models import Progress
from common.tasks import recalculate_mmr
from Clans.models import ClanMember

logger = logging.getLogger(__name__)

@receiver(post_save, sender=Character)
def update_hero_leaderboard(sender, instance, **kwargs):
    """Обновить рейтинг героя при изменении характеристик"""
    try:
        logger.debug(f"Updating hero leaderboard for {instance.hero_name}, user {instance.user.username}")
        
        power = instance.compute_power()
        HeroLeaderboardEntry.objects.update_or_create(
            user=instance.user,
            hero_name=instance.hero_name,
            defaults={'power': power}
        )
        
        logger.info(f"Hero leaderboard updated: {instance.hero_name} - {power}")
        
    except Exception as e:
        logger.error(f"Error updating hero leaderboard for character {instance.id}: {str(e)}")

@receiver(post_save, sender=Progress)
def update_mmr_leaderboard(sender, instance, **kwargs):
    """Обновить MMR при прогрессе"""
    try:
        logger.debug(f"MMR update triggered by progress for user {instance.user.username}")
        recalculate_mmr.delay(instance.user.id)
    except Exception as e:
        logger.error(f"Error triggering MMR update for progress {instance.id}: {str(e)}")

@receiver(post_save, sender=ClanMember)  
def update_clan_leaderboard(sender, instance, **kwargs):
    """Обновить рейтинг клана при изменении состава"""
    try:
        logger.debug(f"Clan leaderboard update for clan {instance.clan.name}")
        from common.tasks import update_clan_rank
        update_clan_rank.delay(instance.clan.id)
    except Exception as e:
        logger.error(f"Error updating clan leaderboard for clan {instance.clan.id}: {str(e)}")