from datetime import date

from django.test import TestCase
from django.urls import reverse

from accounts.models import Tier
from core.test_utils import make_team, make_user
from insights.models import StrategicInitiative, TeamFeedback
from skills.models import (
    Skill,
    SkillCategory,
    SkillCriticalityAssessment,
    SkillProficiency,
    SkillRelationship,
)
from teams.models import Department, TeamMembership, TeamSkillRequirement

from . import services


def _months_between(a, b):
    return (b.year - a.year) * 12 + (b.month - a.month)


class InsightsServicesTests(TestCase):
    def setUp(self):
        self.category = SkillCategory.objects.create(name="Testing")
        self.python = Skill.objects.create(name="Python", category=self.category)
        self.aws = Skill.objects.create(name="AWS", category=self.category)
        self.legacy = Skill.objects.create(name="Legacy", category=self.category)

        self.mgr = make_user("smoketest_mgr", Tier.TEAM_MANAGER)
        self.team = make_team("smoketest_ibteam", manager=self.mgr)

        self.alice = self._proficient("alice", {"python": 5, "aws": 4, "legacy": 4})
        self.bob = self._proficient("bob", {"python": 3})
        self.carol = self._proficient("carol", {"aws": 5})
        self.dave = self._proficient("dave", {"python": 5})
        self.eve = self._proficient("eve", {"aws": 4})
        self.grace = self._proficient("grace", {"python": 2})
        self.henry = self._proficient("henry", {"python": 1})
        self.liam = self._proficient("liam", {"python": 1})

        self.alice.expected_leave_date = date(2030, 6, 1)
        self.bob.expected_leave_date = date(2030, 3, 15)
        self.grace.expected_leave_date = date(2029, 12, 1)
        self.alice.save()
        self.bob.save()
        self.grace.save()

        # Python: heavy demand, enough holders -> shortfall, not low bus-factor.
        TeamSkillRequirement.objects.create(
            team=self.team,
            skill=self.python,
            required_level=4,
            importance=TeamSkillRequirement.Importance.CRITICAL,
            people_needed=8,
        )
        # Legacy: one holder -> low bus-factor.
        TeamSkillRequirement.objects.create(
            team=self.team,
            skill=self.legacy,
            required_level=4,
            importance=TeamSkillRequirement.Importance.CRITICAL,
            people_needed=1,
        )
        # AWS: adequate supply -> not at risk.
        TeamSkillRequirement.objects.create(
            team=self.team,
            skill=self.aws,
            required_level=3,
            importance=TeamSkillRequirement.Importance.IMPORTANT,
            people_needed=2,
        )

    def _proficient(self, username, skills):
        user = make_user(username)
        for skill_name, level in skills.items():
            SkillProficiency.objects.create(
                user=user,
                skill=getattr(self, skill_name),
                level=level,
                status=SkillProficiency.Status.APPROVED,
            )
        return user

    def _row_for(self, rows, skill):
        return next(r for r in rows if r["skill"].pk == skill.pk)

    def test_bottlenecks_flag_shortfall_and_bus_factor_but_not_healthy(self):
        rows = services.at_risk_skills()
        names = {r["skill"].name for r in rows}
        self.assertEqual(names, {"Python", "Legacy"})

        python = self._row_for(rows, self.python)
        self.assertEqual(python["shortfall"], 2)
        self.assertFalse(python["low_bus_factor"])
        self.assertTrue(python["critical"])

        legacy = self._row_for(rows, self.legacy)
        self.assertTrue(legacy["low_bus_factor"])
        self.assertEqual(legacy["shortfall"], 0)

    def test_expected_stays_computes_months_and_leaves_missing_unset(self):
        stays = {rows["user"].username: rows for rows in services.expected_stays()}
        today = date.today()
        self.assertEqual(
            stays["alice"]["months_remaining"],
            _months_between(today, self.alice.expected_leave_date),
        )
        self.assertIsNone(stays["carol"]["months_remaining"])

    def test_skill_depletion_horizon_is_last_holder_leave(self):
        rows = services.skill_depletion()
        by_name = {r["skill"].name: r for r in rows}
        today = date.today()

        legacy = by_name["Legacy"]
        self.assertFalse(legacy["unknown"])
        self.assertEqual(legacy["last_leave_date"], date(2030, 6, 1))
        self.assertEqual(
            legacy["months_left"], _months_between(today, date(2030, 6, 1))
        )

        python = by_name["Python"]
        self.assertTrue(python["unknown"])
        self.assertEqual(python["last_leave_date"], date(2030, 6, 1))

    def test_successors_rank_by_pace_and_cap(self):
        rows = {r["skill"].name: r for r in services.successors()}
        self.assertEqual(list(rows), ["Python"])
        candidates = rows["Python"]["candidates"]
        self.assertEqual(len(candidates), 3)
        self.assertEqual([c["name"] for c in candidates], ["bob", "grace", "henry"])
        self.assertEqual(
            [c["months"] for c in candidates],
            [services.MONTHS_PER_LEVEL * 1, services.MONTHS_PER_LEVEL * 2,
             services.MONTHS_PER_LEVEL * 3],
        )


class StrategicServicesTests(TestCase):
    """Readiness (weighted coverage) and what-if departure simulations."""

    def setUp(self):
        self.category = SkillCategory.objects.create(name="Strategic testing")
        self.dept = Department.objects.create(name="Smoketest Strat")
        self.aws = Skill.objects.create(name="Strat AWS", category=self.category)
        self.adjacent = Skill.objects.create(
            name="Strat AWS Basics", category=self.category
        )
        SkillRelationship.objects.create(
            from_skill=self.aws,
            to_skill=self.adjacent,
            kind=SkillRelationship.Kind.TRANSFERS,
            weight=4,
        )
        self.alice = make_user("strat_alice")
        SkillProficiency.objects.create(
            user=self.alice,
            skill=self.aws,
            level=4,
            status=SkillProficiency.Status.APPROVED,
        )
        SkillCriticalityAssessment.objects.create(
            department=self.dept,
            skill=self.aws,
            business_impact=5,
            strategic_relevance=5,
            time_to_replace_months=24,
            criticality_score=80,
            version=1,
        )

    def _add_qualified_successor(self):
        bob = make_user("strat_bob")
        SkillProficiency.objects.create(
            user=bob, skill=self.aws, level=2, status=SkillProficiency.Status.APPROVED
        )
        SkillProficiency.objects.create(
            user=bob,
            skill=self.adjacent,
            level=5,
            status=SkillProficiency.Status.APPROVED,
        )
        return bob

    def test_uncovered_critical_skill_readiness_sags(self):
        self.assertEqual(services.readiness_score(self.dept), (0, 1))

    def test_successor_coverage_raises_readiness_to_full(self):
        self._add_qualified_successor()
        self.assertEqual(services.readiness_score(self.dept), (100, 1))

    def test_readiness_report_lists_departments_and_org(self):
        report = services.readiness_report()
        by_scope = {r["department"]: r for r in report}
        self.assertIn(self.dept, by_scope)
        self.assertIn(None, by_scope)
        self.assertEqual(by_scope[self.dept]["critical_skills"], 1)
        self.assertEqual(by_scope[None]["critical_skills"], 1)

    def test_simulate_departure_flags_unbacked_critical_skill(self):
        impacts = services.simulate_departure(self.alice)
        self.assertEqual(len(impacts), 1)
        self.assertEqual(impacts[0]["skill"], self.aws)
        self.assertTrue(impacts[0]["kt_needed"])
        self.assertEqual(impacts[0]["holders_after"], 0)

    def test_simulate_departure_is_empty_for_non_holders(self):
        bystander = make_user("strat_bystander")
        self.assertEqual(services.simulate_departure(bystander), [])

    def test_set_criticality_factors_versions_and_recomputes(self):
        updated = services.set_criticality_factors(
            department=self.dept,
            skill=self.aws,
            business_impact=5,
            strategic_relevance=5,
            time_to_replace_months=12,
        )
        self.assertEqual(updated.version, 2)
        # 40 + 20 + 10 + 16 (one high-proficiency holder) = 86
        self.assertEqual(updated.criticality_score, 86)
        self.assertEqual(
            SkillCriticalityAssessment.objects.filter(
                skill=self.aws, department=self.dept
            ).count(),
            2,
        )

    def test_set_criticality_factors_noop_when_unchanged(self):
        # setUp already assessed v1 with exactly these factors.
        same = services.set_criticality_factors(
            department=self.dept,
            skill=self.aws,
            business_impact=5,
            strategic_relevance=5,
            time_to_replace_months=24,
        )
        self.assertEqual(same.version, 1)
        self.assertEqual(
            SkillCriticalityAssessment.objects.filter(
                skill=self.aws, department=self.dept
            ).count(),
            1,
        )


class InsightsViewTests(TestCase):
    def setUp(self):
        self.leader = make_user("smoketest_leader", Tier.LEADERSHIP)
        self.manager = make_user("smoketest_manager", Tier.TEAM_MANAGER)
        self.employee = make_user("smoketest_employee")
        self.leader_client = self._client(self.leader)
        self.manager_client = self._client(self.manager)
        self.employee_client = self._client(self.employee)

    def _client(self, user):
        client = type(self.client)()
        client.force_login(user)
        return client

    def test_insights_leadership_only(self):
        self.assertEqual(self.leader_client.get(reverse("insights")).status_code, 200)
        self.assertEqual(self.manager_client.get(reverse("insights")).status_code, 403)
        self.assertEqual(self.employee_client.get(reverse("insights")).status_code, 403)

    def test_dashboard_renders_expected_sections(self):
        response = self.leader_client.get(reverse("insights"))
        content = response.content.decode()
        for section in ("Knowledge bottlenecks", "Skill depletion", "Successor readiness", "Expected stay"):
            self.assertIn(section, content)

    def test_dashboard_renders_strategic_sections(self):
        response = self.leader_client.get(reverse("insights"))
        content = response.content.decode()
        for section in (
"Org readiness",
            "Risk matrix",
            "Succession risk cards",
            "Future skills",
            "What-if sandbox",
        ):
            self.assertIn(section, content)

    def test_what_if_departure_simulation_renders_impact(self):
        from skills.models import Skill, SkillCategory, SkillCriticalityAssessment, SkillProficiency
        from teams.models import Department

        category = SkillCategory.objects.create(name="What-if testing")
        dept = Department.objects.create(name="Smoketest Whatif")
        skill = Skill.objects.create(name="Whatif Core", category=category)
        holder = make_user("smoketest_holder")
        SkillProficiency.objects.create(
            user=holder,
            skill=skill,
            level=4,
            status=SkillProficiency.Status.APPROVED,
        )
        SkillCriticalityAssessment.objects.create(
            department=dept, skill=skill, criticality_score=80, version=1
        )
        response = self.leader_client.get(
            reverse("insights"), {"departure_user_id": holder.pk}
        )
        self.assertContains(response, "Whatif Core")
        self.assertContains(response, "holders after")


class CriticalityEditTests(TestCase):
    def setUp(self):
        self.leader = make_user("smoketest_leader", Tier.LEADERSHIP)
        self.manager = make_user("smoketest_manager", Tier.TEAM_MANAGER)
        self.employee = make_user("smoketest_employee")
        self.leader_client = self._client(self.leader)
        self.manager_client = self._client(self.manager)
        self.employee_client = self._client(self.employee)

        self.category = SkillCategory.objects.create(name="Criticality edits")
        self.dept = Department.objects.create(name="Smoketest CritEdits")
        self.skill = Skill.objects.create(
            name="Smoketest Critical", category=self.category
        )
        self.current = SkillCriticalityAssessment.objects.create(
            department=self.dept,
            skill=self.skill,
            business_impact=4,
            strategic_relevance=4,
            time_to_replace_months=3,
            criticality_score=66,
            version=1,
        )

    def _client(self, user):
        client = type(self.client)()
        client.force_login(user)
        return client

    def test_list_and_edit_leadership_only(self):
        list_url = reverse("criticality_list")
        edit_url = reverse("criticality_edit", args=[self.skill.pk, self.dept.pk])
        self.assertEqual(self.leader_client.get(list_url).status_code, 200)
        self.assertEqual(self.manager_client.get(list_url).status_code, 403)
        self.assertEqual(self.employee_client.get(list_url).status_code, 403)
        self.assertEqual(self.manager_client.get(edit_url).status_code, 403)
        self.assertEqual(self.employee_client.get(edit_url).status_code, 403)

    def test_list_page_lists_skills(self):
        response = self.leader_client.get(reverse("criticality_list"))
        self.assertContains(response, self.skill.name)

    def test_edit_appends_version_and_recomputes(self):
        response = self.leader_client.post(
            reverse("criticality_edit", args=[self.skill.pk, self.dept.pk]),
            {
                "business_impact": "5",
                "strategic_relevance": "5",
                "time_to_replace_months": "18",
            },
        )
        self.assertRedirects(
            response, reverse("criticality_edit", args=[self.skill.pk, self.dept.pk])
        )
        latest = (
            SkillCriticalityAssessment.objects.filter(
                skill=self.skill, department=self.dept
            )
            .order_by("-version")
            .first()
        )
        self.assertEqual(latest.version, 2)
        self.assertEqual(latest.business_impact, 5)
        self.assertEqual(latest.time_to_replace_months, 18)
        # 40 + 20 + 15 + 16 (concentration floor) = 91
        self.assertEqual(latest.criticality_score, 91)
        # history preserved
        self.assertEqual(
            SkillCriticalityAssessment.objects.filter(
                skill=self.skill, department=self.dept
            ).count(),
            2,
        )

    def test_edit_noop_when_factors_unchanged(self):
        self.leader_client.post(
            reverse("criticality_edit", args=[self.skill.pk, self.dept.pk]),
            {
                "business_impact": "4",
                "strategic_relevance": "4",
                "time_to_replace_months": "3",
            },
        )
        latest = (
            SkillCriticalityAssessment.objects.filter(
                skill=self.skill, department=self.dept
            )
            .order_by("-version")
            .first()
        )
        self.assertEqual(latest.pk, self.current.pk)
        self.assertEqual(latest.version, 1)

    def test_edit_creates_when_no_assessment_exists(self):
        other = Department.objects.create(name="Smoketest CritEdits2")
        self.leader_client.post(
            reverse("criticality_edit", args=[self.skill.pk, other.pk]),
            {
                "business_impact": "3",
                "strategic_relevance": "3",
                "time_to_replace_months": "12",
            },
        )
        row = SkillCriticalityAssessment.objects.get(skill=self.skill, department=other)
        self.assertEqual(row.version, 1)
        # 24 + 12 + 10 + 16 (concentration floor) = 62
        self.assertEqual(row.criticality_score, 62)


class AnonymizationGuardTests(TestCase):
    """Unit checks for the count/name coarsening helpers."""

    def test_counts_masked_boundary(self):
        self.assertFalse(services.counts_masked(0))  # empty group: nothing to hide
        self.assertFalse(services.counts_masked(5))
        self.assertTrue(services.counts_masked(1))
        self.assertTrue(services.counts_masked(services.ANON_GROUP_SIZE - 1))

    def test_guarded_count_exact_when_group_large_enough(self):
        self.assertEqual(services.guarded_count(6, 6), 6)
        self.assertEqual(services.guarded_count(2, 5), 2)

    def test_guarded_count_coarsens_small_nonzero_group(self):
        self.assertEqual(services.guarded_count(3, 3), "1–4")
        # A single-person group must never collapse to the exact "1–1".
        self.assertEqual(services.guarded_count(1, 1), "1–4")
        self.assertEqual(services.guarded_count(0, 2), 0)  # empty group stays exact

    def test_guarded_shortfall_cannot_leak_holder_count(self):
        self.assertEqual(services.guarded_shortfall(9, 6), 3)  # unmasked exact
        self.assertEqual(services.guarded_shortfall(4, 3), "0–3")  # hides exact 1
        self.assertEqual(services.guarded_shortfall(1, 1), 0)

    def test_guard_display_name_masks_by_default(self):
        masked = services.guard_display_name("Alice Smith")
        self.assertNotIn("Alice", masked)
        self.assertIn("masked", masked)
        self.assertEqual(
            services.guard_display_name("Alice Smith", drill_down=True),
            "Alice Smith",
        )


class AnonymizationViewTests(TestCase):
    """Phase 3: <5-person groups are coarsened on the leadership dashboard;
    groups of >=5 people show exact counts and names."""

    def setUp(self):
        self.leader = make_user("anon_leader", Tier.LEADERSHIP)
        self.manager = make_user("anon_manager", Tier.TEAM_MANAGER)
        self.client = type(self.client)()
        self.client.force_login(self.leader)

        self.category = SkillCategory.objects.create(name="Anon view testing")
        self.dept = Department.objects.create(name="Smoketest AnonViews")
        self.small_team = make_team("Anon small team", manager=self.manager)
        self.large_team = make_team("Anon large team", manager=self.manager)

        self.small_skill = Skill.objects.create(name="Anon Core", category=self.category)
        small_holders = []
        for i in range(3):
            user = make_user(f"anon_holder{i}")
            small_holders.append(user)
            SkillProficiency.objects.create(
                user=user,
                skill=self.small_skill,
                level=4,
                status=SkillProficiency.Status.APPROVED,
            )
        for user in small_holders:
            TeamMembership.objects.create(
                team=self.small_team, user=user, role=TeamMembership.Role.MEMBER
            )
        TeamSkillRequirement.objects.create(
            team=self.small_team,
            skill=self.small_skill,
            required_level=4,
            importance=TeamSkillRequirement.Importance.CRITICAL,
            people_needed=4,
        )
        SkillCriticalityAssessment.objects.create(
            department=self.dept,
            skill=self.small_skill,
            business_impact=5,
            strategic_relevance=5,
            time_to_replace_months=24,
            criticality_score=88,
            version=1,
        )

        self.large_skill = Skill.objects.create(
            name="Anon Widely Held", category=self.category
        )
        large_holders = []
        for i in range(6):
            user = make_user(f"anon_wide{i}")
            large_holders.append(user)
            SkillProficiency.objects.create(
                user=user,
                skill=self.large_skill,
                level=3,
                status=SkillProficiency.Status.APPROVED,
            )
        for user in large_holders:
            TeamMembership.objects.create(
                team=self.large_team, user=user, role=TeamMembership.Role.MEMBER
            )
        TeamSkillRequirement.objects.create(
            team=self.large_team,
            skill=self.large_skill,
            required_level=4,
            importance=TeamSkillRequirement.Importance.IMPORTANT,
            people_needed=9,
        )
        SkillCriticalityAssessment.objects.create(
            department=self.dept,
            skill=self.large_skill,
            business_impact=5,
            strategic_relevance=5,
            time_to_replace_months=24,
            criticality_score=90,
            version=1,
        )

    def _small_row(self, safe_rows):
        return next(r for r in safe_rows if r["skill"].pk == self.small_skill.pk)

    def _large_row(self, safe_rows):
        return next(r for r in safe_rows if r["skill"].pk == self.large_skill.pk)

    def test_bottlenecks_small_group_coarsened_large_exact(self):
        from insights.views import _safe_bottlenecks

        rows = _safe_bottlenecks(services.at_risk_skills())
        small = self._small_row(rows)
        self.assertTrue(small["masked"])
        self.assertEqual(small["holder_count_display"], "1–4")
        # exact shortfall of 1 is hidden behind a range
        self.assertEqual(small["shortfall_display"], "0–3")

        large = self._large_row(rows)
        self.assertFalse(large["masked"])
        self.assertEqual(large["holder_count_display"], 6)
        self.assertEqual(large["shortfall_display"], 3)

    def test_depletion_strips_holder_details_for_small_group(self):
        from insights.views import _safe_depletion

        rows = _safe_depletion(services.skill_depletion())
        small = self._small_row(rows)
        self.assertTrue(small["masked"])
        self.assertEqual(small["holder_count"], "1–4")
        self.assertEqual(small["holders"], [])

        large = self._large_row(rows)
        self.assertFalse(large["masked"])
        self.assertEqual(len(large["holders"]), 6)

    def test_risk_matrix_rarity_and_counts_masked_for_small_group(self):
        from insights.views import _safe_risk_matrix

        rows = _safe_risk_matrix(services.risk_matrix())
        small = self._small_row(rows)
        self.assertTrue(small["masked"])
        self.assertEqual(small["holder_count"], "1–4")
        self.assertEqual(small["high_proficiency"], "1–4")
        self.assertEqual(small["rarity"], "masked (small group)")

        large = self._large_row(rows)
        self.assertFalse(large["masked"])
        self.assertEqual(large["holder_count"], 6)

    def test_succession_cards_mask_small_group_and_keep_large(self):
        from insights.views import _safe_succession_cards

        cards = _safe_succession_cards(services.succession_report())
        small = next(c for c in cards if c["skill"].pk == self.small_skill.pk)
        self.assertTrue(small["masked"])
        self.assertEqual(small["holder_count"], "1–4")

        large = next(c for c in cards if c["skill"].pk == self.large_skill.pk)
        self.assertFalse(large["masked"])
        self.assertEqual(large["holder_count"], 6)

    def test_successor_names_exact_for_large_pool(self):
        from insights.views import _safe_successors

        rows = _safe_successors(services.successors())
        large = self._large_row(rows)
        self.assertFalse(large["masked"])
        self.assertEqual(large["candidate_count"], 6)
        # the top SUCCESSOR_CAP names render unmasked for a group >= 5
        self.assertEqual(
            [c["name_display"] for c in large["candidates"]],
            [f"anon_wide{i}" for i in range(3)],
        )

    def test_dashboard_html_coarsens_small_group_and_shows_large(self):
        response = self.client.get(reverse("insights"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Anonymization: aggregates over groups smaller than 5")
        # depletion pill for the masked small group
        self.assertContains(response, "1–4 holders &mdash; details masked")
        self.assertContains(response, "Too few holders to disclose their leave dates")
        # large-group candidate names remain visible in the successor list
        self.assertContains(response, "anon_wide0")


class CascadeTests(TestCase):
    """Phase 4: draft → approve → cascade flow and team-feedback rollup."""

    def setUp(self):
        self.leader = make_user("cascade_leader", Tier.LEADERSHIP)
        self.manager = make_user("cascade_manager", Tier.TEAM_MANAGER)
        self.employee = make_user("cascade_employee")
        self.leader_client = self._client(self.leader)
        self.manager_client = self._client(self.manager)
        self.employee_client = self._client(self.employee)

    def _client(self, user):
        client = type(self.client)()
        client.force_login(user)
        return client

    def _post(self, client, name, *args, **data):
        return client.post(reverse(name, args=args), data)

    def test_cascade_and_feedback_gating(self):
        self.assertEqual(self.leader_client.get(reverse("cascade_list")).status_code, 200)
        self.assertEqual(self.manager_client.get(reverse("cascade_list")).status_code, 403)
        self.assertEqual(self.employee_client.get(reverse("cascade_list")).status_code, 403)

        feedback_url = reverse("feedback_list")
        self.assertEqual(self.leader_client.get(feedback_url).status_code, 200)
        self.assertEqual(self.manager_client.get(feedback_url).status_code, 200)
        self.assertEqual(self.employee_client.get(feedback_url).status_code, 403)

        self.assertEqual(
            self._post(self.leader_client, "feedback_create").status_code, 403
        )
        self.assertEqual(
            self._post(self.employee_client, "feedback_resolve", 1).status_code, 403
        )

    def test_create_initiative_generates_deterministic_draft(self):
        self._post(
            self.leader_client,
            "initiative_create",
            title="Grow cloud capability",
            level=StrategicInitiative.Level.BOARD,
            parent="",
        )
        initiative = StrategicInitiative.objects.get(title="Grow cloud capability")
        self.assertEqual(initiative.status, StrategicInitiative.Status.DRAFT)
        self.assertEqual(initiative.owner, self.leader)
        self.assertIn("CURRENT STATE", initiative.ai_draft_content)
        self.assertIn("Organization readiness", initiative.ai_draft_content)
        self.assertIn("Grow cloud capability", initiative.ai_draft_content)
        self.assertIn("OBJECTIVES", initiative.ai_draft_content)
        # deterministic: same inputs → same draft
        self._post(
            self.leader_client,
            "initiative_create",
            title="Grow cloud capability",
            level=StrategicInitiative.Level.BOARD,
            parent="",
        )
        second = StrategicInitiative.objects.filter(
            title="Grow cloud capability"
        ).order_by("id").last()
        self.assertEqual(initiative.ai_draft_content, second.ai_draft_content)

    def test_approve_copies_draft_and_sets_metadata(self):
        self._post(
            self.leader_client,
            "initiative_create",
            title="Talent pipeline",
            level=StrategicInitiative.Level.CSUITE,
            parent="",
        )
        initiative = StrategicInitiative.objects.get(title="Talent pipeline")
        self.assertRedirects(
            self._post(self.leader_client, "initiative_approve", initiative.pk),
            reverse("cascade_list"),
        )
        initiative.refresh_from_db()
        self.assertEqual(initiative.status, StrategicInitiative.Status.APPROVED)
        self.assertEqual(initiative.approved_content, initiative.ai_draft_content)
        self.assertEqual(initiative.approved_by, self.leader)
        self.assertIsNotNone(initiative.approved_at)

    def test_approve_requires_a_draft(self):
        initiative = StrategicInitiative.objects.create(
            owner=self.leader,
            title="No draft yet",
            level=StrategicInitiative.Level.DEPARTMENT,
        )
        self._post(self.leader_client, "initiative_approve", initiative.pk)
        initiative.refresh_from_db()
        self.assertEqual(initiative.status, StrategicInitiative.Status.DRAFT)
        self.assertEqual(initiative.approved_content, "")

    def test_cascade_requires_approved_parent(self):
        draft = StrategicInitiative.objects.create(
            owner=self.leader,
            title="Unapproved plan",
            level=StrategicInitiative.Level.BOARD,
        )
        self._post(
            self.leader_client, "initiative_cascade", draft.pk, title="Child val"
        )
        self.assertEqual(StrategicInitiative.objects.count(), 1)

    def test_cascade_inherits_only_approved_content(self):
        board = StrategicInitiative.objects.create(
            owner=self.leader,
            title="Board strategy",
            level=StrategicInitiative.Level.BOARD,
        )
        board.ai_draft_content = services.draft_initiative_content(board)
        board.approved_content = board.ai_draft_content
        board.status = StrategicInitiative.Status.APPROVED
        board.approved_by = self.leader
        board.save()

        self._post(
            self.leader_client,
            "initiative_cascade",
            board.pk,
            title="C-Suite execution",
        )
        child = StrategicInitiative.objects.get(level=StrategicInitiative.Level.CSUITE)
        self.assertEqual(child.parent, board)
        self.assertEqual(child.status, StrategicInitiative.Status.DRAFT)
        self.assertIn("INHERITED CONTEXT", child.ai_draft_content)
        self.assertIn(board.approved_content, child.ai_draft_content)

    def test_cascade_stops_at_team_level(self):
        team = StrategicInitiative.objects.create(
            owner=self.leader,
            title="Team plan",
            level=StrategicInitiative.Level.TEAM,
            status=StrategicInitiative.Status.APPROVED,
            approved_content="stop here",
        )
        self._post(self.leader_client, "initiative_cascade", team.pk, title="Lower")
        self.assertEqual(StrategicInitiative.objects.count(), 1)

    def test_manager_raises_flag_and_leadership_resolves_and_rolls_up(self):
        self._post(
            self.manager_client,
            "feedback_create",
            issue_type=TeamFeedback.IssueType.SKILL,
            initiative="",
            description="We have no Python experts left in my team.",
        )
        flag = TeamFeedback.objects.get()
        self.assertFalse(flag.resolved)
        self.assertEqual(flag.raised_by, self.manager)

        rollup = services.feedback_risk_rollup()
        self.assertEqual(len(rollup), 1)
        self.assertEqual(rollup[0]["issue_type"], TeamFeedback.IssueType.SKILL)
        self.assertEqual(rollup[0]["count"], 1)

        response = self.leader_client.get(reverse("insights"))
        self.assertContains(response, "Unresolved team flags")
        self.assertContains(response, "Skill shortfall")
        self.assertContains(response, "Python experts")

        self._post(
            self.leader_client,
            "feedback_resolve",
            flag.pk,
            resolution="Backfill headcount approved.",
        )
        flag.refresh_from_db()
        self.assertTrue(flag.resolved)
        self.assertEqual(flag.resolution, "Backfill headcount approved.")
        self.assertIsNotNone(flag.resolved_at)
        self.assertEqual(services.feedback_risk_rollup(), [])


class DepartmentScopeTests(TestCase):
    """Phase 5: leadership analytics rescope to a chosen department while
    Phase 3 anonymization still applies within that scope."""

    def setUp(self):
        self.leader = make_user("scope_leader", Tier.LEADERSHIP)
        self.manager = make_user("scope_manager", Tier.TEAM_MANAGER)
        self.client = type(self.client)()
        self.client.force_login(self.leader)

        self.category = SkillCategory.objects.create(name="Scope testing")

        self.dept_a = Department.objects.create(name="Scope Alpha")
        self.dept_b = Department.objects.create(name="Scope Beta")

        self.team_a = make_team("Scope team A", manager=self.manager)
        self.team_a.department = self.dept_a
        self.team_a.save()
        self.team_b = make_team("Scope team B", manager=self.manager)
        self.team_b.department = self.dept_b
        self.team_b.save()

        self.skill_a = Skill.objects.create(
            name="Scope Alpha Pipeline", category=self.category
        )
        holders_a = [make_user(f"scope_a{i}") for i in range(6)]
        for u in holders_a:
            TeamMembership.objects.create(
                team=self.team_a, user=u, role=TeamMembership.Role.MEMBER
            )
            SkillProficiency.objects.create(
                user=u,
                skill=self.skill_a,
                level=4,
                status=SkillProficiency.Status.APPROVED,
            )
        TeamSkillRequirement.objects.create(
            team=self.team_a,
            skill=self.skill_a,
            required_level=4,
            importance=TeamSkillRequirement.Importance.CRITICAL,
            people_needed=8,
        )
        SkillCriticalityAssessment.objects.create(
            department=self.dept_a,
            skill=self.skill_a,
            business_impact=5,
            strategic_relevance=5,
            time_to_replace_months=24,
            criticality_score=80,
            version=1,
        )

        self.skill_small = Skill.objects.create(
            name="Scope Alpha Small", category=self.category
        )
        small_a = [make_user(f"scope_small{i}") for i in range(3)]
        for u in small_a:
            TeamMembership.objects.create(
                team=self.team_a, user=u, role=TeamMembership.Role.MEMBER
            )
            SkillProficiency.objects.create(
                user=u,
                skill=self.skill_small,
                level=3,
                status=SkillProficiency.Status.APPROVED,
            )
        extra = make_user("scope_small_extra")
        SkillProficiency.objects.create(
            user=extra,
            skill=self.skill_small,
            level=3,
            status=SkillProficiency.Status.APPROVED,
        )
        # incipient-level holder in dept A gives a successor to project
        incipient = make_user("scope_small_incipient")
        TeamMembership.objects.create(
            team=self.team_a, user=incipient, role=TeamMembership.Role.MEMBER
        )
        SkillProficiency.objects.create(
            user=incipient,
            skill=self.skill_small,
            level=2,
            status=SkillProficiency.Status.APPROVED,
        )
        TeamSkillRequirement.objects.create(
            team=self.team_a,
            skill=self.skill_small,
            required_level=3,
            importance=TeamSkillRequirement.Importance.CRITICAL,
            people_needed=6,
        )
        SkillCriticalityAssessment.objects.create(
            department=self.dept_a,
            skill=self.skill_small,
            business_impact=5,
            strategic_relevance=5,
            time_to_replace_months=24,
            criticality_score=75,
            version=1,
        )

        self.skill_b = Skill.objects.create(
            name="Scope Beta Data", category=self.category
        )
        holders_b = [make_user(f"scope_b{i}") for i in range(6)]
        for u in holders_b:
            TeamMembership.objects.create(
                team=self.team_b, user=u, role=TeamMembership.Role.MEMBER
            )
            SkillProficiency.objects.create(
                user=u,
                skill=self.skill_b,
                level=3,
                status=SkillProficiency.Status.APPROVED,
            )
        TeamSkillRequirement.objects.create(
            team=self.team_b,
            skill=self.skill_b,
            required_level=3,
            importance=TeamSkillRequirement.Importance.IMPORTANT,
            people_needed=9,
        )
        SkillCriticalityAssessment.objects.create(
            department=self.dept_b,
            skill=self.skill_b,
            business_impact=4,
            strategic_relevance=4,
            time_to_replace_months=24,
            criticality_score=70,
            version=1,
        )

    def test_risk_matrix_scoped_to_department(self):
        alpha = {r["skill"].name for r in services.risk_matrix(self.dept_a)}
        self.assertEqual(
            alpha, {"Scope Alpha Pipeline", "Scope Alpha Small"}
        )
        beta = {r["skill"].name for r in services.risk_matrix(self.dept_b)}
        self.assertEqual(beta, {"Scope Beta Data"})
        # no filter → every department's skills
        org = {r["skill"].name for r in services.risk_matrix()}
        self.assertEqual(
            org,
            {"Scope Alpha Pipeline", "Scope Alpha Small", "Scope Beta Data"},
        )

    def test_succession_report_scoped_to_department(self):
        alpha = {c["skill"].name for c in services.succession_report(self.dept_a)}
        self.assertEqual(alpha, {"Scope Alpha Pipeline", "Scope Alpha Small"})
        beta = {c["skill"].name for c in services.succession_report(self.dept_b)}
        self.assertEqual(beta, {"Scope Beta Data"})

    def test_bottlenecks_scope_demand_and_holder_pool(self):
        alpha = {r["skill"].name for r in services.at_risk_skills(self.dept_a)}
        self.assertEqual(alpha, {"Scope Alpha Pipeline", "Scope Alpha Small"})
        self.assertNotIn("Scope Beta Data", alpha)
        # dept B only sees its own requirement as at risk
        beta = {r["skill"].name for r in services.at_risk_skills(self.dept_b)}
        self.assertEqual(beta, {"Scope Beta Data"})

    def test_depletion_and_successors_rescope_with_department(self):
        alpha_dep = {r["skill"].name for r in services.skill_depletion(self.dept_a)}
        self.assertEqual(alpha_dep, {"Scope Alpha Pipeline", "Scope Alpha Small"})
        alpha_succ = {r["skill"].name for r in services.successors(self.dept_a)}
        # Pipeline holders already sit at the required level, so only the
        # incipient pool produces successor projections — but Beta stays out.
        self.assertEqual(alpha_succ, {"Scope Alpha Small"})
        scoped_dep = {r["skill"].name for r in services.skill_depletion(self.dept_b)}
        self.assertEqual(scoped_dep, {"Scope Beta Data"})

    def test_holder_pool_scoped_to_department_membership(self):
        org_row = next(
            r
            for r in services.at_risk_skills()
            if r["skill"].pk == self.skill_small.pk
        )
        # 3 dept-A holders at level 3+ + 1 outsider + 1 incipient = 5 org-wide
        self.assertEqual(org_row["holder_count"], 5)
        alpha_row = next(
            r
            for r in services.at_risk_skills(self.dept_a)
            if r["skill"].pk == self.skill_small.pk
        )
        # dept A sees only its own 4 members — the outsider stays out of scope
        self.assertEqual(alpha_row["holder_count"], 4)

    def test_dashboard_scopes_sections_and_keeps_org_default(self):
        org = self.client.get(reverse("insights"))
        self.assertEqual(org.status_code, 200)
        self.assertContains(org, "Org readiness")
        self.assertEqual(
            {r["skill"].name for r in org.context["risk_matrix"]},
            {"Scope Alpha Pipeline", "Scope Alpha Small", "Scope Beta Data"},
        )

        scoped = self.client.get(reverse("insights"), {"dept": self.dept_a.pk})
        self.assertEqual(scoped.status_code, 200)
        self.assertContains(scoped, "Scope Alpha readiness")
        self.assertEqual(
            {r["skill"].name for r in scoped.context["risk_matrix"]},
            {"Scope Alpha Pipeline", "Scope Alpha Small"},
        )
        self.assertEqual(
            {r["skill"].name for r in scoped.context["bottlenecks"]},
            {"Scope Alpha Pipeline", "Scope Alpha Small"},
        )
        self.assertEqual(
            {c["skill"].name for c in scoped.context["succession_cards"]},
            {"Scope Alpha Pipeline", "Scope Alpha Small"},
        )
        # the org headline is replaced by the department's own readiness card
        self.assertEqual(len(scoped.context["readiness"]), 1)
        self.assertEqual(scoped.context["readiness"][0]["department"], self.dept_a)

    def test_department_scoping_still_anonymizes_small_groups(self):
        scoped = self.client.get(reverse("insights"), {"dept": self.dept_a.pk})
        self.assertContains(scoped, "1–4 holders &mdash; details masked")
        self.assertContains(scoped, "Too few holders to disclose their leave dates")
        self.assertContains(scoped, "small group &mdash; details masked")


class PromotionGapTests(TestCase):
    """Phase 6: next-position (purpose=promotion) requirements surface as
    promotion gaps in the employee gap list."""

    def setUp(self):
        self.category = SkillCategory.objects.create(name="Promo testing")
        self.python = Skill.objects.create(name="Python Promo", category=self.category)
        self.javascript = Skill.objects.create(
            name="JavaScript Promo", category=self.category
        )
        self.mgr = make_user("promo_manager", Tier.TEAM_MANAGER)
        self.team = make_team("Promo team", manager=self.mgr)

        self.user = make_user("promo_employee")
        TeamMembership.objects.create(
            team=self.team, user=self.user, role=TeamMembership.Role.MEMBER
        )

        # current-role gap: Python at required 4, user holds 3
        TeamSkillRequirement.objects.create(
            team=self.team,
            skill=self.python,
            required_level=4,
            importance=TeamSkillRequirement.Importance.IMPORTANT,
            purpose=TeamSkillRequirement.Purpose.CURRENT,
        )
        # next-position gap: JavaScript required 3, user holds nothing
        TeamSkillRequirement.objects.create(
            team=self.team,
            skill=self.javascript,
            required_level=3,
            importance=TeamSkillRequirement.Importance.CRITICAL,
            purpose=TeamSkillRequirement.Purpose.PROMOTION,
        )
        SkillProficiency.objects.create(
            user=self.user,
            skill=self.python,
            level=3,
            status=SkillProficiency.Status.APPROVED,
        )

    def _gap(self, gaps, skill):
        return next(r for r in gaps if r["skill"].pk == skill.pk)

    def test_employee_gaps_carry_purpose(self):
        gaps = services.employee_gaps(self.user)
        self.assertEqual(self._gap(gaps, self.python)["purpose"], "current")
        self.assertEqual(self._gap(gaps, self.javascript)["purpose"], "promotion")

    def test_promotion_gap_appears_in_development_plan(self):
        gaps = services.employee_gaps(self.user)
        plan = services.development_recommendations(self.user, gaps)
        items = {r["skill"].name: r for r in plan}
        self.assertIn("JavaScript Promo", items)
        self.assertEqual(items["JavaScript Promo"]["purpose"], "promotion")

    def test_me_page_labels_promotion_gap(self):
        self.client.force_login(self.user)
        response = self.client.get(reverse("my_skills"))
        self.assertContains(response, "next position")