from django.urls import path

from . import views

urlpatterns = [
    path("", views.user_list, name="user_list"),
    path("create/", views.create_user, name="create_user"),
    path("<int:pk>/tier/", views.change_tier, name="change_tier"),
    path("<int:pk>/toggle-active/", views.toggle_active, name="toggle_active"),
]