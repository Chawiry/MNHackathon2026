from django.urls import path

from . import views

urlpatterns = [
    path("", views.team_list, name="team_list"),
    path("members/add/", views.add_member, name="add_member"),
    path("memberships/<int:pk>/role/", views.change_role, name="change_role"),
    path("memberships/<int:pk>/remove/", views.remove_member, name="remove_member"),
]