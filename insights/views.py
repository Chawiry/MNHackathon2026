from django.contrib import messages
from django.contrib.auth import get_user_model
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils import timezone

from accounts.tiers import require_tier
from insights.models import StrategicInitiative, TeamFeedback
from skills.models import Skill, SkillCriticalityAssessment, SkillProficiency
from teams.models import Department

from .forms import (
    CriticalityFactorsForm,
    FeedbackForm,
    FeedbackResolutionForm,
    InitiativeCreateForm,
)
from . import services

User = get_user_model()


def _trend_points(department=None, limit=12):
    """Readiness history (org or a department), oldest-first.

    Each point carries the delta to the prior snapshot.
    """
    snapshots = services.readiness_trend(department=department, limit=limit)
    points = []
    previous = None
    for snapshot in reversed(list(snapshots)):
        delta = snapshot.score - previous if previous is not None else None
        points.append({"snapshot": snapshot, "delta": delta})
        previous = snapshot.score
    return points


def _record_trend_if_changed(readiness):
    """Persist a readiness snapshot only when the score moved, so the trend
    tracks real change instead of recording the same point on every visit."""
    from insights.models import ReadinessSnapshot

    for row in readiness:
        scope = "org" if row["department"] is None else row["department"].name
        latest = (
            ReadinessSnapshot.objects.filter(scope=scope)
            .order_by("-created_at")
            .first()
        )
        if latest is None or latest.score != row["score"]:
            ReadinessSnapshot.objects.create(
                scope=scope,
                score=row["score"],
                critical_skills_count=row["critical_skills"],
            )


# ---------------------------------------------------------------------------
# Disclosure control (Phase 3): every per-skill aggregate is coarsened when the
# underlying group (approved holders) is smaller than ANON_GROUP_SIZE, so no
# exact count or individual name leaks above team-lead tier. Services stay raw;
# this view is the only place that shows leadership aggregates.
# ---------------------------------------------------------------------------

def _safe_bottlenecks(rows):
    safe = []
    for row in rows:
        safe.append(
            {
                **row,
                "masked": services.counts_masked(row["holder_count"]),
                "holder_count_display": services.guarded_count(
                    row["holder_count"], row["holder_count"]
                ),
                "shortfall_display": services.guarded_shortfall(
                    row["demand"], row["holder_count"]
                ),
            }
        )
    return safe


def _safe_depletion(rows):
    safe = []
    for row in rows:
        masked = services.counts_masked(row["holder_count"])
        holders = []
        if not masked:
            holders = [
                {
                    "name": h["name"],
                    "level": h["level"],
                    "expected_leave_date": h["expected_leave_date"],
                }
                for h in row["holders"]
            ]
        safe.append(
            {
                **row,
                "masked": masked,
                "holder_count": services.guarded_count(
                    row["holder_count"], row["holder_count"]
                ),
                "holders": holders,
            }
        )
    return safe


def _safe_successors(rows):
    safe = []
    for row in rows:
        masked = services.counts_masked(row["candidate_count"])
        candidates = [
            {
                **c,
                "name_display": (
                    services.guard_display_name(c["name"])
                    if masked
                    else c["name"]
                ),
            }
            for c in row["candidates"]
        ]
        safe.append({**row, "masked": masked, "candidates": candidates})
    return safe


def _safe_risk_matrix(rows):
    safe = []
    for row in rows:
        masked = services.counts_masked(row["rarity_holders"])
        safe.append(
            {
                **row,
                "masked": masked,
                "rarity": "masked (small group)" if masked else row["rarity"],
                "rarity_holders": services.guarded_count(
                    row["rarity_holders"], row["rarity_holders"]
                ),
                "holder_count": services.guarded_count(
                    row["holder_count"], row["rarity_holders"]
                ),
                "high_proficiency": services.guarded_count(
                    row["high_proficiency"], row["rarity_holders"]
                ),
            }
        )
    return safe


def _safe_succession_cards(cards):
    safe = []
    for card in cards:
        masked = services.counts_masked(card["group_size"])
        candidates = [
            {
                **c,
                "name_display": (
                    services.guard_display_name(c["name"])
                    if masked
                    else c["name"]
                ),
            }
            for c in card["candidates"]
        ]
        safe.append(
            {
                **card,
                "masked": masked,
                "holder_count": services.guarded_count(
                    card["holder_count"], card["group_size"]
                ),
                "qualified_count": services.guarded_count(
                    card["qualified_count"], card["group_size"]
                ),
                "ready_today_count": services.guarded_count(
                    card["ready_today_count"], card["group_size"]
                ),
                "candidates": candidates,
            }
        )
    return safe


def _safe_future_skills(rows):
    safe = []
    for row in rows:
        masked = services.counts_masked(row["holder_count"])
        safe.append(
            {
                **row,
                "masked": masked,
                "holder_count": services.guarded_count(
                    row["holder_count"], row["holder_count"]
                ),
                "avg_level": "—" if masked else row["avg_level"],
                "high_proficiency": services.guarded_count(
                    row["high_proficiency"], row["holder_count"]
                ),
            }
        )
    return safe


def _safe_departure_impacts(impacts):
    safe = []
    for impact in impacts:
        holders_after = impact["holders_after"]
        masked = services.counts_masked(holders_after)
        safe.append(
            {
                **impact,
                "masked": masked,
                "holders_after_display": services.guarded_count(
                    impact["holders_after"], holders_after
                ),
            }
        )
    return safe


@require_tier("leadership")
def insights_dashboard(request):
    dept_id = request.GET.get("dept")
    department = None
    if dept_id:
        department = get_object_or_404(Department, pk=dept_id)

    if department is not None:
        score, critical_skills = services.readiness_score(department)
        readiness = [
            {"department": department, "score": score, "critical_skills": critical_skills}
        ]
        org_score = readiness[0]
    else:
        readiness = services.readiness_report()
        org_score = next(r for r in readiness if r["department"] is None)
    _record_trend_if_changed(readiness)

    departure_user_id = request.GET.get("departure_user_id")
    departure_user = None
    departure_impacts = []
    if departure_user_id:
        departure_user = get_object_or_404(User, pk=departure_user_id)
        departure_impacts = services.simulate_departure(departure_user)

    adopt_skill_id = request.GET.get("adopt_skill_id")
    adopt = None
    if adopt_skill_id:
        skill = get_object_or_404(Skill, pk=adopt_skill_id)
        adopt = services.simulate_skill_adoption(skill)

    scope_label = department.name if department is not None else "Org"
    trend_points = _trend_points(department)
    risk_matrix = _safe_risk_matrix(services.risk_matrix(department))
    departure_impacts = _safe_departure_impacts(departure_impacts)
    stays = services.expected_stays()
    scheduled_leavers = sorted(
        (s for s in stays if s["months_remaining"] is not None),
        key=lambda s: s["months_remaining"],
    )
    unscheduled_leavers = len(stays) - len(scheduled_leavers)
    return render(
        request,
        "insights/insights.html",
        {
            "department": department,
            "departments": Department.objects.order_by("name"),
            "scope_label": scope_label,
            "bottlenecks": _safe_bottlenecks(services.at_risk_skills(department)),
            "scheduled_leavers": scheduled_leavers,
            "unscheduled_leavers": unscheduled_leavers,
            "depletion": _safe_depletion(services.skill_depletion(department)),
            "successors": _safe_successors(services.successors(department)),
            "months_per_level": services.MONTHS_PER_LEVEL,
            "bus_factor_threshold": services.BUS_FACTOR_THRESHOLD,
            "readiness": readiness,
            "org_score": org_score,
            "trend_points": trend_points,
            "risk_matrix": risk_matrix,
            "succession_cards": _safe_succession_cards(
                services.succession_report(department)
            ),
            "successor_ready_bar": services.QUALIFIED_SUCCESSOR_BAR,
            "future_skills": _safe_future_skills(services.future_skills()),
            "feedback_risks": services.feedback_risk_rollup(),
            "departure_users": User.objects.filter(is_active=True).order_by(
                "last_name", "username"
            ),
            "departure_user": departure_user,
            "departure_impacts": departure_impacts,
            "adopt_skills": Skill.objects.filter(is_active=True).order_by("name"),
            "adopt": adopt,
            "anon_group_size": services.ANON_GROUP_SIZE,
            # Chart.js payloads (SSR data — progressive enhancement)
            "readiness_chart": {
                "score": org_score["score"],
                "critical": org_score["critical_skills"],
            },
            "trend_chart": [
                {
                    "label": p["snapshot"].created_at.strftime("%d %b"),
                    "score": p["snapshot"].score,
                    "delta": p["delta"],
                }
                for p in trend_points
            ],
            "risk_chart": [
                {
                    "skill": row["skill"].name,
                    "score": row["criticality_score"],
                    "holders": row["rarity_holders"],
                }
                for row in risk_matrix
            ],
            "departure_chart": [
                {
                    "skill": impact["skill"].name,
                    "before": round(impact["coverage_before"] * 100),
                    "after": round(impact["coverage_after"] * 100),
                }
                for impact in departure_impacts
            ],
            "heatmap": services.criticality_heatmap(
                departments=[department] if department is not None else None
            ),
            "radar_chart": [
                {
                    "department": r["department"].name,
                    "score": r["score"],
                }
                for r in readiness
                if r["department"] is not None
            ],
            "level_mix": services.level_mix_by_category(),
        },
    )


@require_tier("leadership")
def criticality_list(request):
    """Skill × department grid of latest criticality scores, each cell editable."""
    departments = list(Department.objects.order_by("name"))
    latest_by_cell = {}
    for a in (
        SkillCriticalityAssessment.objects.select_related("skill", "department")
        .order_by("skill_id", "department_id", "-version")
    ):
        latest_by_cell.setdefault((a.skill_id, a.department_id), a)

    skill_ids = {sk for sk, _dept in latest_by_cell}
    skills = Skill.objects.filter(pk__in=skill_ids, is_active=True).order_by("name")
    rows = [
        {
            "skill": s,
            "cells": [
                (latest_by_cell.get((s.pk, d.pk)), d)
                for d in departments
            ],
        }
        for s in skills
    ]
    return render(
        request,
        "insights/criticality_list.html",
        {"departments": departments, "rows": rows},
    )


@require_tier("leadership")
def criticality_edit(request, skill_pk, dept_pk):
    skill = get_object_or_404(Skill, pk=skill_pk)
    department = get_object_or_404(Department, pk=dept_pk)
    current = (
        SkillCriticalityAssessment.objects.filter(skill=skill, department=department)
        .order_by("-version")
        .first()
    )

    if request.method == "POST":
        form = CriticalityFactorsForm(request.POST)
        if form.is_valid():
            data = form.cleaned_data
            updated = services.set_criticality_factors(
                department=department,
                skill=skill,
                business_impact=int(data["business_impact"]),
                strategic_relevance=int(data["strategic_relevance"]),
                time_to_replace_months=data["time_to_replace_months"],
                assessed_by=request.user,
            )
            if current and updated.pk == current.pk:
                messages.info(request, "No changes — the factors were already at those values.")
            elif current:
                messages.success(
                    request,
                    f"Updated {skill.name} @ {department.name}: "
                    f"{current.criticality_score} → {updated.criticality_score} (v{updated.version}).",
                )
            else:
                messages.success(
                    request,
                    f"Assessed {skill.name} @ {department.name}: "
                    f"score {updated.criticality_score} (v{updated.version}).",
                )
            return redirect(reverse("criticality_edit", args=[skill.pk, department.pk]))
    else:
        form = CriticalityFactorsForm(
            initial={
                "business_impact": current.business_impact if current else 3,
                "strategic_relevance": current.strategic_relevance if current else 3,
                "time_to_replace_months": current.time_to_replace_months if current else 12,
            }
        )

    history = list(
        SkillCriticalityAssessment.objects.filter(skill=skill, department=department)
        .order_by("-version")
    )
    concentration = SkillProficiency.objects.filter(
        skill=skill, status=SkillProficiency.Status.APPROVED, level__gte=4
    ).count()
    return render(
        request,
        "insights/criticality_edit.html",
        {
            "skill": skill,
            "department": department,
            "form": form,
            "current": current,
            "history": history,
            "concentration": concentration,
        },
    )


# ---------------------------------------------------------------------------
# Leadership cascade (§17): initiatives drafted, approved, cascaded.
# ---------------------------------------------------------------------------

@require_tier("leadership")
def cascade_list(request):
    initiatives = (
        StrategicInitiative.objects.select_related("parent", "owner", "approved_by")
        .prefetch_related("children", "feedback")
    )
    rows = []
    for initiative in initiatives:
        next_value = services.NEXT_INITIATIVE_LEVEL.get(initiative.level)
        rows.append(
            {
                "initiative": initiative,
                "can_cascade": (
                    next_value is not None
                    and initiative.status == StrategicInitiative.Status.APPROVED
                ),
                "next_label": (
                    StrategicInitiative.Level(next_value).label
                    if next_value
                    else None
                ),
                "next_title": f"{initiative.title} — {StrategicInitiative.Level(next_value).label}"
                              if next_value else initiative.title,
            }
        )
    return render(
        request,
        "insights/cascade.html",
        {
            "rows": rows,
            "create_form": InitiativeCreateForm(),
        },
    )


@require_tier("leadership")
def initiative_create(request):
    form = InitiativeCreateForm(request.POST or None)
    if form.is_valid():
        initiative = form.save(commit=False)
        initiative.owner = request.user
        initiative.status = StrategicInitiative.Status.DRAFT
        initiative.save()
        initiative.ai_draft_content = services.draft_initiative_content(initiative)
        initiative.save(update_fields=["ai_draft_content"])
        messages.success(
            request,
            f"Drafted {initiative.get_level_display()} initiative "
            f"“{initiative.title}” — review and approve it to cascade.",
        )
        return redirect(reverse("cascade_list"))
    messages.error(request, form.errors)
    return redirect(reverse("cascade_list"))


@require_tier("leadership")
def initiative_generate(request, pk):
    initiative = get_object_or_404(StrategicInitiative, pk=pk)
    if initiative.status == StrategicInitiative.Status.APPROVED:
        messages.error(request, "Approved plans can't be regenerated — create a new draft.")
    else:
        initiative.ai_draft_content = services.draft_initiative_content(initiative)
        initiative.save(update_fields=["ai_draft_content"])
        messages.info(request, f"Regenerated the draft for “{initiative.title}”.")
    return redirect(reverse("cascade_list"))


@require_tier("leadership")
def initiative_approve(request, pk):
    initiative = get_object_or_404(StrategicInitiative, pk=pk)
    if not initiative.ai_draft_content:
        messages.error(request, "Generate a draft before approving.")
    else:
        initiative.approved_content = initiative.ai_draft_content
        initiative.status = StrategicInitiative.Status.APPROVED
        initiative.approved_by = request.user
        initiative.approved_at = timezone.now()
        initiative.save(
            update_fields=[
                "approved_content",
                "status",
                "approved_by",
                "approved_at",
            ]
        )
        messages.success(
            request, f"Approved “{initiative.title}” — the next level can cascade from it."
        )
    return redirect(reverse("cascade_list"))


@require_tier("leadership")
def initiative_cascade(request, pk):
    parent = get_object_or_404(StrategicInitiative, pk=pk)
    if parent.status != StrategicInitiative.Status.APPROVED:
        messages.error(
            request,
            f"Approve “{parent.title}” first — children inherit only approved content.",
        )
        return redirect(reverse("cascade_list"))
    next_level = services.NEXT_INITIATIVE_LEVEL.get(parent.level)
    if next_level is None:
        messages.error(request, "Team-level plans are the bottom of the cascade.")
        return redirect(reverse("cascade_list"))
    title = (request.POST.get("title") or "").strip() or parent.title
    child = StrategicInitiative.objects.create(
        title=title,
        level=next_level,
        parent=parent,
        owner=request.user,
        status=StrategicInitiative.Status.DRAFT,
    )
    child.ai_draft_content = services.draft_initiative_content(child)
    child.save(update_fields=["ai_draft_content"])
    messages.success(
        request,
        f"Cascaded “{parent.title}” down to a {StrategicInitiative.Level(next_level).label} "
        f"draft “{child.title}”.",
    )
    return redirect(reverse("cascade_list"))


# ---------------------------------------------------------------------------
# Team feedback (§17): team leads raise flags, leadership resolves them, and
# unresolved flags roll up as aggregated risks on the dashboard.
# ---------------------------------------------------------------------------

@require_tier("team_manager", "leadership")
def feedback_list(request):
    feedback = (
        TeamFeedback.objects.select_related("raised_by", "initiative")
        .order_by("-created_at")
    )
    return render(
        request,
        "insights/feedback.html",
        {
            "feedback": feedback,
            "raise_form": FeedbackForm()
            if request.user.tier == "team_manager"
            else None,
            "resolve_form": FeedbackResolutionForm(),
            "can_resolve": request.user.tier == "leadership",
        },
    )


@require_tier("team_manager")
def feedback_create(request):
    form = FeedbackForm(request.POST or None)
    if form.is_valid():
        flag = form.save(commit=False)
        flag.raised_by = request.user
        flag.save()
        messages.success(
            request,
            f"Flagged {flag.get_issue_type_display()} — leadership will review it.",
        )
        return redirect(reverse("feedback_list"))
    messages.error(request, form.errors)
    return redirect(reverse("feedback_list"))


@require_tier("leadership")
def feedback_resolve(request, pk):
    flag = get_object_or_404(TeamFeedback, pk=pk)
    form = FeedbackResolutionForm(request.POST or None)
    if form.is_valid() and form.cleaned_data["resolution"]:
        flag.resolution = form.cleaned_data["resolution"]
        flag.resolved = True
        flag.resolved_at = timezone.now()
        flag.save(
            update_fields=["resolution", "resolved", "resolved_at"]
        )
        messages.success(request, "Flag resolved.")
    else:
        messages.error(request, "A resolution note is required.")
    return redirect(reverse("feedback_list"))