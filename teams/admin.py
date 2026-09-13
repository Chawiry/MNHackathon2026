from django.contrib import admin

from .models import Department, Team, TeamMembership, TeamSkillRequirement


@admin.register(Department)
class DepartmentAdmin(admin.ModelAdmin):
    list_display = ("name", "description")
    search_fields = ("name",)


class TeamMembershipInline(admin.TabularInline):
    model = TeamMembership
    extra = 1


@admin.register(Team)
class TeamAdmin(admin.ModelAdmin):
    list_display = ("name", "department", "manager")
    list_filter = ("department",)
    search_fields = ("name",)
    inlines = [TeamMembershipInline]

    def manager(self, obj):
        manager_membership = obj.memberships.filter(role=TeamMembership.Role.MANAGER).first()
        return manager_membership.user if manager_membership else "—"


@admin.register(TeamMembership)
class TeamMembershipAdmin(admin.ModelAdmin):
    list_display = ("team", "user", "role", "joined_at")
    list_filter = ("team", "role")
    autocomplete_fields = ("user",)


@admin.register(TeamSkillRequirement)
class TeamSkillRequirementAdmin(admin.ModelAdmin):
    list_display = ("team", "skill", "required_level", "importance", "people_needed")
    list_filter = ("importance", "team")
    autocomplete_fields = ("team", "skill")