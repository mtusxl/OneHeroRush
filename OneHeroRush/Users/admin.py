from django.contrib import admin
from Users.models import User, UserProfile
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
@admin.register(User)
class UserAdmin(BaseUserAdmin):
    list_display = ('username', 'gold', 'diamonds', 'souls', 'keys', 'mmr', 'is_active', 'created_at')
    list_filter = ('is_active', 'is_staff', 'is_superuser', 'created_at')
    search_fields = ('username',)
    ordering = ('-created_at',)
    fieldsets = (
        (None, {'fields': ('username', 'password')}),
        ('Игровая статистика', {'fields': ('gold', 'diamonds', 'souls', 'keys', 'soul_coupons', 'mmr')}),
        ('Лимиты', {'fields': ('max_heroes', 'purchased_heroes')}),
        ('Права', {'fields': ('is_active', 'is_staff', 'is_superuser', 'groups', 'user_permissions')}),
        ('Даты', {'fields': ('last_login', 'created_at')}),
    )
    readonly_fields = ('created_at',)

@admin.register(UserProfile)
class UserProfileAdmin(admin.ModelAdmin):
    list_display = ('user', 'active_pet')
    search_fields = ('user__username',)