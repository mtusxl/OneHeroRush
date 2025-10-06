from django.urls import path
from .views import GlobalLeaderboardView, HeroLeaderboardView, ClanLeaderboardView

urlpatterns = [
    path("leaderboard/global/", GlobalLeaderboardView.as_view(), name="leaderboard-global"),
    path("leaderboard/heroes/", HeroLeaderboardView.as_view(), name="leaderboard-heroes"),
    path("leaderboard/clans/", ClanLeaderboardView.as_view(), name="leaderboard-clans"),
]
