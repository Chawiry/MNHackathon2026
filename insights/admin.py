from django.contrib import admin

from .models import ReadinessSnapshot, StrategicInitiative, TeamFeedback


@admin.register(StrategicInitiative)
class StrategicInitiativeAdmin(admin.ModelAdmin):
    list_display = ("title", "level", "status", "approved_by", "approved_at")
    list_filter = ("level", "status")
    search_fields = ("title",)


@admin.register(TeamFeedback)
class TeamFeedbackAdmin(admin.ModelAdmin):
    list_display = ("raised_by", "issue_type", "resolved", "initiative", "created_at")
    list_filter = ("issue_type", "resolved")
    autocomplete_fields = ("raised_by", "initiative")


@admin.register(ReadinessSnapshot)
class ReadinessSnapshotAdmin(admin.ModelAdmin):
    list_display = ("scope", "score", "critical_skills_count", "created_at")
    list_filter = ("scope",)