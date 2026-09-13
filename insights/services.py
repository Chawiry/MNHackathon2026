"""Organization-wide analytics for leadership.

All insights are derived from the live data model:

- bottlenecks: low bus-factor skills (few holders) and supply/demand shortfalls
- expected stays: leadership-set expected leave dates for every active user
- skill depletion: when a skill could be lost entirely (last holder leaves)
- successor readiness: estimated months-to-required-level using a configurable
  pace (MONTHS_PER_LEVEL months to gain one proficiency level).
"""

from collections import defaultdict
from datetime import date

from django.utils import timezone

from accounts.models import User
from skills.models import Skill, SkillProficiency
from teams.models import TeamSkillRequirement

MONTHS_PER_LEVEL = 6
BUS_FACTOR_THRESHOLD = 2
SUCCESSOR_CAP = 3


def _months_between(from_date, to_date):
    return (to_date.year - from_date.year) * 12 + (to_date.month - from_date.month)


def _approved_by_skill():
    proficiencies = SkillProficiency.objects.filter(
        status=SkillProficiency.Status.APPROVED
    ).select_related("skill", "user")
    by_skill = defaultdict(list)
    for p in proficiencies:
        by_skill[p.skill_id].append(p)
    return dict(by_skill)


def at_risk_skills():
    """Skills flagged as knowledge bottlenecks.

    A skill is at risk when it has a low bus factor (<= BUS_FACTOR_THRESHOLD
    holders) or when org-wide demand slots exceed the number of holders.
    """
    requirements = TeamSkillRequirement.objects.select_related("skill")
    demand = defaultdict(int)
    required_level = {}
    critical = set()
    for r in requirements:
        demand[r.skill_id] += r.people_needed or 1
        level = required_level.get(r.skill_id)
        if level is None or r.required_level > level:
            required_level[r.skill_id] = r.required_level
        if r.importance == TeamSkillRequirement.Importance.CRITICAL:
            critical.add(r.skill_id)

    by_skill = _approved_by_skill()
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


def skill_depletion():
    """When the company could lose each at-risk skill entirely.

    Uses the last holder's expected leave date as the horizon; flagged as
    unknown when any holder has no expected leave date set.
    """
    today = timezone.localdate()
    by_skill = _approved_by_skill()
    rows = []
    for entry in at_risk_skills():
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


def successors():
    """Estimated time-to-readiness for people below an at-risk skill's level."""
    by_skill = _approved_by_skill()
    rows = []
    for entry in at_risk_skills():
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
                    "candidates": candidates[:SUCCESSOR_CAP],
                }
            )
    rows.sort(key=lambda r: (not r["critical"], r["skill"].name))
    return rows