# примерный код
from django.db import transaction
from django.shortcuts import get_object_or_404
from django.utils import timezone
from django.core.cache import cache
from rest_framework import generics, permissions, status
from rest_framework.views import APIView
from rest_framework.response import Response
from .models import Product, Wallet, Purchase, PromoCode
from .serializers import ProductSerializer, PurchaseCreateSerializer, RedeemSerializer
from django.conf import settings

# GET /shop/ - cached catalog
class ShopListView(generics.ListAPIView):
    permission_classes = [permissions.IsAuthenticated]
    serializer_class = ProductSerializer

    def get_queryset(self):
        return Product.objects.filter(active=True)

    def list(self, request, *args, **kwargs):
        cache_key = "shop:catalog"
        data = cache.get(cache_key)
        if data:
            return Response(data)
        qs = self.get_queryset()
        data = ProductSerializer(qs, many=True).data
        cache.set(cache_key, data, timeout=60)  # 60s TTL (tuneable)
        return Response(data)


# POST /shop/buy
class ShopBuyView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        serializer = PurchaseCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        product_key = serializer.validated_data["product_key"]
        use_wallet = serializer.validated_data.get("use_wallet", False)
        idempotency_key = serializer.validated_data.get("idempotency_key")
        promo_code = serializer.validated_data.get("promo_code")

        product = get_object_or_404(Product, key=product_key, active=True)

        # server-side price check
        price_cents = product.price_cents
        currency = product.currency

        # apply promo code if provided (simple example)
        if promo_code:
            try:
                promo = PromoCode.objects.get(code=promo_code, active=True)
                if promo.expires_at and promo.expires_at < timezone.now():
                    return Response({"error": "Promo expired"}, status=status.HTTP_400_BAD_REQUEST)
                if promo.promo_type == "flat":
                    price_cents = max(0, price_cents - promo.value)
                elif promo.promo_type == "percent":
                    price_cents = int(price_cents * (100 - promo.value) / 100)
                # usage limit check omitted for brevity
            except PromoCode.DoesNotExist:
                return Response({"error": "Invalid promo"}, status=status.HTTP_400_BAD_REQUEST)

        user = request.user

        # Idempotency: если есть уже Purchase с таким ключом и PENDING/COMPLETED — вернуть её
        if idempotency_key:
            existing = Purchase.objects.filter(user=user, idempotency_key=idempotency_key).order_by("-created_at").first()
            if existing:
                # return already existing record status
                return Response({
                    "purchase_id": existing.id,
                    "status": existing.status,
                })

        # Two flows:
        # 1) use_wallet => immediate internal purchase
        if use_wallet:
            # atomic wallet debit + grant item
            with transaction.atomic():
                wallet, _ = Wallet.objects.select_for_update().get_or_create(user=user)
                if wallet.balance_cents < price_cents:
                    return Response({"error": "Insufficient funds"}, status=status.HTTP_402_PAYMENT_REQUIRED)

                # debit
                wallet.balance_cents -= price_cents
                wallet.save(update_fields=["balance_cents"])

                # create purchase record
                purchase = Purchase.objects.create(
                    user=user, product=product, price_cents=price_cents,
                    currency=currency, status="COMPLETED", payment_provider="internal",
                    idempotency_key=idempotency_key or None
                )

                # grant product to user — implement grant_product()
                # grant_product(user, product, purchase)

                return Response({"purchase_id": purchase.id, "status": purchase.status})

        # 2) external payment: create PENDING purchase and return payment details
        # create purchase
        purchase = Purchase.objects.create(
            user=user, product=product, price_cents=price_cents,
            currency=currency, status="PENDING", payment_provider="external",
            idempotency_key=idempotency_key or None
        )

        # create payment intent with provider (placeholder)
        # Implement create_payment_intent(purchase) -> {provider_id, payment_url}
        #provider_payload = create_payment_intent(purchase)

        # save provider info
        #purchase.provider_payment_id = provider_payload.get("provider_id")
        #purchase.meta = provider_payload.get("meta", {})
        purchase.save(update_fields=["provider_payment_id", "meta"])

        # return payment instructions to client
        # return Response({
        #     "purchase_id": purchase.id,
        #     "payment": provider_payload
        # }, status=status.HTTP_201_CREATED)
