# clans/views.py
from rest_framework import status, generics
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated
from django.db import transaction

from .models import Clan, ClanMember
from .serializers import ClanSerializer, ClanDetailSerializer
from common.tasks import recalculate_mmr



class ClanCreateView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        name = request.data.get("name")
        description = request.data.get("description", "")

        if hasattr(request.user, "clan"):
            return Response({"error": "Вы уже состоите в клане"}, status=400)

        with transaction.atomic():
            clan = Clan.objects.create(name=name, description=description, leader=request.user)
            ClanMember.objects.create(clan=clan, user=request.user)
        return Response(ClanSerializer(clan).data, status=201)


class ClanJoinView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        clan_id = request.data.get("clan_id")
        if hasattr(request.user, "clan"):
            return Response({"error": "Вы уже в клане"}, status=400)

        try:
            clan = Clan.objects.get(id=clan_id)
        except Clan.DoesNotExist:
            return Response({"error": "Клан не найден"}, status=404)

        with transaction.atomic():
            ClanMember.objects.create(clan=clan, user=request.user)
            clan.members_count = clan.members.count()
            clan.save(update_fields=["members_count"])

        return Response({"success": f"Вы вступили в {clan.name}"})


# clans/views.py
class ClanLeaveView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        try:
            clan_member = request.user.clan
            clan = clan_member.clan

            with transaction.atomic():
                clan_member.delete()

                # если лидер вышел → можно либо передать лидерство, либо удалить клан
                if clan.leader == request.user:
                    if clan.members.exists():
                        # новый лидер = первый член клана
                        new_leader = clan.members.first().user
                        clan.leader = new_leader
                    else:
                        clan.delete()
                        return Response({"success": "Клан распался"}, status=200)

            return Response({"success": f"Вы покинули {clan.name}"}, status=200)
        except ClanMember.DoesNotExist:
            return Response({"error": "Вы не состоите в клане"}, status=400)


class ClanDetailView(generics.RetrieveAPIView):
    queryset = Clan.objects.all()
    serializer_class = ClanDetailSerializer
    permission_classes = [IsAuthenticated]


class ClanRankingView(generics.ListAPIView):
    queryset = Clan.objects.order_by("-total_mmr")[:50]  # топ-50
    serializer_class = ClanSerializer
    permission_classes = [IsAuthenticated]
