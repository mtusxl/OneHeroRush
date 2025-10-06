from django.contrib import admin
from Quests.models import Quest, Achievement, UserAchievement


@admin.register(Quest)
class QuestAdmin(admin.ModelAdmin):
    list_display = ('name', 'type', 'reward_diamonds', 'reward_souls', 'created_at')
    list_filter = ('type', 'created_at')
    search_fields = ('name',)
    readonly_fields = ('created_at',)
    filter_horizontal = ('users_completed',)

@admin.register(Achievement)
class AchievementAdmin(admin.ModelAdmin):
    list_display = ('title', 'points')
    search_fields = ('title', 'description')

@admin.register(UserAchievement)
class UserAchievementAdmin(admin.ModelAdmin):
    list_display = ('user', 'achievement', 'earned_at')
    list_filter = ('earned_at',)
    search_fields = ('user__username', 'achievement__title')