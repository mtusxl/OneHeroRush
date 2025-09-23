from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import CharacterViewSet, select_character

router = DefaultRouter()
router.register(r'characters', CharacterViewSet, basename='character')

urlpatterns = [
    path('', include(router.urls)),
    path('characters/select/', select_character),
]