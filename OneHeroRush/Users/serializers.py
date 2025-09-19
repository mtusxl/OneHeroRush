from rest_framework import serializers
from django.contrib.auth import authenticate
from .models import User  # Импорт твоей модели (username UNIQUE как steam_id, gold=0 default для оффлайн-фарма)

class LoginSerializer(serializers.Serializer): 
    username = serializers.CharField(max_length=50, required=True)
    password = serializers.CharField(required=True, write_only=True) 

    def validate(self, data):
        username = data.get('username').lower().strip()  
        password = data.get('password')
        if not username or not password:
            raise serializers.ValidationError("Username and password are required.")
        data['username'] = username
        return data

class UserPublicSerializer(serializers.Serializer):
    id = serializers.IntegerField(read_only=True)
    username = serializers.CharField(max_length=50, read_only=True)
    gold = serializers.IntegerField(read_only=True)  
    diamonds = serializers.IntegerField(read_only=True) 
    souls = serializers.IntegerField(read_only=True)  
    keys = serializers.IntegerField(read_only=True)

    def create(self, validated_data):
        pass 

    def to_representation(self, instance): 
        return {
            'id': instance.id,
            'username': instance.username,
            'gold': instance.gold,
            'diamonds': instance.diamonds,
            'souls': instance.souls,
            'keys': instance.keys,
        }