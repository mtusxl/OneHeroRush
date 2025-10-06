from django.contrib import admin
from Progress.models import Progress


@admin.register(Progress)
class ProgressAdmin(admin.ModelAdmin):
    list_display = ('user', 'location', 'act', 'stage', 'wave', 'difficulty', 'last_online')
    list_filter = ('location', 'difficulty', 'last_online')
    search_fields = ('user__username',)
    readonly_fields = ('last_online',)