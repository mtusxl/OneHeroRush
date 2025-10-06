from django.urls import path
from .views import MailListView, MailReadView

path("mail/", MailListView.as_view(), name="mail-list"),
path("mail/read/<int:id>/", MailReadView.as_view(), name="mail-read"),