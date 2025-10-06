from django.contrib import admin
from Clans.models import Clan, ClanMember


class ClanMemberInline(admin.TabularInline):
    model = ClanMember
    extra = 1

@admin.register(Clan)
class ClanAdmin(admin.ModelAdmin):
    list_display = ('name', 'leader', 'members_count', 'total_mmr', 'created_at')
    list_filter = ('created_at',)
    search_fields = ('name', 'leader__username')
    inlines = [ClanMemberInline]
    readonly_fields = ('created_at',)

@admin.register(ClanMember)
class ClanMemberAdmin(admin.ModelAdmin):
    list_display = ('user', 'clan', 'is_officer', 'joined_at')
    list_filter = ('clan', 'is_officer', 'joined_at')
    search_fields = ('user__username', 'clan__name')