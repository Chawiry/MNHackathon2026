"""Invariant tests for the seed_demo command (plan Phase 1)."""

from django.core.management import call_command
from django.test import TestCase

from accounts.models import Tier, User
from insights.models import ReadinessSnapshot
from profiles.models import DevelopmentActivity, ExperienceEntry, PerformanceReview
from skills.models import SkillCriticalityAssessment, SkillFutureDemand, SkillProficiency, SkillRelationship
from teams.models import Department, Team, TeamSkillRequirement


class SeedInvariantTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        call_command("seed_demo", verbosity=0)

    def _proficiencies(self, skill_name, min_level=1):
        return SkillProficiency.objects.filter(
            skill__name=skill_name, level__gte=min_level, status=SkillProficiency.Status.APPROVED
        )

    def test_org_shape(self):
        self.assertGreaterEqual(Department.objects.count(), 4)
        self.assertGreaterEqual(Team.objects.count(), 8)
        users = User.objects.count()
        self.assertTrue(40 <= users <= 60, f"user count {users} outside 40–60")

    def test_at_least_one_small_team(self):
        small = [
            t.name for t in Team.objects.all() if t.memberships.count() <= 4
        ]
        self.assertTrue(small, "expected at least one team with <= 4 people")

    def test_skill_graph_has_edges(self):
        self.assertGreaterEqual(SkillRelationship.objects.count(), 25)
        kinds = set(SkillRelationship.objects.values_list("kind", flat=True))
        self.assertIn("related", kinds)
        self.assertIn("prerequisite", kinds)
        self.assertIn("transfers", kinds)

    def test_generative_ai_is_emerging_and_scarce(self):
        demand = SkillFutureDemand.objects.filter(
            skill__name="Generative AI / LLM", direction=SkillFutureDemand.Direction.EMERGING
        ).first()
        self.assertIsNotNone(demand)
        self.assertEqual(demand.confidence_level, SkillFutureDemand.Confidence.HIGH)
        high = self._proficiencies("Generative AI / LLM", min_level=4).count()
        self.assertLessEqual(high, 2, "expected 1–2 high-proficiency GenAI holders")

    def test_concentration_risk_exists(self):
        critical_skill_ids = {
            a.skill_id
            for a in SkillCriticalityAssessment.objects.filter(criticality_score__gte=60)
        }
        self.assertTrue(critical_skill_ids, "expected at least one critical (>=60) skill")

    def test_leave_dates_drive_depletion_inputs(self):
        self.assertTrue(User.objects.filter(expected_leave_date__isnull=False).exists())

    def test_readiness_snapshots_seeded(self):
        self.assertGreaterEqual(ReadinessSnapshot.objects.count(), 5)

    def test_criticality_assessed_for_teams(self):
        self.assertGreaterEqual(SkillCriticalityAssessment.objects.count(), 1)

    def test_demo_accounts_exist_with_correct_tiers(self):
        for username, tier in {
            "alex.rivera": Tier.LEADERSHIP,
            "sam.lee": Tier.TEAM_MANAGER,
            "jordan.mendez": Tier.EMPLOYEE,
        }.items():
            user = User.objects.get(username=username)
            self.assertEqual(user.tier, tier)
            self.assertTrue(user.check_password("Testpass123!"))

    def test_demo_manager_manages_platform_engineering(self):
        sam = User.objects.get(username="sam.lee")
        from teams.models import TeamMembership

        membership = TeamMembership.objects.get(user=sam)
        self.assertEqual(membership.team.name, "Platform Engineering")
        self.assertEqual(membership.role, TeamMembership.Role.MANAGER)

    def test_promotion_requirements_seeded(self):
        self.assertTrue(
            TeamSkillRequirement.objects.filter(
                purpose=TeamSkillRequirement.Purpose.PROMOTION
            ).exists()
        )

    def test_profile_entries_seeded(self):
        self.assertTrue(DevelopmentActivity.objects.exists())
        self.assertTrue(ExperienceEntry.objects.exists())
        self.assertTrue(PerformanceReview.objects.exists())


class SeedRepeatabilityTests(TestCase):
    def test_seed_command_runs_twice_cleanly(self):
        call_command("seed_demo", verbosity=0)
        first_users = User.objects.count()
        first_profs = SkillProficiency.objects.count()
        call_command("seed_demo", verbosity=0)
        self.assertEqual(User.objects.count(), first_users)
        self.assertEqual(SkillProficiency.objects.count(), first_profs)
        self.assertEqual(SkillRelationship.objects.count(), 33)