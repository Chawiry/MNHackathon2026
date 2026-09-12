from django.urls import path

from . import views

urlpatterns = [
    path("", views.project_list, name="project_list"),
    path("create/", views.create_project, name="create_project"),
    path("<int:pk>/", views.project_detail, name="project_detail"),
    path("<int:pk>/teams/add/", views.add_team, name="add_team"),
    path("teams/<int:pk>/remove/", views.remove_team, name="remove_team"),
]