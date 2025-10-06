from django.contrib import admin
from Pets.models import Pet, UserPet, UserSummonConfig


@admin.register(Pet)
class PetAdmin(admin.ModelAdmin):
    list_display = ('name', 'rarity', 'bonus_gold', 'bonus_damage', 'bonus_health')
    list_filter = ('rarity',)
    search_fields = ('name',)

@admin.register(UserPet)
class UserPetAdmin(admin.ModelAdmin):
    list_display = ('user', 'pet', 'level', 'is_selected', 'created_at')
    list_filter = ('is_selected', 'created_at')
    search_fields = ('user__username', 'pet__name')

@admin.register(UserSummonConfig)
class UserSummonConfigAdmin(admin.ModelAdmin):
    list_display = ('user', 'summon_level', 'summon_exp')
    search_fields = ('user__username',)