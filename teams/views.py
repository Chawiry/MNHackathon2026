from django.contrib import messages
from django.core.exceptions import PermissionDenied
from django.http import HttpResponseForbidden
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse

from accounts.models import Tier
from accounts.tiers import manages_team, require_tier
from skills.forms import RecordCertificateForm, RecordSkillForm
from .services import team_coverage

from teams.models import Team, TeamMembership, TeamSkillRequirement

from .forms import AddMemberForm, AddRequirementForm, ChangeRoleForm, CreateMemberForm


def _can_edit_requirements(request, team):
    if request.user.tier == Tier.LEADERSHIP:
        return
    if manages_team(request.user, team):
        return
    raise PermissionDenied


def _safe_return(request):
    next_url = request.POST.get("next")
    if next_url and next_url.startswith("/") and not next_url.startswith("//"):
        return next_url
    return reverse("team_list")


@require_tier("team_manager")
def team_list(request):
    managed_teams = Team.objects.filter(
        memberships__user=request.user,
        memberships__role=TeamMembership.Role.MANAGER,
    ).distinct()

    coverage = {team.id: team_coverage(team) for team in managed_teams}

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
                "requirements": team.skill_requirements.select_related("skill"),
            }
        )

    context = {
        "teams": teams_data,
        "add_member_form": AddMemberForm(manager=request.user),
        "create_member_form": CreateMemberForm(manager=request.user),
        "add_requirement_form": AddRequirementForm(),
        "record_skill_form": RecordSkillForm(),
        "record_certificate_form": RecordCertificateForm(),
        "profile": request.user,
    }
    return render(request, "teams/teams.html", context)


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


@require_tier("team_manager", "leadership")
def create_member(request):
    form = CreateMemberForm(manager=request.user, data=request.POST or None)
    if form.is_valid():
        team = form.cleaned_data["team"]
        if not manages_team(request.user, team) and request.user.tier != Tier.LEADERSHIP:
            return HttpResponseForbidden("You don't manage that team.")
        user = form.save()
        messages.success(
            request,
            f"Created {user.username} and added them to {team.name}.",
        )
        if request.user.tier == Tier.LEADERSHIP:
            return redirect(reverse("user_list"))
        return redirect(reverse("team_list"))
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


@require_tier("team_manager", "leadership")
def add_requirement(request, pk):
    team = get_object_or_404(Team, pk=pk)
    _can_edit_requirements(request, team)
    form = AddRequirementForm(request.POST)
    if form.is_valid():
        TeamSkillRequirement.objects.create(team=team, **form.cleaned_data)
        messages.success(request, "Skill requirement added.")
    else:
        messages.error(request, form.errors)
    return redirect(_safe_return(request))


@require_tier("team_manager", "leadership")
def remove_requirement(request, pk):
    req = get_object_or_404(TeamSkillRequirement, pk=pk)
    _can_edit_requirements(request, req.team)
    req.delete()
    messages.success(request, "Skill requirement removed.")
    return redirect(_safe_return(request))