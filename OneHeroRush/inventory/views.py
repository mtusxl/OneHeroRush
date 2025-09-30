from rest_framework import viewsets, status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.decorators import action
from django.db import transaction
from .models import Item, Chest
from .serializers import ItemSerializer, ChestSerializer, OpenChestSerializer
from common.tasks import recalculate_mmr  

from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework import status

class ItemViewSet(viewsets.ModelViewSet):
    serializer_class = ItemSerializer

    def get_queryset(self):
        return Item.objects.filter(user=self.request.user)

    @action(detail=True, methods=["post"])
    def equip(self, request, pk=None):
        """
        Экипировать предмет.
        """
        item = self.get_object()
        if item.is_equipped:
            return Response({"error": "Item already equipped"},
                            status=status.HTTP_400_BAD_REQUEST)

        # снимаем все предметы того же типа
        Item.objects.filter(user=request.user, name=item.name).update(is_equipped=False)
        item.is_equipped = True
        item.save(update_fields=["is_equipped"])

        recalculate_mmr.delay(request.user.id)

        return Response({"message": f"Equipped {item.name}"}, status=status.HTTP_200_OK)

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