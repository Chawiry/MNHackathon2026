from django.urls import path

from . import views

urlpatterns = [
    path("activities/add/", views.add_activity, name="add_activity"),
    path("experiences/add/", views.add_experience, name="add_experience"),
    path("reviews/add/", views.add_review, name="add_review"),
]