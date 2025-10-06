from rest_framework import serializers
from .models import LeaderboardEntry, HeroLeaderboardEntry, ClanLeaderboardEntry

class LeaderboardSerializer(serializers.ModelSerializer):
    username = serializers.CharField(source="user.username", read_only=True)
    rank = serializers.IntegerField(read_only=True)

    class Meta:
        model = LeaderboardEntry
        fields = ["rank", "username", "mmr"]


class HeroLeaderboardSerializer(serializers.ModelSerializer):
    username = serializers.CharField(source="user.username", read_only=True)
    rank = serializers.IntegerField(read_only=True)

    class Meta:
        model = HeroLeaderboardEntry
        fields = ["rank", "username", "hero_name", "power"]


class ClanLeaderboardSerializer(serializers.ModelSerializer):
    clan_name = serializers.CharField(source="clan.name", read_only=True)
    rank = serializers.IntegerField(read_only=True)

    class Meta:
        model = ClanLeaderboardEntry
        fields = ["rank", "clan_name", "points"]
