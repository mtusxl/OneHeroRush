from django.contrib.auth.models import AbstractBaseUser, PermissionsMixin, BaseUserManager
from django.db import models
from django.utils import timezone
import logging

logger = logging.getLogger(__name__)

class UserManager(BaseUserManager):
    def create_user(self, username, password=None, **extra_fields):
        try:
            if not username:
                logger.error("Attempt to create user without username")
                raise ValueError("Username is required")
            
            username = username.lower().strip()
            logger.debug(f"Creating user with username: {username}")
            
            user = self.model(username=username, **extra_fields)
            user.set_password(password)
            user.save(using=self._db)
            
            logger.info(f"User created successfully: {username}")
            return user
            
        except Exception as e:
            logger.error(f"Error creating user {username}: {str(e)}")
            raise

    def create_superuser(self, username, password=None, **extra_fields):
        try:
            logger.debug(f"Creating superuser: {username}")
            extra_fields.setdefault("is_staff", True)
            extra_fields.setdefault("is_superuser", True)
            
            user = self.create_user(username, password, **extra_fields)
            logger.info(f"Superuser created successfully: {username}")
            return user
            
        except Exception as e:
            logger.error(f"Error creating superuser {username}: {str(e)}")
            raise


class User(AbstractBaseUser, PermissionsMixin):
    username = models.CharField(max_length=50, unique=True)

    # Игровая валюта
    gold = models.IntegerField(default=0)
    diamonds = models.IntegerField(default=0)
    souls = models.IntegerField(default=0)
    keys = models.IntegerField(default=0)
    soul_coupons = models.PositiveIntegerField(default=0)

    mmr = models.IntegerField(default=0)

    # Служебные поля
    is_active = models.BooleanField(default=True)
    is_staff = models.BooleanField(default=False)
    created_at = models.DateTimeField(default=timezone.now)
    max_heroes = models.PositiveIntegerField(default=3)
    purchased_heroes = models.JSONField(default=list)

    class Meta:
        indexes = [
            models.Index(fields=['mmr']),
            models.Index(fields=['username']),
        ]

    objects = UserManager()

    USERNAME_FIELD = "username"
    REQUIRED_FIELDS = []

    def __str__(self):
        return self.username

    def save(self, *args, **kwargs):
        try:
            # Нормализация username перед сохранением
            if self.username:
                self.username = self.username.lower().strip()
            
            is_new = self._state.adding
            super().save(*args, **kwargs)
            
            if is_new:
                logger.info(f"New user saved: {self.username} (ID: {self.id})")
            else:
                logger.debug(f"User updated: {self.username} (ID: {self.id})")
                
        except Exception as e:
            logger.error(f"Error saving user {self.username}: {str(e)}")
            raise


class UserProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    active_pet = models.ForeignKey('Pets.UserPet', on_delete=models.SET_NULL, 
                                   null=True, blank=True, related_name='active_for_user')

    def __str__(self):
        return f"Profile for {self.user.username}"

    def save(self, *args, **kwargs):
        try:
            is_new = self._state.adding
            super().save(*args, **kwargs)
            
            if is_new:
                logger.info(f"New user profile created for user {self.user.id}")
            else:
                logger.debug(f"User profile updated for user {self.user.id}")
                
        except Exception as e:
            logger.error(f"Error saving user profile for user {self.user.id}: {str(e)}")
            raise