from rest_framework import serializers
from .models import Quest

class QuestSerializer(serializers.ModelSerializer):
    '''
    Сериализатор для списка квестов: имя, тип, условия, награды. Для GET /quests/.
    '''

    is_completed = serializers.SerializerMethodField()

    class Meta:
        model = Quest
        fields = ['id', 'name', 'type', 'conditions', 'reward_diamonds', 'reward_souls', 'reward_gold', 'reward_keys']

    def get_is_completed(self, obj):
        user = self.context.get('request').user
        return user in obj.users_completed.all()

class CompleteQuestSerializer(serializers.Serializer):
    '''
    Сериализатор для завершения квеста: проверка условий (для простоты булевое, но можно добавить валидацию).
    '''
    completed = serializers.BooleanField(default=True)