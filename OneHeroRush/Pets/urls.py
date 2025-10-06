from django.urls import path
from .views import UserPetListView, SelectPetView, SummonPetView, UserSummonConfigView

urlpatterns = [
    path("pets/", UserPetListView.as_view(), name="pets-list"),
    path("pets/select/<int:id>/", SelectPetView.as_view(), name="pet-select"),
    path("pets/summon/", SummonPetView.as_view(), name="pet-summon"),
    path("pets/summon-config/", UserSummonConfigView.as_view(), name="summon-config"),
]