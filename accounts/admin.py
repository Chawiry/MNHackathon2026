from django.contrib import admin
from django.contrib.auth.admin import UserAdmin

from .models import User


@admin.register(User)
class CustomUserAdmin(UserAdmin):
    fieldsets = UserAdmin.fieldsets + (
        (
            "Profile",
            {"fields": ("tier", "job_title", "hire_date")},
        ),
    )
    add_fieldsets = UserAdmin.add_fieldsets + (
        (
            "Profile",
            {"fields": ("tier", "job_title", "hire_date")},
        ),
    )
    list_display = ("username", "email", "tier", "job_title", "is_staff")
    list_filter = ("tier", "is_staff", "is_superuser", "is_active")