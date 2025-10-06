from django.urls import path
from .views import MailTemplateListView, MailTaskListView, MailSendView

urlpatterns = [
    path("mail/templates/", MailTemplateListView.as_view(), name="mail-templates"),
    path("mail/tasks/", MailTaskListView.as_view(), name="mail-tasks"),
    path("mail/send/", MailSendView.as_view(), name="mail-send"),
]
