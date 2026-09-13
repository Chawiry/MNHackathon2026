from datetime import date

from django.test import TestCase
from django.urls import reverse

from accounts.models import Tier
from core.test_utils import make_team, make_user
from skills.models import Skill, SkillCategory, SkillProficiency
from teams.models import TeamSkillRequirement

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