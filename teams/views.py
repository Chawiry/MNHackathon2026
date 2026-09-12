from django.contrib import messages
from django.http import HttpResponseForbidden
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse

from accounts.tiers import manages_team, require_tier, team_member_ids
from projects.services import team_coverage
from skills.forms import RecordCertificateForm, RecordSkillForm
from skills.models import CertificateAward, SkillProficiency
from teams.models import Team, TeamMembership

from .forms import AddMemberForm, ChangeRoleForm


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
            }
        )

    context = {
        "teams": teams_data,
        "pending_skills": pending_skills,
        "pending_certificates": pending_certificates,
        "add_member_form": AddMemberForm(manager=request.user),
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