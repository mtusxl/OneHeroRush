from rest_framework import serializers
from .models import Clan, ClanMember


class ClanSerializer(serializers.ModelSerializer):
    leader = serializers.StringRelatedField()

    class Meta:
        model = Clan
        fields = ["id", "name", "description", "leader", "members_count", "total_mmr"]


class ClanDetailSerializer(serializers.ModelSerializer):
    leader = serializers.StringRelatedField()
    members = serializers.SerializerMethodField()

    class Meta:
        model = Clan
        fields = ["id", "name", "description", "leader", "members", "total_mmr"]

    def get_members(self, obj):
        return [m.user.username for m in obj.members.all()]
