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
        try:
            user = self.context.get('request').user
            if user.is_authenticated:
                return obj.users_completed.filter(id=user.id).exists()
            return False
        except Exception as e:
            return False

class CompleteQuestSerializer(serializers.Serializer):
    '''
    Сериализатор для завершения квеста: проверка условий (для простоты булевое, но можно добавить валидацию).
    '''
    completed = serializers.BooleanField(default=True)