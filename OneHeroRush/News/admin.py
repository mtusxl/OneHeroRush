from django.contrib import admin
from .models import MailTask, MailTemplate


class MailTaskInline(admin.TabularInline):
    model = MailTask
    extra = 0
    readonly_fields = ('status', 'created_at')

@admin.register(MailTemplate)
class MailTemplateAdmin(admin.ModelAdmin):
    list_display = ('name', 'mail_type', 'created_at')
    list_filter = ('mail_type', 'created_at')
    search_fields = ('name', 'subject', 'body')
    inlines = [MailTaskInline]
    readonly_fields = ('created_at',)

@admin.register(MailTask)
class MailTaskAdmin(admin.ModelAdmin):
    list_display = ('template', 'status', 'target_count', 'created_by', 'created_at')
    list_filter = ('status', 'created_at')
    search_fields = ('template__name', 'created_by__username')
    readonly_fields = ('created_at', 'completed_at')