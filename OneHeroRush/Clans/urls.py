from django.urls import path
from .views import ClanCreateView, ClanJoinView, ClanDetailView, ClanRankingView, ClanLeaveView

urlpatterns = [
    path("clans/create", ClanCreateView.as_view()),
    path("clans/join", ClanJoinView.as_view()),
    path("clans/<int:pk>/", ClanDetailView.as_view()),
    path("clans/rankings", ClanRankingView.as_view()),
    path("clans/leave", ClanLeaveView.as_view()),  
]
