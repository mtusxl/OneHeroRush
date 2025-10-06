from django.contrib import admin
from Shop.models import Product, Wallet, Purchase, PromoCode


@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = ('key', 'title', 'product_type', 'price_cents', 'currency', 'active')
    list_filter = ('product_type', 'currency', 'active', 'created_at')
    search_fields = ('key', 'title')
    readonly_fields = ('created_at',)

@admin.register(Wallet)
class WalletAdmin(admin.ModelAdmin):
    list_display = ('user', 'balance_cents', 'updated_at')
    search_fields = ('user__username',)
    readonly_fields = ('updated_at',)

@admin.register(Purchase)
class PurchaseAdmin(admin.ModelAdmin):
    list_display = ('user', 'product', 'price_cents', 'status', 'created_at')
    list_filter = ('status', 'created_at')
    search_fields = ('user__username', 'product__title')
    readonly_fields = ('created_at',)

@admin.register(PromoCode)
class PromoCodeAdmin(admin.ModelAdmin):
    list_display = ('code', 'promo_type', 'value', 'active', 'usage_limit', 'used_count')
    list_filter = ('promo_type', 'active', 'created_at')
    search_fields = ('code',)