from django.urls import path
from .views import ChatHistoryView, MailListView, MailReadView

urlpatterns = [
    path("chat/history/<str:room>/", ChatHistoryView.as_view(), name="chat-history"),
    path("mail/", MailListView.as_view(), name="mail-list"),
    path("mail/read/<int:id>/", MailReadView.as_view(), name="mail-read"),
]
