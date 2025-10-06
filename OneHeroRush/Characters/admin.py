from django.contrib import admin
from Characters.models import Character



@admin.register(Character)
class CharacterAdmin(admin.ModelAdmin):
    list_display = ('user', 'hero_name', 'level', 'get_race', 'is_active', 'created_at')
    list_filter = ('hero_name', 'level', 'is_active', 'created_at')
    search_fields = ('user__username', 'hero_name')
    readonly_fields = ('created_at', 'stats', 'race_bonus')
    
    def get_race(self, obj):
        return obj.get_race()
    get_race.short_description = 'Раса'