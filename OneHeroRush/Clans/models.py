import logging
from django.db import models
from django.conf import settings

logger = logging.getLogger(__name__)
User = settings.AUTH_USER_MODEL

class Clan(models.Model):
    name = models.CharField(max_length=50, unique=True) 
    description = models.TextField(blank=True)          
    leader = models.ForeignKey(
        User, on_delete=models.SET_NULL,
        null=True, related_name="led_clans"
    )  
    members_count = models.PositiveIntegerField(default=1) 
    total_mmr = models.PositiveIntegerField(default=0) 
    created_at = models.DateTimeField(auto_now_add=True)

    def recalc_total_mmr(self):
        """Пересчитать суммарный рейтинг клана по всем членам"""
        try:
            logger.debug(f"Recalculating MMR for clan: {self.name} (ID: {self.id})")
            
            total = sum([m.user.mmr for m in self.members.select_related("user")])
            old_mmr = self.total_mmr
            old_count = self.members_count
            
            self.total_mmr = total
            self.members_count = self.members.count()
            self.save(update_fields=["total_mmr", "members_count"])
            
            logger.info(f"Clan MMR recalculated: {self.name} - MMR: {old_mmr}→{total}, Members: {old_count}→{self.members_count}")
            
        except Exception as e:
            logger.error(f"Error recalculating MMR for clan {self.id}: {str(e)}")
            raise

    def save(self, *args, **kwargs):
        try:
            is_new = not self.pk
            logger.debug(f"Saving clan: {self.name}, new={is_new}")
            
            super().save(*args, **kwargs)
            
            logger.info(f"Clan saved successfully: {self.name} (ID: {self.pk})")
            
        except Exception as e:
            logger.error(f"Error saving clan {self.name}: {str(e)}")
            raise

    def delete(self, *args, **kwargs):
        try:
            logger.warning(f"Deleting clan: {self.name} (ID: {self.id})")
            
            super().delete(*args, **kwargs)
            
            logger.info(f"Clan deleted: {self.name}")
            
        except Exception as e:
            logger.error(f"Error deleting clan {self.id}: {str(e)}")
            raise

    def __str__(self):
        return self.name


class ClanMember(models.Model):
    clan = models.ForeignKey(Clan, on_delete=models.CASCADE, related_name="members")
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name="clan")
    joined_at = models.DateTimeField(auto_now_add=True)
    is_officer = models.BooleanField(default=False)

    def save(self, *args, **kwargs):
        try:
            is_new = not self.pk
            logger.debug(f"Saving ClanMember: user={self.user.username}, clan={self.clan.name}, new={is_new}")
            
            super().save(*args, **kwargs)
            
            logger.info(f"ClanMember saved: {self.user.username} → {self.clan.name}")
            
        except Exception as e:
            logger.error(f"Error saving ClanMember {self.user.username} to {self.clan.name}: {str(e)}")
            raise

    def delete(self, *args, **kwargs):
        try:
            logger.info(f"Deleting ClanMember: {self.user.username} from {self.clan.name}")
            
            super().delete(*args, **kwargs)
            
            logger.info(f"ClanMember deleted: {self.user.username} from {self.clan.name}")
            
        except Exception as e:
            logger.error(f"Error deleting ClanMember {self.pk}: {str(e)}")
            raise

    def __str__(self):
        return f"{self.user.username} in {self.clan.name}"