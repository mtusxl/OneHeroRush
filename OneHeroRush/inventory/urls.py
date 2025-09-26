from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import ItemViewSet, ChestViewSet

router = DefaultRouter()
router.register(r'items', ItemViewSet, basename='item')
router.register(r'chests', ChestViewSet, basename='chest')

urlpatterns = [
    path('', include(router.urls)),
]