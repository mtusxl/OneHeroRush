from django.urls import path
from .views import ChatHistoryView

urlpatterns = [
    path("chat/history/<str:room>/", ChatHistoryView.as_view(), name="chat-history"),

]
