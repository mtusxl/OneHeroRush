from rest_framework import generics
from .models import LeaderboardEntry, HeroLeaderboardEntry, ClanLeaderboardEntry
from .serializers import LeaderboardSerializer, HeroLeaderboardSerializer, ClanLeaderboardSerializer

# Глобальный рейтинг
class GlobalLeaderboardView(generics.ListAPIView):
    serializer_class = LeaderboardSerializer

    def get_queryset(self):
        return LeaderboardEntry.objects.select_related("user").order_by("-mmr")[:100]


# Рейтинг по героям
class HeroLeaderboardView(generics.ListAPIView):
    serializer_class = HeroLeaderboardSerializer

    def get_queryset(self):
        hero_name = self.request.query_params.get("hero")
        # ✅ Используем метод get_ranked() с фильтром по герою
        qs = HeroLeaderboardEntry.get_ranked(hero=hero_name)
        return qs[:100]


# Рейтинг кланов
class ClanLeaderboardView(generics.ListAPIView):
    serializer_class = ClanLeaderboardSerializer

    def get_queryset(self):
        return ClanLeaderboardEntry.get_ranked()[:100]
