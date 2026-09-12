from django.urls import path

from . import views

urlpatterns = [
    path("", views.team_list, name="team_list"),
    path("create/", views.create_team, name="create_team"),
    path("members/add/", views.add_member, name="add_member"),
    path("memberships/<int:pk>/role/", views.change_role, name="change_role"),
    path("memberships/<int:pk>/remove/", views.remove_member, name="remove_member"),
]