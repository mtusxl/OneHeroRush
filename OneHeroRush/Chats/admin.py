from django.contrib import admin
from Chats.models import ChatMessage

@admin.register(ChatMessage)
class ChatMessageAdmin(admin.ModelAdmin):
    list_display = ('user', 'room', 'truncated_content', 'created_at')
    list_filter = ('room', 'created_at')
    search_fields = ('user__username', 'content', 'room')
    readonly_fields = ('created_at',)
    ordering = ('-created_at',)
    
    def truncated_content(self, obj):
        return obj.content[:50] + "..." if len(obj.content) > 50 else obj.content
    truncated_content.short_description = 'Сообщение'