from django.contrib import admin
from Messages.models import Messages


@admin.register(Messages)
class MessagesAdmin(admin.ModelAdmin):
    list_display = ('user', 'subject', 'message_type', 'is_read', 'created_at')
    list_filter = ('message_type', 'is_read', 'created_at')
    search_fields = ('user__username', 'subject', 'body')
    readonly_fields = ('created_at',)