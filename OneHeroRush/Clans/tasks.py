from celery import shared_task
from Users.models import User
from Clans.models import ClanMember


@shared_task
def recalculate_mmr(user_id):
    user = User.objects.get(id=user_id)

    new_mmr = user.gold + user.diamonds + user.items.filter(is_equipped=True).count() * 10
    user.mmr = new_mmr
    user.save(update_fields=["mmr"])

    # если игрок состоит в клане → обновляем рейтинг клана
    try:
        clan_member = user.clan 
        clan = clan_member.clan  
        clan.recalc_total_mmr()
    except ClanMember.DoesNotExist:
        pass  
