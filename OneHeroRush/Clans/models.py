# clans/models.py
from django.db import models
from django.conf import settings

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
        total = sum([m.user.mmr for m in self.members.select_related("user")])
        self.total_mmr = total
        self.members_count = self.members.count()
        self.save(update_fields=["total_mmr", "members_count"])

    def __str__(self):
        return self.name


class ClanMember(models.Model):
    clan = models.ForeignKey(Clan, on_delete=models.CASCADE, related_name="members")
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name="clan")
    joined_at = models.DateTimeField(auto_now_add=True)
    is_officer = models.BooleanField(default=False)  # можно вводить роли внутри клана

    def __str__(self):
        return f"{self.user.username} in {self.clan.name}"
