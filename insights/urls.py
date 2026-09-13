from django.urls import path

from . import views

urlpatterns = [
    path("", views.insights_dashboard, name="insights"),
    path("criticality/", views.criticality_list, name="criticality_list"),
    path(
        "criticality/<int:skill_pk>/<int:dept_pk>/",
        views.criticality_edit,
        name="criticality_edit",
    ),
    path("cascade/", views.cascade_list, name="cascade_list"),
    path("cascade/create/", views.initiative_create, name="initiative_create"),
    path(
        "cascade/<int:pk>/generate/",
        views.initiative_generate,
        name="initiative_generate",
    ),
    path(
        "cascade/<int:pk>/approve/",
        views.initiative_approve,
        name="initiative_approve",
    ),
    path(
        "cascade/<int:pk>/cascade/",
        views.initiative_cascade,
        name="initiative_cascade",
    ),
    path("feedback/", views.feedback_list, name="feedback_list"),
    path("feedback/create/", views.feedback_create, name="feedback_create"),
    path(
        "feedback/<int:pk>/resolve/",
        views.feedback_resolve,
        name="feedback_resolve",
    ),
]