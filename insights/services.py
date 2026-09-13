"""Organization-wide analytics for leadership.

All insights are derived from the live data model:

- bottlenecks: low bus-factor skills (few holders) and supply/demand shortfalls
- expected stays: leadership-set expected leave dates for every active user
- skill depletion: when a skill could be lost entirely (last holder leaves)
- successor readiness: estimated months-to-required-level using a configurable
  pace (MONTHS_PER_LEVEL months to gain one proficiency level).

The strategic layer adds:

- criticality & rarity: per-business-unit, versioned skill risk (criticality is
  NOT rarity — a skill can be rare without being critical and vice versa)
- succession coverage: graph-aware successor candidates + readiness %
  (the 'who can back them up?' half of the criticality answer)
- organization readiness: a 0-100 score penalizing critical skills that are
  uncovered, timestamped for trend tracking
- per-employee skill gaps with priority, and an IF->THEN recommendation rule
  set (Gap 5) that routes each gap to a believable development action
- plan readiness: manning x qualification x availability for projects/plans
- what-if simulations: departure and skill-adoption scenarios
- anonymization: small-group aggregates (< n) are coarsened or hidden above
  the team-lead tier to prevent re-identification
"""

from collections import defaultdict
from datetime import date

from django.utils import timezone

from accounts.models import User
from skills.models import Skill, SkillCriticalityAssessment, SkillFutureDemand, SkillProficiency, SkillRelationship
from teams.models import Department, Team, TeamMembership, TeamSkillRequirement

MONTHS_PER_LEVEL = 6
BUS_FACTOR_THRESHOLD = 2
SUCCESSOR_CAP = 3

# --- strategic-layer constants -------------------------------------------------
CRITICALITY_THRESHOLD = 60          # score >= this => the skill is "critical"
ANON_GROUP_SIZE = 5                 # groups smaller than this must be coarsened
SUCCESSOR_HOLDER_LEVEL = 3          # level at/above which someone counts as a holder
SUCCESSOR_TARGET_LEVEL = 4          # level a successor should reach to "back up"
READY_TODAY_BAR = 80                # readiness % at/above which a successor is ready now
QUALIFIED_SUCCESSOR_BAR = 60       # readiness % at/above which a successor counts as a qualified backup
MAX_TEAMS_AVAILABILITY = 2          # qualified person is unavailable past this many teams
FUTURE_BOOST = 10                   # priority points for emerging/growing skills
RECOMMENDATION_POOL_CAP = 3


def _months_between(from_date, to_date):
    return (to_date.year - from_date.year) * 12 + (to_date.month - from_date.month)


def _approved_by_skill(user_ids=None):
    """Approved proficiencies keyed by skill id; optionally scoped to users."""
    qs = SkillProficiency.objects.filter(
        status=SkillProficiency.Status.APPROVED
    ).select_related("skill", "user")
    if user_ids is not None:
        qs = qs.filter(user_id__in=user_ids)
    by_skill = defaultdict(list)
    for p in qs:
        by_skill[p.skill_id].append(p)
    return dict(by_skill)


def _department_member_ids(department):
    return set(
        TeamMembership.objects.filter(team__department=department).values_list(
            "user_id", flat=True
        )
    )


def at_risk_skills(department=None):
    """Skills flagged as knowledge bottlenecks, optionally per department.

    A skill is at risk when it has a low bus factor (<= BUS_FACTOR_THRESHOLD
    holders) or when demand slots exceed the number of holders. When a
    department is given, both the demand (its teams' requirements) and the
    holder pool (its own people) are scoped to that business unit.
    """
    requirements = TeamSkillRequirement.objects.select_related("skill")
    demand = defaultdict(int)
    required_level = {}
    critical = set()
    if department is not None:
        requirements = requirements.filter(team__department=department)
    for r in requirements:
        demand[r.skill_id] += r.people_needed or 1
        level = required_level.get(r.skill_id)
        if level is None or r.required_level > level:
            required_level[r.skill_id] = r.required_level
        if r.importance == TeamSkillRequirement.Importance.CRITICAL:
            critical.add(r.skill_id)

    member_ids = (
        _department_member_ids(department)
        if department is not None
        else None
    )
    by_skill = _approved_by_skill(user_ids=member_ids)
    skills = {
        s.pk: s
        for s in Skill.objects.filter(
            pk__in=set(demand) | set(by_skill)
        ).select_related("category")
    }

    rows = []
    for skill_id in sorted(set(demand) | set(by_skill)):
        holders = by_skill.get(skill_id, [])
        holder_count = len(holders)
        slots = demand.get(skill_id, 0)
        low_bus_factor = holder_count <= BUS_FACTOR_THRESHOLD
        shortfall = max(0, slots - holder_count)
        at_risk = low_bus_factor or shortfall > 0
        rows.append(
            {
                "skill": skills[skill_id],
                "holder_count": holder_count,
                "demand": slots,
                "shortfall": shortfall,
                "low_bus_factor": low_bus_factor,
                "critical": skill_id in critical,
                "required_level": required_level.get(skill_id),
                "at_risk": at_risk,
            }
        )
    return [r for r in rows if r["at_risk"]]


def expected_stays():
    """Every active user with their leadership-set expected leave date."""
    today = timezone.localdate()
    rows = []
    users = (
        User.objects.filter(is_active=True)
        .order_by("last_name", "username")
    )
    for user in users:
        if user.expected_leave_date:
            months = max(0, _months_between(today, user.expected_leave_date))
        else:
            months = None
        rows.append(
            {
                "user": user,
                "expected_leave_date": user.expected_leave_date,
                "hire_date": user.hire_date,
                "months_remaining": months,
            }
        )
    return rows


def skill_depletion(department=None):
    """When the company could lose each at-risk skill entirely.

    Uses the last holder's expected leave date as the horizon; flagged as
    unknown when any holder has no expected leave date set. Optionally scoped
    to a department's demand and holder pool.
    """
    today = timezone.localdate()
    by_skill = _approved_by_skill(
        _department_member_ids(department) if department is not None else None
    )
    rows = []
    for entry in at_risk_skills(department):
        skill = entry["skill"]
        holders = by_skill.get(skill.id, [])
        holder_rows = []
        last_leave = None
        unknown = False
        for p in holders:
            leave = p.user.expected_leave_date
            if leave is None:
                unknown = True
            elif last_leave is None or leave > last_leave:
                last_leave = leave
            holder_rows.append(
                {
                    "name": p.user.get_full_name() or p.user.username,
                    "level": p.get_level_display(),
                    "expected_leave_date": leave,
                }
            )
        if holder_rows:
            holder_rows.sort(
                key=lambda h: (h["expected_leave_date"] is None, h["expected_leave_date"] or date.min)
            )
        has_horizon = last_leave is not None
        months_left = (
            _months_between(today, last_leave)
            if has_horizon and last_leave > today
            else None
        )
        rows.append(
            {
                "skill": skill,
                "critical": entry["critical"],
                "holder_count": entry["holder_count"],
                "holders": holder_rows,
                "last_leave_date": last_leave,
                "unknown": unknown,
                "months_left": months_left,
            }
        )
    # Most urgent first: definite near-term horizons, then unknown horizons.
    rows.sort(
        key=lambda r: (
            r["last_leave_date"] is None,
            r["last_leave_date"] or today,
        )
    )
    return rows


def successors(department=None):
    """Estimated time-to-readiness for people below an at-risk skill's level.

    Optionally scoped to a department's demand and holder pool.
    """
    by_skill = _approved_by_skill(
        _department_member_ids(department) if department is not None else None
    )
    rows = []
    for entry in at_risk_skills(department):
        required = entry["required_level"]
        if not required:
            continue
        candidates = []
        for p in by_skill.get(entry["skill"].id, []):
            if p.level < required:
                gap = required - p.level
                candidates.append(
                    {
                        "name": p.user.get_full_name() or p.user.username,
                        "level": p.get_level_display(),
                        "gap": gap,
                        "months": gap * MONTHS_PER_LEVEL,
                    }
                )
        if candidates:
            candidates.sort(key=lambda c: (c["months"], c["name"]))
            rows.append(
                {
                    "skill": entry["skill"],
                    "critical": entry["critical"],
                    "required_level": SkillProficiency.Level(required).label,
                    "candidate_count": len(candidates),
                    "candidates": candidates[:SUCCESSOR_CAP],
                }
            )
    rows.sort(key=lambda r: (not r["critical"], r["skill"].name))
    return rows


# ---------------------------------------------------------------------------
# 1. Anonymization rule (Gap 2)
#    Any aggregate over a group smaller than ANON_GROUP_SIZE is suppressed or
#    shown as a range, to prevent re-identification above the team-lead tier.
# ---------------------------------------------------------------------------

def aggregates_allowed(group_size):
    """Whether detailed aggregate info may be shown for a group of this size."""
    return group_size >= ANON_GROUP_SIZE


def counts_masked(group_size):
    """True when a nonempty group below ANON_GROUP_SIZE must be coarsened.

    An empty group (0 people) has nobody to re-identify, so exact zeros stay
    disclosed; small but nonempty groups never show exact figures.
    """
    return 0 < group_size < ANON_GROUP_SIZE


def guarded_count(count, group_size):
    """Exact count when the group is large enough, else a coarsened range.

    Small nonzero groups always show the full anonymous band (``1–4``) so the
    exact figure — including a degenerate ``1–1`` for a single-person group —
    is never stated; exact counts pass through when disclosure is safe.
    """
    if not counts_masked(group_size):
        return count
    if count <= 0:
        return count
    return f"1–{ANON_GROUP_SIZE - 1}"


def guarded_shortfall(demand, group_size):
    """Supply-shortfall display that cannot leak a masked holder count.

    When holders are masked they are between 1 and ANON_GROUP_SIZE - 1, so the
    shortfall can be anything from ``demand - (ANON_GROUP_SIZE - 1)`` up to
    ``demand - 1``; the exact figure is never stated.
    """
    if not counts_masked(group_size):
        return max(0, demand - group_size)
    lo = max(0, demand - (ANON_GROUP_SIZE - 1))
    hi = max(0, demand - 1)
    if lo == hi:
        return lo
    return f"{lo}–{hi}"


def guard_display_name(name, drill_down=False):
    """Mask individual identity unless the viewer has drill-down permission.

    Drill-down is disabled by default: leadership aggregates never reveal
    individual names without an explicit approval workflow.
    """
    if drill_down:
        return name
    return "— masked (requests drill-down approval)"


# ---------------------------------------------------------------------------
# 2. Criticality & rarity (§6)
#    Criticality = the business impact if the skill disappears. Scoped per
#    business unit, timestamped and versioned. Rarity is a separate measure.
# ---------------------------------------------------------------------------

def criticality_formula(business_impact, strategic_relevance, time_to_replace_months, concentration_count):
    """0–100 criticality from the four spec factors.

    - business impact (1–5) drives up to 40 pts
    - strategic relevance (1–5) drives up to 20 pts
    - time-to-replace drives up to 20 pts (12mo→10, 24mo→20)
    - concentration risk (holders at proficiency >= 4) drives up to 20 pts
    """
    impact = (min(max(business_impact, 1), 5) / 5) * 40
    strategic = (min(max(strategic_relevance, 1), 5) / 5) * 20
    replace = min(20.0, (time_to_replace_months / 12) * 10) if time_to_replace_months else 5.0
    concentration = (1 - min(max(concentration_count, 1), 5) / 5) * 20
    score = impact + strategic + replace + concentration
    return int(round(min(100, max(0, score))))


def _high_proficiency_count(skill_id, by_skill=None):
    """Number of approved holders at proficiency >= 4 (concentration risk)."""
    by_skill = by_skill or _approved_by_skill()
    return sum(1 for p in by_skill.get(skill_id, []) if p.level >= 4)


def _holder_count(skill_id, by_skill=None, level=3):
    by_skill = by_skill or _approved_by_skill()
    return sum(1 for p in by_skill.get(skill_id, []) if p.level >= level)


def latest_assessments(department=None):
    """Latest SkillCriticalityAssessment per skill, optionally scoped to a dept."""
    qs = SkillCriticalityAssessment.objects.select_related("skill", "department")
    if department is not None:
        qs = qs.filter(department=department)
    latest_by_skill = {}
    for a in qs.order_by("skill_id", "-version"):
        if a.skill_id not in latest_by_skill:
            latest_by_skill[a.skill_id] = a
    return latest_by_skill


def _critical_skills_of(department, by_skill=None, assessments=None):
    """Skills assessed at/above CRITICALITY_THRESHOLD in a business unit."""
    assessments = assessments if assessments is not None else latest_assessments(department)
    return {
        sid: a
        for sid, a in assessments.items()
        if a.criticality_score >= CRITICALITY_THRESHOLD
    }


def assess_criticality(department, skill, by_skill=None, force=False):
    """Upsert a new versioned assessment only when the score moved materially."""
    by_skill = by_skill or _approved_by_skill()
    concentration = _high_proficiency_count(skill.pk, by_skill)
    current = (
        SkillCriticalityAssessment.objects.filter(department=department, skill=skill)
        .order_by("-version")
        .first()
    )
    if current:
        business_impact = current.business_impact
        strategic_relevance = current.strategic_relevance
        time_to_replace_months = current.time_to_replace_months
    else:
        business_impact = 3
        strategic_relevance = 3
        time_to_replace_months = 12

    score = criticality_formula(
        business_impact, strategic_relevance, time_to_replace_months, concentration
    )
    if current and abs(current.criticality_score - score) < 5 and not force:
        return current

    version = (current.version if current else 0) + 1
    return SkillCriticalityAssessment.objects.create(
        department=department,
        skill=skill,
        business_impact=business_impact,
        strategic_relevance=strategic_relevance,
        time_to_replace_months=time_to_replace_months,
        criticality_score=score,
        version=version,
    )


def set_criticality_factors(
    department,
    skill,
    business_impact,
    strategic_relevance,
    time_to_replace_months,
    assessed_by=None,
):
    """Record an explicit (human) edit of a skill's criticality factor inputs.

    Preserves history: if the factors changed, a new version is appended with
    the score recomputed from today's live high-proficiency concentration.
    Returns the latest assessment (no new row if the inputs are unchanged).
    """
    by_skill = _approved_by_skill()
    concentration = _high_proficiency_count(skill.pk, by_skill)
    current = (
        SkillCriticalityAssessment.objects.filter(department=department, skill=skill)
        .order_by("-version")
        .first()
    )
    if (
        current
        and current.business_impact == business_impact
        and current.strategic_relevance == strategic_relevance
        and current.time_to_replace_months == time_to_replace_months
    ):
        return current

    score = criticality_formula(
        business_impact, strategic_relevance, time_to_replace_months, concentration
    )
    version = (current.version if current else 0) + 1
    return SkillCriticalityAssessment.objects.create(
        department=department,
        skill=skill,
        business_impact=business_impact,
        strategic_relevance=strategic_relevance,
        time_to_replace_months=time_to_replace_months,
        criticality_score=score,
        assessed_by=assessed_by,
        version=version,
    )


def reassess_all(department=None, by_skill=None, force=True):
    """(Re)assess every skill that matters to a business unit's teams."""
    by_skill = by_skill or _approved_by_skill()
    departments = Department.objects.all() if department is None else [department]
    skills = Skill.objects.filter(
        is_active=True,
        id__in=set(by_skill) | set(
            TeamSkillRequirement.objects.values_list("skill_id", flat=True)
        ),
    )
    for dept in departments:
        for skill in skills:
            assess_criticality(dept, skill, by_skill=by_skill, force=force)


def rarity(skill_id, by_skill=None):
    """Rarity measures how few people possess the skill, apart from criticality."""
    by_skill = by_skill or _approved_by_skill()
    holders = sum(1 for p in by_skill.get(skill_id, []) if p.level >= 1)
    if holders == 0:
        return ("unavailable", holders)
    if holders == 1:
        return ("ultra_rare", holders)
    if holders <= 3:
        return ("rare", holders)
    if holders <= 8:
        return ("scarce", holders)
    return ("available", holders)


def risk_matrix(department=None):
    """Critical ratio + rarity per skill for the dashboard."""
    by_skill = _approved_by_skill()
    assessments = latest_assessments(department)
    rows = []
    for skill_id, assessment in assessments.items():
        if assessment.criticality_score < CRITICALITY_THRESHOLD:
            continue
        rarity_label, holders = rarity(skill_id, by_skill)
        rows.append(
            {
                "skill": assessment.skill,
                "criticality_score": assessment.criticality_score,
                "business_impact": assessment.business_impact,
                "strategic_relevance": assessment.strategic_relevance,
                "time_to_replace_months": assessment.time_to_replace_months,
                "holder_count": _holder_count(skill_id, by_skill),
                "high_proficiency": _high_proficiency_count(skill_id, by_skill),
                "rarity": rarity_label,
                "rarity_holders": holders,
                "version": assessment.version,
                "assessed_at": assessment.assessed_at,
                "department": assessment.department,
            }
        )
    rows.sort(key=lambda r: (-r["criticality_score"], r["skill"].name))
    return rows


# ---------------------------------------------------------------------------
# 3. Succession coverage & readiness (Gap 3)
#    The 'who can back them up?' half of the criticality answer.
# ---------------------------------------------------------------------------

def _related_skills(skill):
    """Skills adjacent to a target through the skills graph."""
    return SkillRelationship.objects.filter(
        from_skill=skill,
        kind__in=(SkillRelationship.Kind.RELATED, SkillRelationship.Kind.TRANSFERS),
    ).select_related("to_skill")


def succession_for_skill(skill, by_skill=None, drill_down=False):
    """Risk card for one critical skill: holders, successors, coverage, readiness.

    A successor is someone who does NOT yet hold the skill at holder level, but
    either already has it at an incipient level (1–2) or holds a closely related
    skill at >= 2 through the skills graph.
    """
    by_skill = by_skill or _approved_by_skill()
    holders = [
        p
        for p in by_skill.get(skill.pk, [])
        if p.level >= SUCCESSOR_HOLDER_LEVEL
    ]
    holder_ids = {p.user_id for p in holders}

    candidates = []
    for p in by_skill.get(skill.pk, []):
        if p.user_id in holder_ids or p.level >= SUCCESSOR_HOLDER_LEVEL:
            continue
        direct_level = p.level  # 1-2, incipient
        best_related = 0.0
        for rel in _related_skills(skill):
            rel_level = next(
                (
                    r.level
                    for r in by_skill.get(rel.to_skill_id, [])
                    if r.user_id == p.user_id
                ),
                0,
            )
            best_related = max(best_related, rel_level / 5)
        if direct_level >= 2 or best_related >= 0.4:  # prof >=2 incl. via graph
            readiness = min(100, round((direct_level / 5) * 60 + best_related * 40))
            months = max(1, (SUCCESSOR_TARGET_LEVEL - max(direct_level, 1))) * MONTHS_PER_LEVEL
            candidates.append(
                {
                    "user": p.user,
                    "name": p.user.get_full_name() or p.user.username,
                    "direct_level": direct_level,
                    "readiness": readiness,
                    "months": months,
                    "ready_today": readiness >= READY_TODAY_BAR,
                }
            )

    candidates.sort(key=lambda c: (-c["readiness"], c["name"]))
    qualified = [c for c in candidates if c["readiness"] >= QUALIFIED_SUCCESSOR_BAR]
    ready_today = [c for c in candidates if c["ready_today"]]
    if holders:
        joined_coverage = min(1.0, len(qualified) / len(holders))
        if joined_coverage <= 0.0:
            # No one has crossed the qualified bar yet, but someone may already
            # be partway there — count the strongest in-pipeline successor as
            # fractional coverage so the metric shows progress, not a binary 0.
            best_pipeline = max((c["readiness"] for c in candidates), default=0)
            joined_coverage = best_pipeline / 100
    else:
        joined_coverage = 0.0
    coverage_ratio = round(joined_coverage, 2)
    return {
        "skill": skill,
        "holders": holders,
        "group_size": len(by_skill.get(skill.pk, [])),
        "holder_count": len(holders),
        "candidates": candidates[:SUCCESSOR_CAP],
        "qualified_count": len(qualified),
        "ready_today_count": len(ready_today),
        "coverage_ratio": coverage_ratio,
        "kt_recommended": len(holders) == 1,
    }


def succession_report(department=None):
    """Risk cards for every critical skill in scope, org or one department."""
    critical = _critical_skills_of(department)
    by_skill = _approved_by_skill()
    rows = []
    for skill_id, assessment in critical.items():
        card = succession_for_skill(assessment.skill, by_skill=by_skill)
        card["criticality_score"] = assessment.criticality_score
        card["department"] = assessment.department
        rows.append(card)
    rows.sort(key=lambda r: (-r["criticality_score"], r["skill"].name))
    return rows


# ---------------------------------------------------------------------------
# 4. Organization readiness (§9)
#    Readiness = 100 × Σ(criticality_i × coverage_i) / Σ(criticality_i)
#    i.e. the coverage of critical skills weighted by how critical each skill is.
# ---------------------------------------------------------------------------

def readiness_score(department=None):
    """0–100 headline score for a business unit or the whole organization.

    Readiness = 100 × Σ(criticality_i × coverage_i) / Σ(criticality_i).
    An uncovered high-criticality skill drags the score down more than an
    uncovered low-criticality one; marginal penalties don't shrink to noise.
    """
    by_skill = _approved_by_skill()
    crit_skills = _critical_skills_of(department, by_skill=by_skill)
    weighted_coverage = 0.0
    total_weight = 0.0
    for skill_id, assessment in crit_skills.items():
        card = succession_for_skill(assessment.skill, by_skill=by_skill)
        weighted_coverage += assessment.criticality_score * card["coverage_ratio"]
        total_weight += assessment.criticality_score
    if not total_weight:
        return 100, len(crit_skills)
    return int(round(100 * weighted_coverage / total_weight)), len(crit_skills)


def readiness_report():
    """Per-department + organization readiness with trend snapshots."""
    rows = []
    for department in Department.objects.all():
        score, n = readiness_score(department)
        rows.append(
            {
                "department": department,
                "score": score,
                "critical_skills": n,
            }
        )
    org_score, org_n = readiness_score()
    rows.append({"department": None, "score": org_score, "critical_skills": org_n})
    return rows


def snapshot_readiness():
    """Store org + per-department timestamps so the trend can be shown."""
    for department in Department.objects.all():
        score, n = readiness_score(department)
        from insights.models import ReadinessSnapshot
        ReadinessSnapshot.objects.create(
            scope=department.name, score=score, critical_skills_count=n
        )
    org_score, org_n = readiness_score()
    from insights.models import ReadinessSnapshot
    ReadinessSnapshot.objects.create(
        scope="org", score=org_score, critical_skills_count=org_n
    )


def readiness_trend(department=None, limit=12):
    from insights.models import ReadinessSnapshot
    scope = department.name if department else "org"
    return list(
        ReadinessSnapshot.objects.filter(scope=scope)
        .order_by("-created_at")[:limit]
    )


# ---------------------------------------------------------------------------
# 5. Per-employee gaps + priority (§4, §5)
# ---------------------------------------------------------------------------

def _importance_weight(importance):
    return {"critical": 20, "important": 10, "optional": 0}.get(importance, 0)


def _future_boost(skill_id):
    demand = (
        SkillFutureDemand.objects.filter(
            skill_id=skill_id,
            direction__in=(SkillFutureDemand.Direction.EMERGING, SkillFutureDemand.Direction.GROWING),
        )
        .order_by("-future_importance")
        .first()
    )
    if not demand:
        return 0
    if demand.confidence_level == SkillFutureDemand.Confidence.HIGH:
        return FUTURE_BOOST
    if demand.confidence_level == SkillFutureDemand.Confidence.MEDIUM:
        return 5
    return 2


def employee_gaps(user):
    """Current ability → role requirements → gaps, each with a priority score.

    Priority blends gap size (up to 50), business-unit criticality (up to 30),
    requirement importance (up to 20), and future demand (up to 10).
    """
    assessed = latest_assessments()
    by_skill = _approved_by_skill()
    per_user_levels = defaultdict(dict)
    for p in by_skill.values():
        for prof in p:
            per_user_levels[prof.user_id][prof.skill_id] = prof.level

    requirements = (
        TeamSkillRequirement.objects.filter(team__memberships__user=user)
        .select_related("skill", "team__department")
        .order_by("-importance")
    )
    rows = []
    seen = set()
    for req in requirements:
        skill_id = req.skill_id
        key = (skill_id, req.required_level)
        if key in seen:
            continue
        seen.add(key)
        level = per_user_levels.get(user.id, {}).get(skill_id, 0)
        if level >= req.required_level:
            continue
        missing = level == 0
        gap_size = req.required_level - level
        assessment = assessed.get(skill_id)
        crit = assessment.criticality_score if assessment else 0
        priority = min(50, gap_size * 10) + (crit * 0.3) + _importance_weight(req.importance) + _future_boost(skill_id)
        rows.append(
            {
                "skill": req.skill,
                "required_level": req.required_level,
                "level": level,
                "gap_size": gap_size if not missing else req.required_level,
                "missing": missing,
                "importance": req.get_importance_display(),
                "purpose": req.purpose,
                "criticality": crit,
                "team": req.team.name,
                "priority": int(round(priority)),
            }
        )
    rows.sort(key=lambda r: -r["priority"])
    return rows


# ---------------------------------------------------------------------------
# 6. Gap → recommendation rule set (Gap 5)
#    A simple IF condition → THEN recommended action table. No ML required.
# ---------------------------------------------------------------------------

def _org_matches(skill_id, level, by_skill=None, exclude_user_id=None):
    by_skill = by_skill or _approved_by_skill()
    return [
        p
        for p in by_skill.get(skill_id, [])
        if p.level >= level and p.user_id != exclude_user_id
    ]


def recommendation_for_gap(user, gap, by_skill=None):
    """Route one skill gap to a concrete, believable development action."""
    by_skill = by_skill or _approved_by_skill()
    skill = gap["skill"]
    exception = successions = None

    related = []
    for rel in _related_skills(skill):
        for p in by_skill.get(rel.to_skill_id, []):
            if p.user_id == user.id and p.level >= 3:
                related.append((rel.to_skill, p.level))
                break

    # Rule 1: adjacent skill exists (related through the graph at >= 3).
    if related:
        strongest = max(related, key=lambda r: r[1])
        return {
            "rule": 1,
            "action": "Targeted training / certification (short path)",
            "reason": f"You already hold {strongest[0].name} at level {strongest[1]}, "
            "which transfers into this skill — a focused course or certification "
            "should close the gap quickly.",
            "action_kind": "training",
        }

    # Rule 3: skill comfortably exists elsewhere in the organization.
    matches = _org_matches(skill.id, 4, by_skill, exclude_user_id=user.id)
    if matches:
        peer = matches[0].user
        peer_team = peer.team_memberships.first()
        peer_label = peer_team.team.name if peer_team else "another team"
        return {
            "rule": 3,
            "action": "Job rotation or shadowing",
            "reason": (
                f"{peer.get_full_name() or peer.username} in {peer_label} holds this "
                f"at proficiency {matches[0].level} — a short rotation or shadowing "
                "assignment is the fastest low-cost path."
            ),
            "action_kind": "shadowing",
        }

    # Rule 2: no related skill nearby.
    holders = _org_matches(skill.id, 3, by_skill, exclude_user_id=user.id)
    mentor = holders[0].user if holders else None
    mentor_label = f" with {mentor.get_full_name() or mentor.username}" if mentor else ""
    return {
        "rule": 2,
        "action": f"Structured course + mentoring pairing{mentor_label}",
        "reason": "You have nothing nearby in the skills graph — a structured course "
        "plus 1:1 mentoring from a current holder builds this from scratch.",
        "action_kind": "course",
    }


def development_recommendations(user, gaps=None, by_skill=None):
    """Full development plan: a recommendation for each of the user's gaps,
    plus extra flags for single-holder critical skills and emerging skills."""
    gaps = gaps if gaps is not None else employee_gaps(user)
    by_skill = by_skill or _approved_by_skill()
    rows = []
    for gap in gaps[:8]:
        recommendation = recommendation_for_gap(user, gap, by_skill)
        extras = []

        # Rule 4: critical skill with a single holder → knowledge transfer.
        if gap["criticality"] >= CRITICALITY_THRESHOLD:
            high = _high_proficiency_count(gap["skill"].pk, by_skill)
            if high <= 1:
                extras.append(
                    {
                        "action": "Knowledge-transfer project",
                        "reason": f"Only {high} person(s) here at high proficiency — "
                        "pair the current holder with 1–2 successors on a real project.",
                        "action_kind": "kt",
                    }
                )

        # Rule 5: emerging/future skill with low org-wide proficiency.
        assess = latest_assessments()
        demand = SkillFutureDemand.objects.filter(skill=gap["skill"]).order_by("-future_importance").first()
        if demand and demand.direction in (
            SkillFutureDemand.Direction.EMERGING,
            SkillFutureDemand.Direction.GROWING,
        ):
            any_holders = sum(1 for p in by_skill.get(gap["skill"].pk, []) if p.level >= 1)
            if demand.confidence_level == SkillFutureDemand.Confidence.HIGH and any_holders <= 2:
                extras.append(
                    {
                        "action": "External certification + community of practice",
                        "reason": "This is an emerging skill the company is betting on — "
                        "fund a certification and host a community of practice.",
                        "action_kind": "external",
                    }
                )

        rows.append(
            {
                **gap,
                "recommendation": recommendation["action"],
                "reason": recommendation["reason"],
                "rule": recommendation["rule"],
                "extras": extras,
            }
        )
    return rows


# ---------------------------------------------------------------------------
# 7. Future workforce needs (§10)
# ---------------------------------------------------------------------------

def future_skills():
    """Curated future demand joined with today's scarcity."""
    by_skill = _approved_by_skill()
    rows = []
    for demand in SkillFutureDemand.objects.select_related("skill").order_by("-future_importance"):
        holders = [p for p in by_skill.get(demand.skill_id, [])]
        avg_level = round(sum(p.level for p in holders) / len(holders), 1) if holders else 0
        high = _high_proficiency_count(demand.skill_id, by_skill)
        rows.append(
            {
                "demand": demand,
                "skill": demand.skill,
                "holder_count": len(holders),
                "high_proficiency": high,
                "avg_level": avg_level,
                "confidence": demand.get_confidence_level_display(),
            }
        )
    return rows


# ---------------------------------------------------------------------------
# 8. Plan / task readiness (§14)
#    Readiness = Manning % × Qualification % × Availability %
# ---------------------------------------------------------------------------

def plan_readiness(project):
    """Per-requirement and project-level readiness for a plan/project."""
    rows = []
    for team in project.teams.prefetch_related("memberships__user"):
        roster_size = team.memberships.count()
        for req in team.skill_requirements.select_related("skill"):
            people_needed = req.people_needed or 1
            member_profs = SkillProficiency.objects.filter(
                status=SkillProficiency.Status.APPROVED,
                skill_id=req.skill_id,
                user_id__in=team.memberships.values_list("user_id", flat=True),
            )
            qualified = member_profs.filter(level__gte=req.required_level)
            qualified_ids = set(qualified.values_list("user_id", flat=True))

            manning = min(1.0, roster_size / people_needed) if people_needed else 1.0
            qualification = qualified.count() / roster_size if roster_size else 0.0
            available = []
            for user_id in qualified_ids:
                team_count = TeamMembership.objects.filter(user_id=user_id).count()
                if team_count <= MAX_TEAMS_AVAILABILITY:
                    available.append(user_id)
            availability = len(available) / qualified.count() if qualified.count() else 0.0
            readiness = manning * qualification * availability

            if manning < 0.9 and qualification >= 0.9 and availability >= 0.9:
                diagnosis = "Hiring problem — not enough people (manning low)"
            elif qualification < 0.9:
                diagnosis = "Qualification problem — enough people, too few with the skill"
            elif availability < 0.9:
                diagnosis = "Availability problem — qualified people already committed"
            else:
                diagnosis = "Ready"
            rows.append(
                {
                    "team": team.name,
                    "skill": req.skill.name,
                    "required_level": req.required_level,
                    "people_needed": people_needed,
                    "roster_size": roster_size,
                    "qualified": qualified.count(),
                    "available": len(available),
                    "manning_pct": round(manning * 100),
                    "qualification_pct": round(qualification * 100),
                    "availability_pct": round(availability * 100),
                    "readiness_pct": round(readiness * 100),
                    "diagnosis": diagnosis,
                }
            )
    return rows


def project_readiness_summary(project):
    rows = plan_readiness(project)
    if not rows:
        return {}
    return {
        "manning_pct": round(sum(r["manning_pct"] for r in rows) / len(rows)),
        "qualification_pct": round(sum(r["qualification_pct"] for r in rows) / len(rows)),
        "availability_pct": round(sum(r["availability_pct"] for r in rows) / len(rows)),
        "readiness_pct": round(sum(r["readiness_pct"] for r in rows) / len(rows)),
    }


# ---------------------------------------------------------------------------
# 9. What-If sandbox (§15)
#    Read-only simulations: employee departure and skill adoption.
# ---------------------------------------------------------------------------

def simulate_departure(user):
    """What happens to critical skills if this employee leaves tomorrow?"""
    by_skill = _approved_by_skill()
    assessments = latest_assessments()
    impacts = []
    # by_skill is keyed by skill_id; collect this user's holder-level proficiencies.
    leaving = {
        p.skill_id: p
        for profs in by_skill.values()
        for p in profs
        if p.user_id == user.id and p.level >= SUCCESSOR_HOLDER_LEVEL
    }
    for skill_id, prof in leaving.items():
        skill = prof.skill
        assessment = assessments.get(skill_id)
        if not assessment or assessment.criticality_score < CRITICALITY_THRESHOLD:
            continue
        holders = [p for p in by_skill.get(skill_id, []) if p.level >= SUCCESSOR_HOLDER_LEVEL and p.user_id != user.id]
        high = [p for p in by_skill.get(skill_id, []) if p.level >= 4 and p.user_id != user.id]
        before_count = _holder_count(skill_id, by_skill)
        coverage_before = succession_for_skill(skill, by_skill=by_skill)["coverage_ratio"]
        card_after = succession_for_skill(skill, by_skill={sk: [p for p in profs if p.user_id not in {user.id}] for sk, profs in by_skill.items()})
        impacts.append(
            {
                "skill": skill,
                "level": prof.level,
                "holders_after": len(holders),
                "high_proficiency_after": len(high),
                "coverage_before": coverage_before,
                "coverage_after": card_after["coverage_ratio"],
                "kt_needed": not holders,
                "recommendation": (
                    "Hire or train immediately — skill would have no holders."
                    if not holders
                    else (
                        "Accelerate knowledge transfer + successor readiness."
                        if len(high) <= 1
                        else "Uncovered but a pool of candidates exists."
                    )
                ),
            }
        )
    impacts.sort(key=lambda r: (-r["coverage_after"], r["skill"].name))
    return impacts


def simulate_skill_adoption(skill):
    """What if the organization adopted/staffed a specific skill?"""
    by_skill = _approved_by_skill()
    required = 3
    qualified = _org_matches(skill.id, required, by_skill)
    holders = by_skill.get(skill.id, [])
    adjacent_pool = []
    for rel in _related_skills(skill):
        for p in by_skill.get(rel.to_skill_id, []):
            if p.level >= 2 and p.user_id not in {q.user_id for q in qualified}:
                adjacent_pool.append((p.user, rel.to_skill, p.level))
    adjacent_pool.sort(key=lambda t: -t[2])
    assessments = latest_assessments()
    top_assessment = max(
        (assessments[sid] for sid in assessments if sid == skill.pk),
        default=None,
    )
    return {
        "skill": skill,
        "qualified": qualified,
        "qualified_count": len(qualified),
        "holder_count": len(holders),
        "adjacent_pool": adjacent_pool[:SUCCESSOR_CAP],
        "adjacent_pool_size": len(adjacent_pool),
        "rarity_label": rarity(skill.pk, by_skill)[0],
        "criticality_score": top_assessment.criticality_score if top_assessment else None,
        "est_training_months": MONTHS_PER_LEVEL * 2 if adjacent_pool else MONTHS_PER_LEVEL * 4,
        "hiring_recommended": len(qualified) < 2,
    }


# ---------------------------------------------------------------------------
# 10. Leadership cascade (§17)
#     The "AI" draft is a deterministic template pipeline over live
#     readiness/gap/feedback data — no randomness, no external calls.
#     Counts are routed through the anonymization guards so strategy text stays
#     consistent with the Phase 3 disclosure policy.
# ---------------------------------------------------------------------------

NEXT_INITIATIVE_LEVEL = {"board": "csuite", "csuite": "department", "department": "team"}


def feedback_risk_rollup():
    """Unresolved team flags aggregated by issue type for the dashboard."""
    from insights.models import TeamFeedback

    flags = (
        TeamFeedback.objects.filter(resolved=False)
        .select_related("raised_by", "initiative__parent")
        .order_by("-created_at")
    )
    buckets = {}
    for flag in flags:
        bucket = buckets.setdefault(
            flag.issue_type, {"issue_type": flag.issue_type, "label": flag.get_issue_type_display(), "count": 0, "flags": []}
        )
        bucket["count"] += 1
        bucket["flags"].append(flag)
    return list(buckets.values())


def _draft_objectives(score, at_risk, unresolved_count):
    objectives = []
    if score < 80:
        objectives.append(
            f"Raise organization readiness from {score}/100 to at least 80 by "
            "closing critical-skill coverage gaps."
        )
    else:
        objectives.append(
            f"Sustain organization readiness at {score}/100."
        )
    if at_risk:
        top = ", ".join(r["skill"].name for r in at_risk[:3])
        objectives.append(
            f"Diversify the top knowledge bottlenecks ({top}) with hiring or training."
        )
    else:
        objectives.append("Keep knowledge-bottleneck skills staffed as demand grows.")
    objectives.append(
        f"Close the {unresolved_count} unresolved team flag(s) this quarter."
    )
    return objectives


def _draft_actions(at_risk, unresolved_count):
    actions = []
    for r in at_risk[:3]:
        holders = guarded_count(r["holder_count"], r["holder_count"])
        if r["shortfall"] > 0:
            shortfall = guarded_shortfall(r["demand"], r["holder_count"])
            actions.append(
                f"Staff {r['skill'].name}: hire or train to cover a "
                f"{shortfall}-slot shortfall."
            )
        else:
            actions.append(
                f"Diversify {r['skill'].name}: grow the {holders}-person holder pool."
            )
    if unresolved_count:
        actions.append(
            f"Prioritize and resolve {unresolved_count} team-flagged readiness issue(s)."
        )
    actions.append("Review progress against the readiness trend at the next operating review.")
    return actions


def draft_initiative_content(initiative):
    """Deterministic draft text for an initiative from live org data.

    Only the parent's *approved* content is inherited (``inherited_content``) —
    never a parent's draft.
    """
    from insights.models import TeamFeedback

    lines = [f"INITIATIVE: {initiative.title}", ""]
    inherited = initiative.inherited_content().strip()
    if inherited:
        lines.append("INHERITED CONTEXT")
        lines.append(inherited)
        lines.append("")
    lines.append("CURRENT STATE")
    score, critical_n = readiness_score()
    at_risk = at_risk_skills()
    unresolved_count = TeamFeedback.objects.filter(resolved=False).count()
    lines.append(
        f"- Organization readiness is {score}/100 with {critical_n} critical "
        "skill(s) in scope."
    )
    if at_risk:
        top = ", ".join(r["skill"].name for r in at_risk[:3])
        lines.append(f"- Top knowledge risks: {top}.")
    else:
        lines.append("- No skills currently flagged as knowledge bottlenecks.")
    lines.append(
        f"- {unresolved_count} unresolved team flag(s) raised by team leads."
    )
    lines.append("OBJECTIVES")
    for i, text in enumerate(_draft_objectives(score, at_risk, unresolved_count), 1):
        lines.append(f"{i}. {text}")
    lines.append("ACTIONS")
    for i, text in enumerate(_draft_actions(at_risk, unresolved_count), 1):
        lines.append(f"{i}. {text}")
    return "\n".join(lines)