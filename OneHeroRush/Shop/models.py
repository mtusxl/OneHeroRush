# Примерные модели
from django.db import models
from django.conf import settings
from django.utils import timezone

User = settings.AUTH_USER_MODEL

class Product(models.Model):
    """
    Товар в магазине: валюта, герой, питомец, наборы и т.д.
    """
    TYPE_CHOICES = [
        ("currency", "Currency"),
        ("hero", "Hero"),
        ("pet", "Pet"),
        ("bundle", "Bundle"),
    ]
    key = models.CharField(max_length=100, unique=True)  # internal id e.g. "coins_1000", "hero_pudge"
    title = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    product_type = models.CharField(max_length=32, choices=TYPE_CHOICES)
    price_cents = models.PositiveIntegerField()  # цена в центах/копейках (серверная)
    currency = models.CharField(max_length=8, default="USD")  # валюта для платежей
    meta = models.JSONField(default=dict, blank=True)  # дополнительные данные (что выдаём)
    active = models.BooleanField(default=True)
    #image = models.ImageField(upload_to="shop/", blank=True, null=True)

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        indexes = [
            models.Index(fields=["product_type"]),
            models.Index(fields=["key"]),
        ]

class Wallet(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name="wallet")
    balance_cents = models.BigIntegerField(default=0)  # внутренняя валюта в центах
    updated_at = models.DateTimeField(auto_now=True)

class Purchase(models.Model):
    """
    Каждая попытка покупки — запись с audit trail.
    payment_provider — e.g. "stripe", "paypal", "internal"
    status: PENDING -> COMPLETED -> FAILED
    idempotency_key: optional header from client
    """
    STATUS_CHOICES = [
        ("PENDING", "Pending"),
        ("COMPLETED", "Completed"),
        ("FAILED", "Failed"),
    ]
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="purchases")
    product = models.ForeignKey(Product, on_delete=models.PROTECT)
    price_cents = models.PositiveIntegerField()
    currency = models.CharField(max_length=8)
    created_at = models.DateTimeField(auto_now_add=True)
    status = models.CharField(max_length=16, choices=STATUS_CHOICES, default="PENDING")
    payment_provider = models.CharField(max_length=64, null=True, blank=True)
    provider_payment_id = models.CharField(max_length=200, null=True, blank=True)
    idempotency_key = models.CharField(max_length=255, null=True, blank=True, db_index=True)
    meta = models.JSONField(default=dict, blank=True)  # debug / provider payload

    class Meta:
        indexes = [
            models.Index(fields=["status"]),
            models.Index(fields=["idempotency_key"]),
        ]

class PromoCode(models.Model):
    code = models.CharField(max_length=64, unique=True)
    # тип награды: flat cents, percent, product_giveaway, currency_giveaway
    TYPE_CHOICES = [("flat", "flat"), ("percent", "percent"), ("currency", "currency")]
    promo_type = models.CharField(max_length=16, choices=TYPE_CHOICES)
    value = models.IntegerField()  # in cents if flat, or percent if percent
    active = models.BooleanField(default=True)
    usage_limit = models.PositiveIntegerField(null=True, blank=True)  # None = unlimited
    used_count = models.PositiveIntegerField(default=0)
    expires_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
