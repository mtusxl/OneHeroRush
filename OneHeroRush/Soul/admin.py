from django.contrib import admin
from .models import Soul, PlayerSoul, SummonLevel

@admin.register(Soul)
class SoulAdmin(admin.ModelAdmin):
    list_display = ('character', 'rarity', 'level', 'multiplier')
    list_filter = ('rarity', 'level')
    search_fields = ('character__hero_name',)

@admin.register(PlayerSoul)
class PlayerSoulAdmin(admin.ModelAdmin):
    list_display = ('user', 'soul', 'equipped_to_character', 'summon_count')
    list_filter = ('summon_count',)
    search_fields = ('user__username', 'soul__character__hero_name')

@admin.register(SummonLevel)
class SummonLevelAdmin(admin.ModelAdmin):
    list_display = ('user', 'level', 'experience')
    search_fields = ('user__username',)