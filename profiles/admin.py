from django.contrib import admin

from .models import DevelopmentActivity, ExperienceEntry, PerformanceReview


class DevelopmentActivityAdmin(admin.ModelAdmin):
    list_display = ("user", "activity_type", "skill", "status", "completed_at")
    list_filter = ("activity_type", "status")


class ExperienceEntryAdmin(admin.ModelAdmin):
    list_display = ("user", "role", "organization", "start_date", "end_date")


class PerformanceReviewAdmin(admin.ModelAdmin):
    list_display = ("user", "period", "rating", "reviewed_at")
    list_filter = ("rating",)


admin.site.register(DevelopmentActivity, DevelopmentActivityAdmin)
admin.site.register(ExperienceEntry, ExperienceEntryAdmin)
admin.site.register(PerformanceReview, PerformanceReviewAdmin)