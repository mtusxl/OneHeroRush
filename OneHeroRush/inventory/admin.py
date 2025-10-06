from django.contrib import admin
from inventory.models import Item, Chest


@admin.register(Item)
class ItemAdmin(admin.ModelAdmin):
    list_display = ('name', 'user', 'level', 'rarity_multiplier', 'created_at')
    list_filter = ('name', 'rarity_multiplier', 'created_at')
    search_fields = ('user__username', 'name')
    readonly_fields = ('created_at', 'stats')

@admin.register(Chest)
class ChestAdmin(admin.ModelAdmin):
    list_display = ('user', 'level', 'created_at')
    list_filter = ('level', 'created_at')
    search_fields = ('user__username',)