from collections import defaultdict

from skills.models import SkillProficiency


def team_coverage(team):
    """A team's requirements resolved against its members' approved skills."""
    member_ids = set(team.memberships.values_list("user_id", flat=True))
    requirements = team.skill_requirements.select_related("skill")

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