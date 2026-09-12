from django.contrib import admin

from .models import Project, ProjectSkillRequirement


class ProjectSkillRequirementInline(admin.TabularInline):
    model = ProjectSkillRequirement
    extra = 2
    autocomplete_fields = ("skill",)


@admin.register(Project)
class ProjectAdmin(admin.ModelAdmin):
    list_display = ("name", "status", "start_date", "end_date")
    list_filter = ("status",)
    search_fields = ("name",)
    inlines = [ProjectSkillRequirementInline]


@admin.register(ProjectSkillRequirement)
class ProjectSkillRequirementAdmin(admin.ModelAdmin):
    list_display = ("project", "skill", "required_level", "importance", "people_needed")
    list_filter = ("importance", "project__status")
    autocomplete_fields = ("project", "skill")