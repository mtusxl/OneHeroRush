from rest_framework import serializers
import logging
from .models import User

logger = logging.getLogger(__name__)

class LoginSerializer(serializers.Serializer): 
    username = serializers.CharField(
        max_length=50, 
        required=True,
        help_text="Steam ID или ник для логина"
    )
    password = serializers.CharField(
        required=True, 
        write_only=True,
        help_text="Пароль"
    )

    def validate(self, data):
        try:
            username = data.get('username', '').lower().strip()  
            password = data.get('password')
            
            if not username:
                logger.warning("Login attempt with empty username")
                raise serializers.ValidationError("Username is required.")
            
            if not password:
                logger.warning(f"Login attempt with empty password for username: {username}")
                raise serializers.ValidationError("Password is required.")
            
            data['username'] = username
            logger.debug(f"Login validation successful for username: {username}")
            return data
            
        except serializers.ValidationError:
            raise
        except Exception as e:
            logger.error(f"Unexpected error during login validation: {str(e)}")
            raise serializers.ValidationError("Validation error occurred.")

class UserPublicSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ['id', 'username', 'gold', 'diamonds', 'souls', 'keys', 'mmr']
        read_only_fields = fields

    def to_representation(self, instance):
        try:
            data = super().to_representation(instance)
            logger.debug(f"Serialized public data for user {instance.id}")
            return data
        except Exception as e:
            logger.error(f"Error serializing user {instance.id}: {str(e)}")
            return {}