import logging
from rest_framework import status, generics
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated
from django.db import transaction
from django.core.exceptions import ObjectDoesNotExist

from .models import Clan, ClanMember
from .serializers import ClanSerializer, ClanDetailSerializer
from common.tasks import recalculate_mmr

logger = logging.getLogger(__name__)

class ClanCreateView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        try:
            user = request.user
            logger.info(f"Clan creation request from user: {user.username}")
            
            name = request.data.get("name", "").strip()
            description = request.data.get("description", "").strip()

            # Валидация входных данных
            if not name:
                logger.warning(f"Empty clan name from user {user.username}")
                return Response({"error": "Название клана обязательно"}, status=status.HTTP_400_BAD_REQUEST)

            if hasattr(user, "clan"):
                logger.warning(f"User {user.username} already in clan {user.clan.clan.name}")
                return Response({"error": "Вы уже состоите в клане"}, status=status.HTTP_400_BAD_REQUEST)

            # Проверка уникальности названия
            if Clan.objects.filter(name__iexact=name).exists():
                logger.warning(f"Clan name already exists: {name}")
                return Response({"error": "Клан с таким названием уже существует"}, status=status.HTTP_400_BAD_REQUEST)

            with transaction.atomic():
                clan = Clan.objects.create(
                    name=name, 
                    description=description, 
                    leader=user
                )
                ClanMember.objects.create(clan=clan, user=user)
                
            logger.info(f"Clan created successfully: {name} by {user.username}")
            return Response(ClanSerializer(clan).data, status=status.HTTP_201_CREATED)

        except Exception as e:
            logger.error(f"Error creating clan for user {request.user.username}: {str(e)}")
            return Response(
                {"error": "Ошибка при создании клана"}, 
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class ClanJoinView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        try:
            user = request.user
            clan_id = request.data.get("clan_id")
            
            logger.info(f"Clan join request: user={user.username}, clan_id={clan_id}")

            if not clan_id:
                logger.warning(f"Missing clan_id from user {user.username}")
                return Response({"error": "ID клана обязательно"}, status=status.HTTP_400_BAD_REQUEST)

            if hasattr(user, "clan"):
                logger.warning(f"User {user.username} already in clan {user.clan.clan.name}")
                return Response({"error": "Вы уже в клане"}, status=status.HTTP_400_BAD_REQUEST)

            try:
                clan = Clan.objects.get(id=clan_id)
                logger.debug(f"Clan found: {clan.name}")
            except Clan.DoesNotExist:
                logger.warning(f"Clan not found: {clan_id}")
                return Response({"error": "Клан не найден"}, status=status.HTTP_404_NOT_FOUND)

            with transaction.atomic():
                ClanMember.objects.create(clan=clan, user=user)
                clan.members_count = clan.members.count()
                clan.save(update_fields=["members_count"])

            logger.info(f"User {user.username} joined clan {clan.name}")
            return Response({"success": f"Вы вступили в {clan.name}"})

        except Exception as e:
            logger.error(f"Error joining clan for user {request.user.username}: {str(e)}")
            return Response(
                {"error": "Ошибка при вступлении в клан"}, 
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class ClanLeaveView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        try:
            user = request.user
            logger.info(f"Clan leave request from user: {user.username}")

            try:
                clan_member = user.clan
                clan = clan_member.clan
                logger.debug(f"User clan found: {clan.name}")
            except ClanMember.DoesNotExist:
                logger.warning(f"User {user.username} not in any clan")
                return Response({"error": "Вы не состоите в клане"}, status=status.HTTP_400_BAD_REQUEST)

            with transaction.atomic():
                clan_member.delete()
                logger.info(f"ClanMember deleted: {user.username} from {clan.name}")

                # если лидер вышел → передача лидерства или удаление клана
                if clan.leader == user:
                    logger.warning(f"Clan leader leaving: {user.username} from {clan.name}")
                    
                    if clan.members.exists():
                        new_leader = clan.members.first().user
                        clan.leader = new_leader
                        clan.save(update_fields=["leader"])
                        logger.info(f"Leadership transferred to {new_leader.username}")
                    else:
                        clan.delete()
                        logger.info(f"Clan deleted (no members left): {clan.name}")
                        return Response({"success": "Клан распался"}, status=status.HTTP_200_OK)

                # Обновляем счетчик членов
                clan.members_count = clan.members.count()
                clan.save(update_fields=["members_count"])
                logger.debug(f"Clan members count updated: {clan.members_count}")

            return Response({"success": f"Вы покинули {clan.name}"}, status=status.HTTP_200_OK)

        except Exception as e:
            logger.error(f"Error leaving clan for user {request.user.username}: {str(e)}")
            return Response(
                {"error": "Ошибка при выходе из клана"}, 
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class ClanDetailView(generics.RetrieveAPIView):
    queryset = Clan.objects.all()
    serializer_class = ClanDetailSerializer
    permission_classes = [IsAuthenticated]

    def retrieve(self, request, *args, **kwargs):
        try:
            clan_id = kwargs.get('pk')
            logger.info(f"Clan details request: clan_id={clan_id}, user={request.user.username}")
            
            response = super().retrieve(request, *args, **kwargs)
            
            logger.debug(f"Clan details retrieved: {clan_id}")
            return response
            
        except Exception as e:
            logger.error(f"Error retrieving clan details {kwargs.get('pk')}: {str(e)}")
            return Response(
                {"error": "Ошибка при получении информации о клане"}, 
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class ClanRankingView(generics.ListAPIView):
    queryset = Clan.objects.order_by("-total_mmr")[:50]
    serializer_class = ClanSerializer
    permission_classes = [IsAuthenticated]

    def list(self, request, *args, **kwargs):
        try:
            logger.info(f"Clan ranking request from user: {request.user.username}")
            
            response = super().list(request, *args, **kwargs)
            
            logger.info(f"Clan ranking returned {len(response.data)} clans")
            return response
            
        except Exception as e:
            logger.error(f"Error retrieving clan ranking: {str(e)}")
            return Response(
                {"error": "Ошибка при получении рейтинга кланов"}, 
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )