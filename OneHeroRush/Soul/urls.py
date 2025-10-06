from django.urls import path
from .views import SummonSoulView

urlpatterns = [
    path('api/souls/summon/', SummonSoulView.as_view(), name='summon_soul'),]