# from datetime import timezone
from celery import shared_task
from django.db import transaction
from django.db.models import Sum
# from django.contrib.auth import get_user_model
from Clans.models import Clan, ClanMember
# # from mail.models import Mail
# # from channels.layers import get_channel_layer
# from asgiref.sync import async_to_sync

# User = get_user_model()

@shared_task
def recalculate_mmr(user_id):
    """
    Пересчёт MMR игрока:
    - волны (прогресс)
    - достижения
    - мощь героев
    """
    from Users.models import User

    user = User.objects.get(id=user_id)

    waves_completed = user.progress.waves_completed if hasattr(user, "progress") else 0
    achievements = sum(ua.achievement.points for ua in user.achievements.all())
    total_power = sum(char.compute_power() for char in user.characters.all())

    user.mmr = waves_completed + achievements + total_power
    user.save(update_fields=["mmr"])

    # обновляем рейтинг клана, если пользователь состоит в нём
    try:
        clan_member = ClanMember.objects.select_related('clan').get(user=user)
        clan_member.clan.recalc_total_mmr()
    except ClanMember.DoesNotExist:
        pass


      

@shared_task
def update_clan_rank(clan_id):
    '''
    Асинхронно обновляет ранг клана (сумма MMR членов), лимит участников (30 + бонус).
    '''
    clan = Clan.objects.get(id=clan_id)
    with transaction.atomic():
        total_mmr = Clan.objects.filter(id=clan_id).annotate(total=Sum('members__mmr')).values('total')[0]['total'] or 0
        clan.rank = total_mmr
        clan.max_members = 30 + (clan.rank // 1000)
        clan.save(update_fields=['rank', 'max_members'])

# @shared_task
# def send_mail_notification(user_id, message):
#     '''
#     Асинхронно создаёт письмо в Mail и отправляет WS-уведомление для реального времени.
#     '''
#     user = User.objects.get(id=user_id)
#     with transaction.atomic():
#         Mail.objects.create(user=user, content=message, is_read=False)

#     channel_layer = get_channel_layer()
#     async_to_sync(channel_layer.group_send)(
#         f"user_{user_id}",
#         {"type": "notification", "message": message}
#    )

