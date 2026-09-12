from collections import defaultdict

from django.contrib import messages
from django.http import HttpResponseForbidden
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse

from accounts.tiers import manages_team, require_tier, team_member_ids
from projects.models import Project, ProjectSkillRequirement
from skills.forms import RecordCertificateForm, RecordSkillForm
from skills.models import CertificateAward, SkillProficiency
from teams.models import Team, TeamMembership

from .forms import AddMemberForm, ChangeRoleForm, TeamCreateForm


@require_tier("team_manager")
def team_list(request):
    managed_teams = Team.objects.filter(
        memberships__user=request.user,
        memberships__role=TeamMembership.Role.MANAGER,
    ).distinct()

    member_ids = set(team_member_ids(request.user))

    pending_skills = (
        SkillProficiency.objects.filter(status=SkillProficiency.Status.PENDING, user_id__in=member_ids)
        .select_related("user", "skill", "skill__category")
        .order_by("user__username", "skill__name")
    )
    pending_certificates = (
        CertificateAward.objects.filter(status=CertificateAward.Status.PENDING, user_id__in=member_ids)
        .select_related("user", "certificate")
        .order_by("user__username", "-created_at")
    )

    coverage = {team.id: team_coverage(request.user, team) for team in managed_teams}

    teams_data = []
    for team in managed_teams:
        roster = list(
            team.memberships.select_related("user").order_by("-role", "user__username")
        )
        teams_data.append(
            {
                "team": team,
                "roster": roster,
                "coverage_rows": coverage[team.id],
            }
        )

    context = {
        "teams": teams_data,
        "pending_skills": pending_skills,
        "pending_certificates": pending_certificates,
        "team_create_form": TeamCreateForm(),
        "add_member_form": AddMemberForm(manager=request.user),
        "record_skill_form": RecordSkillForm(),
        "record_certificate_form": RecordCertificateForm(),
        "profile": request.user,
    }
    return render(request, "teams/teams.html", context)


def team_coverage(manager, team):
    """Project requirements resolved against a team's approved skills."""
    member_ids = set(
        team.memberships.values_list("user_id", flat=True)
    )
    requirements = ProjectSkillRequirement.objects.filter(
        project__status__in=[Project.Status.ACTIVE, Project.Status.PLANNED]
    ).select_related("project", "skill").order_by("-importance", "project__name")

    levels_by_skill = defaultdict(list)
    for skill_id, level in (
        SkillProficiency.objects.filter(
            status=SkillProficiency.Status.APPROVED,
            user_id__in=member_ids,
            skill_id__in=[r.skill_id for r in requirements],
        ).values_list("skill_id", "level")
    ):
        levels_by_skill[skill_id].append(level)

    rows = []
    for req in requirements:
        levels = levels_by_skill.get(req.skill_id, [])
        max_level = max(levels) if levels else 0
        people_needed = req.people_needed or 1
        count_met = sum(1 for level in levels if level >= req.required_level)
        if count_met >= people_needed:
            status = "Met"
        elif levels and max_level < req.required_level and count_met == 0:
            status = "Gap"
        else:
            status = "Partial"
        rows.append(
            {
                "project": req.project.name,
                "status": req.project.status,
                "skill": req.skill.name,
                "required_level": req.get_required_level_display(),
                "importance": req.get_importance_display(),
                "people_needed": req.people_needed,
                "count_met": count_met,
                "max_level": max_level,
                "coverage_status": status,
            }
        )
    return rows


@require_tier("team_manager")
def create_team(request):
    form = TeamCreateForm(request.POST)
    if form.is_valid():
        team = form.save()
        TeamMembership.objects.create(
            team=team, user=request.user, role=TeamMembership.Role.MANAGER
        )
        messages.success(request, f"Created team {team.name}.")
    return redirect(reverse("team_list"))


@require_tier("team_manager")
def add_member(request):
    form = AddMemberForm(manager=request.user, data=request.POST)
    if form.is_valid():
        team = form.cleaned_data["team"]
        user = form.cleaned_data["user"]
        if not manages_team(request.user, team):
            return HttpResponseForbidden("You don't manage that team.")
        team.memberships.get_or_create(
            user=user,
            defaults={"role": form.cleaned_data["role"]},
        )
        messages.success(request, f"Added {user.username} to {team.name}.")
    else:
        messages.error(request, form.errors)
    return redirect(reverse("team_list"))


@require_tier("team_manager")
def change_role(request, pk):
    membership = get_object_or_404(TeamMembership, pk=pk)
    if not manages_team(request.user, membership.team):
        return HttpResponseForbidden("You don't manage that team.")
    form = ChangeRoleForm(request.POST, instance=membership)
    if form.is_valid():
        form.save()
        messages.success(
            request, f"{membership.user.username} is now {membership.get_role_display()}."
        )
    return redirect(reverse("team_list"))


@require_tier("team_manager")
def remove_member(request, pk):
    membership = get_object_or_404(TeamMembership, pk=pk)
    if not manages_team(request.user, membership.team):
        return HttpResponseForbidden("You don't manage that team.")
    if membership.role == TeamMembership.Role.MANAGER:
        managers_left = membership.team.memberships.filter(
            role=TeamMembership.Role.MANAGER
        ).exclude(pk=membership.pk)
        if not managers_left.exists():
            messages.error(request, "A team needs at least one manager.")
            return redirect(reverse("team_list"))
    user = membership.user
    membership.delete()
    messages.success(request, f"Removed {user.username} from {membership.team}.")
    return redirect(reverse("team_list"))