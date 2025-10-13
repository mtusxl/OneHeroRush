import logging
from celery import shared_task
from django.core.exceptions import ObjectDoesNotExist
from Users.models import User
from Clans.models import ClanMember

logger = logging.getLogger(__name__)

@shared_task
def recalculate_mmr(user_id):
    try:
        logger.info(f"Starting MMR recalculation for user: {user_id}")
        
        user = User.objects.get(id=user_id)
        logger.debug(f"User found: {user.username}")

        new_mmr = user.gold + user.diamonds + user.items.filter(is_equipped=True).count() * 10
        old_mmr = user.mmr
        
        user.mmr = new_mmr
        user.save(update_fields=["mmr"])
        
        logger.info(f"MMR updated for user {user.username}: {old_mmr} → {new_mmr}")

        # если игрок состоит в клане → обновляем рейтинг клана
        try:
            clan_member = user.clan 
            clan = clan_member.clan  
            clan.recalc_total_mmr()
            logger.info(f"Clan MMR updated for {clan.name} due to user {user.username}")
            
        except ClanMember.DoesNotExist:
            logger.debug(f"User {user.username} is not in a clan, skipping clan MMR update")
        except Exception as e:
            logger.error(f"Error updating clan MMR for user {user.username}: {str(e)}")

    except User.DoesNotExist:
        logger.error(f"User not found for MMR recalculation: {user_id}")
    except Exception as e:
        logger.error(f"Error in MMR recalculation task for user {user_id}: {str(e)}")