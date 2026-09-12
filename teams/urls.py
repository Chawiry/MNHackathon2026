from django.urls import path

from . import views

urlpatterns = [
    path("", views.team_list, name="team_list"),
    path("members/add/", views.add_member, name="add_member"),
    path("memberships/<int:pk>/role/", views.change_role, name="change_role"),
    path("memberships/<int:pk>/remove/", views.remove_member, name="remove_member"),
    path("team/<int:pk>/requirements/add/", views.add_requirement, name="add_team_requirement"),
    path("requirements/<int:pk>/remove/", views.remove_requirement, name="remove_team_requirement"),
]