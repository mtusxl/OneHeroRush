# Пример кода
import json
from django.views.decorators.csrf import csrf_exempt
from django.db import transaction
from django.http import HttpResponse, JsonResponse
from django.shortcuts import get_object_or_404
from .models import Purchase

@csrf_exempt
def provider_webhook(request):
    # validate signature — provider-specific (very important)
    payload = request.body
    sig = request.META.get("HTTP_X_SIGNATURE", "")
    # if not verify_signature(payload, sig):
    #    return HttpResponse(status=400)

    data = json.loads(payload)
    provider_payment_id = data.get("payment_id")
    status = data.get("status")  # e.g. "succeeded"
    purchase = get_object_or_404(Purchase, provider_payment_id=provider_payment_id)

    if status == "succeeded":
        with transaction.atomic():
            # re-fetch for update to prevent races
            p = Purchase.objects.select_for_update().get(pk=purchase.pk)
            if p.status == "COMPLETED":
                return JsonResponse({"ok": True})
            p.status = "COMPLETED"
            p.meta.update({"provider_payload": data})
            p.save(update_fields=["status", "meta"])

            # grant product
            grant_product(p.user, p.product, p)
        return JsonResponse({"ok": True})

    # handle failed/cancelled
    p.status = "FAILED"
    p.meta.update({"provider_payload": data})
    p.save(update_fields=["status", "meta"])
    return JsonResponse({"ok": True})

def grant_product(user, product, purchase):
    """
    Награждаем игрока: если product.product_type == "currency" -> пополнить Wallet.
    Если hero -> добавить запись UserHero и т.д.
    Важно: эта функция должна быть идемпотентной (проверка по purchase.id).
    """
    # пример для валюты
    if product.product_type == "currency":
        cents = product.meta.get("amount_cents", product.price_cents)
        # wallet, _ = Wallet.objects.get_or_create(user=user)
        # wallet.balance_cents += cents
        # wallet.save(update_fields=["balance_cents"])
    elif product.product_type == "hero":
        # добавить в user inventory
        #UserHero.objects.get_or_create(user=user, hero_key=product.key)
        pass

