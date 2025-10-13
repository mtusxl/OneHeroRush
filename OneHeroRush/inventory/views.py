import logging
from django.core.exceptions import ValidationError
from rest_framework import viewsets, status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.decorators import action
from django.db import transaction
from .models import Item, Chest
from .serializers import ItemSerializer, ChestSerializer, OpenChestSerializer
from common.tasks import recalculate_mmr  


from django.utils.decorators import method_decorator
from django.views.decorators.cache import cache_page

from rest_framework.throttling import UserRateThrottle

from .tasks import bulk_open_chest



logger = logging.getLogger(__name__)


class BulkOpenThrottle(UserRateThrottle):
    rate = '10/minute'


class ItemViewSet(viewsets.ModelViewSet):
    serializer_class = ItemSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        # Оптимизация: select_related для user, только нужные поля
        return Item.objects.filter(user=self.request.user).select_related('user').only(
            'id', 'name', 'level', 'stats', 'rarity_multiplier', 'is_equipped'
        )
    @method_decorator(cache_page(60 * 5))
    @action(detail=True, methods=["post"])
    def equip(self, request, pk=None):
        """
        Экипировать предмет.
        """
        try:
            with transaction.atomic():
                item = self.get_object()
                if item.user_id != request.user.id:
                    return Response(
                        {"error": "You don't own this item"},
                        status=status.HTTP_403_FORBIDDEN
                    )

                if item.is_equipped:
                    return Response(
                        {"error": "Item already equipped"},
                        status=status.HTTP_400_BAD_REQUEST
                    )
                Item.objects.filter(
                    user=request.user, 
                    name=item.name,
                    is_equipped=True
                ).update(is_equipped=False)

                Item.objects.filter(id=item.id).update(is_equipped=True)
            recalculate_mmr.delay(request.user.id)

            return Response(
                {"message": f"Equipped {item.name}"}, 
                status=status.HTTP_200_OK
            )

        except Item.DoesNotExist:
            return Response(
                {"error": "Item not found"}, 
                status=status.HTTP_404_NOT_FOUND
            )
        

    @method_decorator(cache_page(60 * 5))
    @action(detail=True, methods=["post"])
    def sell(self, request, pk=None):
        """
        Продать предмет.
        """
        item = self.get_object()
        gold_reward = 100
        request.user.gold += gold_reward
        request.user.save(update_fields=["gold"])
        item.delete()

        recalculate_mmr.delay(request.user.id)

        return Response(
            {"message": f"Sold {item.name} for {gold_reward} gold",
             "gold": request.user.gold},
            status=status.HTTP_200_OK
        )




class ChestViewSet(viewsets.ModelViewSet):
    '''
    ViewSet для сундуков: list, open (rand item, auto 1-20x).
    '''
    serializer_class = ChestSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return Chest.objects.filter(user=self.request.user)

    @method_decorator(cache_page(60 * 5))
    @action(detail=True, methods=["post"])
    def open(self, request, pk=None):
        """
        Открыть сундук (1 штуку).
        """
        chest = self.get_object()
        try:
            item = chest.open()  
        except ValidationError as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)

    
        recalculate_mmr.delay(request.user.id)

        return Response(
            {"message": f"Chest opened, got {item.name}", "item_id": item.id},
            status=status.HTTP_200_OK,
        )
    

    @method_decorator(cache_page(60 * 5))
    @action(detail=False, methods=['post'], url_path='bulk_open')
    def bulk_open(self, request):
        """
        POST /chest/bulk_open/
        Открывает несколько сундуков асинхронно через Celery.
        """
        user = request.user
        count = request.data.get('count')

        logger.info(f"[ChestViewSet.bulk_open] User={user.username} initiated bulk open with count={count}")

        # Проверка наличия count
        if not count:
            logger.warning(f"[ChestViewSet.bulk_open] Missing 'count' param | User={user.username}")
            return Response({"detail": "Parameter 'count' is required"}, status=status.HTTP_400_BAD_REQUEST)

        try:
            count = int(count)
        except ValueError:
            logger.warning(f"[ChestViewSet.bulk_open] Invalid 'count' value={count} | User={user.username}")
            return Response({"detail": "'count' must be an integer"}, status=status.HTTP_400_BAD_REQUEST)

        if count <= 0:
            logger.warning(f"[ChestViewSet.bulk_open] Invalid count <= 0 | User={user.username}")
            return Response({"detail": "'count' must be greater than 0"}, status=status.HTTP_400_BAD_REQUEST)

        # Проверка ресурсов игрока
        if user.keys < count:
            logger.warning(f"[ChestViewSet.bulk_open] Not enough keys: has={user.keys}, needs={count} | User={user.username}")
            return Response({"detail": "Not enough keys"}, status=status.HTTP_400_BAD_REQUEST)

        user_chest_count = Chest.objects.filter(user=user).count()
        if user_chest_count < count:
            logger.warning(f"[ChestViewSet.bulk_open] Not enough chests: has={user_chest_count}, needs={count} | User={user.username}")
            return Response({"detail": "Not enough chests"}, status=status.HTTP_400_BAD_REQUEST)

        try:
            task = bulk_open_chest.delay(user.id, count)
            logger.info(f"[ChestViewSet.bulk_open] Celery task started: task_id={task.id} | User={user.username}, count={count}")

            return Response(
                {"status": "processing", "task_id": task.id},
                status=status.HTTP_202_ACCEPTED
            )

        except Exception as e:
            logger.exception(f"[ChestViewSet.bulk_open] Failed to start bulk_open task | User={user.username} | Error: {str(e)}")
            return Response({"detail": "Failed to start task"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

