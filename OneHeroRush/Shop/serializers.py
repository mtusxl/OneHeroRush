# shop/serializers.py
from rest_framework import serializers
from .models import Product, Purchase, PromoCode

class ProductSerializer(serializers.ModelSerializer):
    class Meta:
        model = Product
        fields = ["key", "title", "description", "product_type", "price_cents", "currency", "meta"]

class PurchaseCreateSerializer(serializers.Serializer):
    product_key = serializers.CharField()
    # если покупка из баланса
    use_wallet = serializers.BooleanField(default=False)
    idempotency_key = serializers.CharField(required=False, allow_blank=True)
    # дополнительные поля (platform, promo_code)
    promo_code = serializers.CharField(required=False, allow_blank=True)

class RedeemSerializer(serializers.Serializer):
    code = serializers.CharField()
