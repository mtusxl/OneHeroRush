from django.contrib import admin
from Leaderboard.models import LeaderboardEntry, HeroLeaderboardEntry, ClanLeaderboardEntry


@admin.register(LeaderboardEntry)
class LeaderboardEntryAdmin(admin.ModelAdmin):
    list_display = ('user', 'mmr')
    list_filter = ('mmr',)
    search_fields = ('user__username',)
    ordering = ('-mmr',)

@admin.register(HeroLeaderboardEntry)
class HeroLeaderboardEntryAdmin(admin.ModelAdmin):
    list_display = ('hero_name', 'user', 'power')
    list_filter = ('hero_name',)
    search_fields = ('user__username', 'hero_name')
    ordering = ('-power',)

@admin.register(ClanLeaderboardEntry)
class ClanLeaderboardEntryAdmin(admin.ModelAdmin):
    list_display = ('clan', 'points')
    list_filter = ('points',)
    search_fields = ('clan__name',)
    ordering = ('-points',)