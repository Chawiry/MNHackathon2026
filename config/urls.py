"""URL configuration for config project."""

from django.contrib import admin
from django.urls import include, path

urlpatterns = [
    path("admin/", admin.site.urls),
    path("teams/", include("teams.urls")),
    path("skills/", include("skills.urls")),
    path("projects/", include("projects.urls")),
    path("users/", include("accounts.urls")),
    path("", include("core.urls")),
]