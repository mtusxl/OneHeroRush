# views.py
import logging
from rest_framework import generics
from rest_framework.response import Response
from rest_framework import status
from .models import LeaderboardEntry, HeroLeaderboardEntry, ClanLeaderboardEntry
from .serializers import LeaderboardSerializer, HeroLeaderboardSerializer, ClanLeaderboardSerializer

logger = logging.getLogger(__name__)

class GlobalLeaderboardView(generics.ListAPIView):
    serializer_class = LeaderboardSerializer

    def get_queryset(self):
        try:
            logger.info(f"Global leaderboard request from user")
            queryset = LeaderboardEntry.objects.select_related("user").order_by("-mmr")[:100]
            logger.debug(f"Returning {queryset.count()} global leaderboard entries")
            return queryset
        except Exception as e:
            logger.error(f"Error getting global leaderboard: {str(e)}")
            return LeaderboardEntry.objects.none()


class HeroLeaderboardView(generics.ListAPIView):
    serializer_class = HeroLeaderboardSerializer

    def get_queryset(self):
        try:
            hero_name = self.request.query_params.get("hero")
            logger.info(f"Hero leaderboard request: hero={hero_name}")
            
            qs = HeroLeaderboardEntry.get_ranked(hero=hero_name)
            result = qs[:100]
            logger.debug(f"Returning {result.count()} hero leaderboard entries for {hero_name}")
            return result
        except Exception as e:
            logger.error(f"Error getting hero leaderboard for {hero_name}: {str(e)}")
            return HeroLeaderboardEntry.objects.none()


class ClanLeaderboardView(generics.ListAPIView):
    serializer_class = ClanLeaderboardSerializer

    def get_queryset(self):
        try:
            logger.info(f"Clan leaderboard request")
            queryset = ClanLeaderboardEntry.get_ranked()[:100]
            logger.debug(f"Returning {queryset.count()} clan leaderboard entries")
            return queryset
        except Exception as e:
            logger.error(f"Error getting clan leaderboard: {str(e)}")
            return ClanLeaderboardEntry.objects.none()