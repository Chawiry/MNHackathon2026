from django.contrib import messages
from django.db import IntegrityError, transaction
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse

from accounts.tiers import require_tier
from teams.models import Team, TeamMembership
from teams.services import team_coverage

from .forms import AddTeamForm, ProjectCreateForm
from teams.forms import AddRequirementForm
from .models import Project


def _coverage_summary(project):
    rows = []
    for team in project.teams.all():
        rows.extend(team_coverage(team))
    return {
        "met": sum(1 for r in rows if r["coverage_status"] == "Met"),
        "partial": sum(1 for r in rows if r["coverage_status"] == "Partial"),
        "gap": sum(1 for r in rows if r["coverage_status"] == "Gap"),
    }


@require_tier("leadership")
def project_list(request):
    projects = Project.objects.prefetch_related("teams__memberships").all()
    entries = [
        {"project": p, "summary": _coverage_summary(p)}
        for p in projects
    ]
    return render(
        request,
        "projects/project_list.html",
        {
            "entries": entries,
            "create_form": ProjectCreateForm(),
        },
    )


@require_tier("leadership")
def project_detail(request, pk):
    project = get_object_or_404(Project, pk=pk)
    teams = []
    for team in project.teams.all():
        roster = list(
            team.memberships.select_related("user").order_by("-role", "user__username")
        )
        teams.append({"team": team, "roster": roster, "coverage_rows": team_coverage(team)})
    return render(
        request,
        "projects/project_detail.html",
        {
            "project": project,
            "teams": teams,
            "add_team_form": AddTeamForm(),
            "add_requirement_form": AddRequirementForm(),
        },
    )


@require_tier("leadership")
@transaction.atomic
def create_project(request):
    form = ProjectCreateForm(request.POST)
    if form.is_valid():
        project = form.save()
        team_name = form.cleaned_data["team_name"] or project.name
        try:
            team = Team.objects.create(name=team_name, project=project)
            TeamMembership.objects.create(
                team=team,
                user=form.cleaned_data["manager"],
                role=TeamMembership.Role.MANAGER,
            )
        except IntegrityError:
            messages.error(request, f"A team named '{team_name}' already exists for this project.")
            return redirect(reverse("project_detail", args=[project.pk]))
        messages.success(
            request,
            f"Project {project.name} created with team {team.name}.",
        )
        return redirect(reverse("project_detail", args=[project.pk]))
    messages.error(request, form.errors)
    return redirect(reverse("project_list"))


@require_tier("leadership")
@transaction.atomic
def add_team(request, pk):
    project = get_object_or_404(Project, pk=pk)
    form = AddTeamForm(request.POST)
    if form.is_valid():
        try:
            team = Team.objects.create(name=form.cleaned_data["name"], project=project)
            TeamMembership.objects.create(
                team=team,
                user=form.cleaned_data["manager"],
                role=TeamMembership.Role.MANAGER,
            )
            messages.success(request, f"Added team {team.name} to {project.name}.")
        except IntegrityError:
            messages.error(request, f"A team named '{form.cleaned_data['name']}' already exists for this project.")
    return redirect(reverse("project_detail", args=[project.pk]))


@require_tier("leadership")
def remove_team(request, pk):
    team = get_object_or_404(Team, pk=pk)
    project = team.project
    team.delete()
    messages.success(request, f"Removed team {team.name}.")
    if project:
        return redirect(reverse("project_detail", args=[project.pk]))
    return redirect(reverse("project_list"))