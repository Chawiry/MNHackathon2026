from django.contrib.auth.decorators import login_required
from django.db.models import Q
from django.http import JsonResponse
from django.shortcuts import redirect, render, reverse

from accounts.models import Tier, User
from accounts.tiers import team_member_ids
from insights import services as insights_services
from insights.models import TeamFeedback
from projects.models import Project
from skills.models import CertificateAward, Skill, SkillProficiency
from teams.models import Team, TeamMembership


@login_required
def home(request):
    tier = request.user.tier
    stats = []
    extra = {}

    if tier == Tier.EMPLOYEE:
        proficiencies = request.user.proficiencies.all()
        stats = [
            ("Skills recorded", proficiencies.count()),
            ("Approved", proficiencies.filter(status=SkillProficiency.Status.APPROVED).count()),
            ("Pending review", proficiencies.filter(status=SkillProficiency.Status.PENDING).count()),
        ]
        gaps = insights_services.employee_gaps(request.user)
        extra["gaps_count"] = len(gaps)
        extra["development_plan"] = insights_services.development_recommendations(
            request.user, gaps
        )[:3]

    elif tier == Tier.TEAM_MANAGER:
        member_ids = team_member_ids(request.user)
        pending = (
            SkillProficiency.objects.filter(status=SkillProficiency.Status.PENDING, user_id__in=member_ids).count()
            + CertificateAward.objects.filter(status=CertificateAward.Status.PENDING, user_id__in=member_ids).count()
        )
        stats = [
            ("Teams I manage", TeamMembership.objects.filter(user=request.user, role=TeamMembership.Role.MANAGER).count()),
            ("Team members", len(member_ids)),
            ("Pending approvals", pending),
        ]
        extra["open_feedback"] = TeamFeedback.objects.filter(resolved=False).count()

    elif tier == Tier.LEADERSHIP:
        pending = (
            SkillProficiency.objects.filter(status=SkillProficiency.Status.PENDING).count()
            + CertificateAward.objects.filter(status=CertificateAward.Status.PENDING).count()
        )
        stats = [
            ("People", User.objects.filter(is_active=True).count()),
            ("Teams", Team.objects.count()),
            ("Active projects", Project.objects.filter(status=Project.Status.ACTIVE).count()),
            ("Pending approvals", pending),
        ]
        extra["open_feedback"] = TeamFeedback.objects.filter(resolved=False).count()

    return render(request, "core/home.html", {"stats": stats, **extra})


@login_required
def search(request):
    q = request.GET.get("q", "").strip()
    results = _search_results(request, q)
    if request.GET.get("format") == "json":
        return JsonResponse({"q": q, "results": results})
    return render(request, "core/search.html", {"query": q, "results": results})


def _search_results(request, q):
    empty = {"users": [], "skills": [], "teams": [], "projects": []}
    if not q:
        return empty

    def pack(label, detail, url):
        return {"label": label, "detail": detail, "url": url}

    results = empty
    results["skills"] = [
        pack(s.name, "Skill", reverse("my_skills"))
        for s in Skill.objects.filter(name__icontains=q).order_by("name")[:5]
    ]
    if request.user.tier in (Tier.LEADERSHIP, Tier.TEAM_MANAGER):
        results["users"] = [
            pack(u.get_full_name() or u.username, u.job_title, reverse("user_list"))
            for u in User.objects.filter(
                Q(first_name__icontains=q) | Q(last_name__icontains=q)
                | Q(username__icontains=q) | Q(job_title__icontains=q)
            ).order_by("first_name")[:5]
        ]
        results["teams"] = [
            pack(t.name, "Team", reverse("team_list"))
            for t in Team.objects.filter(name__icontains=q).order_by("name")[:5]
        ]
    if request.user.tier == Tier.LEADERSHIP:
        results["projects"] = [
            pack(p.name, p.get_status_display(), reverse("project_detail", args=[p.pk]))
            for p in Project.objects.filter(name__icontains=q).order_by("name")[:5]
        ]
    return results