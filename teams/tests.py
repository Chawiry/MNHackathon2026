from django.test import TestCase
from django.urls import reverse

from accounts.models import Tier, User
from core.test_utils import make_team, make_user

from .models import Team, TeamMembership, TeamSkillRequirement
from .services import requirement_candidates, team_coverage


class RequirementPermissionTests(TestCase):
    def setUp(self):
        from skills.models import Skill, SkillCategory

        self.category = SkillCategory.objects.create(name="Testing")
        self.skill = Skill.objects.create(name="Python", category=self.category)

        self.leader = make_user("smoketest_leader", Tier.LEADERSHIP)
        self.mgr_a = make_user("smoketest_mgra", Tier.TEAM_MANAGER)
        self.mgr_b = make_user("smoketest_mgrb", Tier.TEAM_MANAGER)
        self.emp_a = make_user("smoketest_empa")
        self.team_a = make_team("smoketest_atea", manager=self.mgr_a, members=[self.emp_a])
        self.team_b = make_team("smoketest_bteam", manager=self.mgr_b)

        self.leader_client = self._client(self.leader)
        self.mgr_a_client = self._client(self.mgr_a)
        self.mgr_b_client = self._client(self.mgr_b)
        self.emp = self._client(self.emp_a)

    def _client(self, user):
        client = type(self.client)()
        client.force_login(user)
        return client

    def test_manager_adds_requirement_to_own_team(self):
        response = self.mgr_a_client.post(
            reverse("add_team_requirement", args=[self.team_a.pk]),
            {"skill": self.skill.pk, "required_level": 3, "importance": "important"},
        )
        self.assertRedirects(response, reverse("team_list"))
        self.assertEqual(
            TeamSkillRequirement.objects.filter(team=self.team_a).count(), 1
        )

    def test_manager_blocked_on_other_team(self):
        response = self.mgr_b_client.post(
            reverse("add_team_requirement", args=[self.team_a.pk]),
            {"skill": self.skill.pk, "required_level": 3},
        )
        self.assertEqual(response.status_code, 403)
        self.assertFalse(
            TeamSkillRequirement.objects.filter(team=self.team_a).exists()
        )

    def test_leadership_adds_requirement_to_any_team(self):
        response = self.leader_client.post(
            reverse("add_team_requirement", args=[self.team_b.pk]),
            {"skill": self.skill.pk, "required_level": 4, "importance": "critical"},
        )
        self.assertEqual(response.status_code, 302)
        self.assertEqual(
            TeamSkillRequirement.objects.filter(team=self.team_b).count(), 1
        )

    def test_employee_blocked_on_requirements(self):
        response = self.emp.post(
            reverse("add_team_requirement", args=[self.team_a.pk]),
            {"skill": self.skill.pk, "required_level": 3},
        )
        self.assertEqual(response.status_code, 403)

    def test_remove_requirement_permission(self):
        req = TeamSkillRequirement.objects.create(
            team=self.team_a, skill=self.skill, required_level=3
        )
        blocked = self.mgr_b_client.post(
            reverse("remove_team_requirement", args=[req.pk])
        )
        self.assertEqual(blocked.status_code, 403)
        self.assertTrue(TeamSkillRequirement.objects.filter(pk=req.pk).exists())

        ok = self.mgr_a_client.post(reverse("remove_team_requirement", args=[req.pk]))
        self.assertEqual(ok.status_code, 302)
        self.assertFalse(TeamSkillRequirement.objects.filter(pk=req.pk).exists())

    def test_new_team_has_no_requirements(self):
        team = Team.objects.create(name="smoketest_fresh")
        self.assertEqual(team.skill_requirements.count(), 0)

    def test_open_redirect_rejected(self):
        response = self.mgr_a_client.post(
            reverse("add_team_requirement", args=[self.team_a.pk]),
            {"skill": self.skill.pk, "required_level": 3, "next": "https://evil.example/x"},
        )
        self.assertRedirects(response, reverse("team_list"))


class TeamRosterPermissionTests(TestCase):
    def setUp(self):
        self.leader = make_user("smoketest_leader", Tier.LEADERSHIP)
        self.mgr_a = make_user("smoketest_mgra", Tier.TEAM_MANAGER)
        self.mgr_b = make_user("smoketest_mgrb", Tier.TEAM_MANAGER)
        self.emp_a = make_user("smoketest_empa")
        self.emp_b = make_user("smoketest_empb")
        self.team_a = make_team("smoketest_atea", manager=self.mgr_a, members=[self.emp_a])
        self.team_b = make_team("smoketest_bteam", manager=self.mgr_b)

        self.mgr_a_client = self._client(self.mgr_a)
        self.mgr_b_client = self._client(self.mgr_b)

    def _client(self, user):
        client = type(self.client)()
        client.force_login(user)
        return client

    def test_manager_removes_member_from_own_team(self):
        self.mgr_a_client.post(
            reverse("remove_member",
                    args=[TeamMembership.objects.get(team=self.team_a, user=self.emp_a).pk])
        )
        self.assertFalse(self.team_a.memberships.filter(user=self.emp_a).exists())

    def test_manager_blocked_removing_from_other_team(self):
        membership = TeamMembership.objects.get(team=self.team_a, user=self.emp_a)
        response = self.mgr_b_client.post(
            reverse("remove_member", args=[membership.pk])
        )
        self.assertEqual(response.status_code, 403)
        self.assertTrue(self.team_a.memberships.filter(user=self.emp_a).exists())

    def test_cannot_remove_last_manager(self):
        response = self.mgr_a_client.post(
            reverse("remove_member",
                    args=[TeamMembership.objects.get(team=self.team_a, user=self.mgr_a).pk])
        )
        self.assertEqual(response.status_code, 302)
        self.assertTrue(self.team_a.memberships.filter(user=self.mgr_a).exists())

    def test_manager_changes_role_own_team(self):
        membership = TeamMembership.objects.get(team=self.team_a, user=self.emp_a)
        self.mgr_a_client.post(
            reverse("change_role", args=[membership.pk]), {"role": TeamMembership.Role.MANAGER}
        )
        membership.refresh_from_db()
        self.assertEqual(membership.role, TeamMembership.Role.MANAGER)

    def test_manager_blocked_changing_role_other_team(self):
        membership = TeamMembership.objects.get(team=self.team_a, user=self.emp_a)
        response = self.mgr_b_client.post(
            reverse("change_role", args=[membership.pk]), {"role": TeamMembership.Role.MANAGER}
        )
        self.assertEqual(response.status_code, 403)

    def test_manager_cannot_change_own_role_or_remove_self_if_last_manager(self):
        membership = TeamMembership.objects.get(team=self.team_a, user=self.mgr_a)
        self.mgr_a_client.post(reverse("remove_member", args=[membership.pk]))
        membership.refresh_from_db()
        self.assertEqual(membership.role, TeamMembership.Role.MANAGER)


class TeamCoverageTests(TestCase):
    def setUp(self):
        from skills.models import Skill, SkillCategory, SkillProficiency

        self.category = SkillCategory.objects.create(name="Testing")
        self.skill = Skill.objects.create(name="Python", category=self.category)
        self.skill2 = Skill.objects.create(name="Django", category=self.category)

        self.mgr = make_user("smoketest_mgr", Tier.TEAM_MANAGER)
        self.emp = make_user("smoketest_emp")
        self.team = make_team("smoketest_cov", manager=self.mgr, members=[self.emp])

    def test_coverage_uses_only_own_team_requirements(self):
        TeamSkillRequirement.objects.create(team=self.team, skill=self.skill, required_level=3)
        rows = team_coverage(self.team)
        self.assertEqual({row["skill"] for row in rows}, {self.skill.name})

    def test_coverage_met_when_member_meets_requirement(self):
        from skills.models import SkillProficiency

        SkillProficiency.objects.create(
            user=self.emp, skill=self.skill, level=4, status=SkillProficiency.Status.APPROVED
        )
        TeamSkillRequirement.objects.create(team=self.team, skill=self.skill, required_level=3)
        row = team_coverage(self.team)[0]
        self.assertEqual(row["coverage_status"], "Met")

    def test_coverage_gap_when_no_one_meets(self):
        TeamSkillRequirement.objects.create(team=self.team, skill=self.skill, required_level=5)
        row = team_coverage(self.team)[0]
        self.assertEqual(row["coverage_status"], "Gap")

    def test_approval_unknown_rows_do_not_count(self):
        from skills.models import SkillProficiency

        SkillProficiency.objects.create(
            user=self.emp, skill=self.skill, level=5, status=SkillProficiency.Status.PENDING
        )
        TeamSkillRequirement.objects.create(team=self.team, skill=self.skill, required_level=3)
        row = team_coverage(self.team)[0]
        self.assertEqual(row["coverage_status"], "Gap")


class CreateMemberTests(TestCase):
    def setUp(self):
        self.leader = make_user("smoketest_leader", Tier.LEADERSHIP)
        self.mgr_a = make_user("smoketest_mgra", Tier.TEAM_MANAGER)
        self.mgr_b = make_user("smoketest_mgrb", Tier.TEAM_MANAGER)
        self.team_a = make_team("smoketest_atea", manager=self.mgr_a)
        self.team_b = make_team("smoketest_bteam", manager=self.mgr_b)

        self.mgr_a_client = self._client(self.mgr_a)
        self.mgr_b_client = self._client(self.mgr_b)
        self.leader_client = self._client(self.leader)

    def _client(self, user):
        client = type(self.client)()
        client.force_login(user)
        return client

    def _post(self, client, team, username="smoketest_newbie"):
        return client.post(
            reverse("create_member"),
            {
                "username": username,
                "first_name": "New",
                "job_title": "Engineer",
                "password": "testpass123",
                "team": team.pk,
            },
        )

    def test_employee_cannot_create_member(self):
        employee = make_user("smoketest_employee")
        self.assertEqual(self._client(employee).get(reverse("team_list")).status_code, 403)

    def test_manager_creates_employee_in_managed_team(self):
        response = self._post(self.mgr_a_client, self.team_a)
        self.assertRedirects(response, reverse("team_list"))
        user = User.objects.get(username="smoketest_newbie")
        self.assertEqual(user.tier, Tier.EMPLOYEE)
        self.assertTrue(self.team_a.memberships.filter(user=user, role=TeamMembership.Role.MEMBER).exists())

    def test_manager_cannot_create_member_for_unmanaged_team(self):
        response = self._post(self.mgr_b_client, self.team_a, username="smoketest_other")
        self.assertEqual(response.status_code, 302)
        self.assertFalse(User.objects.filter(username="smoketest_other").exists())

    def test_leadership_creates_member_for_any_team(self):
        response = self._post(self.leader_client, self.team_b, username="smoketest_leaderhire")
        self.assertRedirects(response, reverse("user_list"))
        user = User.objects.get(username="smoketest_leaderhire")
        self.assertTrue(self.team_b.memberships.filter(user=user).exists())


class GigAllocationTests(TestCase):
    def setUp(self):
        from skills.models import Skill, SkillCategory, SkillProficiency

        self.category = SkillCategory.objects.create(name="Testing")
        self.skill = Skill.objects.create(name="Python", category=self.category)
        self.leader = make_user("smoketest_leader", Tier.LEADERSHIP)
        self.mgr_a = make_user("smoketest_mgra", Tier.TEAM_MANAGER)
        self.mgr_b = make_user("smoketest_mgrb", Tier.TEAM_MANAGER)
        self.inhouse = make_user("smoketest_inhouse")
        self.free_expert = make_user("smoketest_freeexp")
        self.busy_expert = make_user("smoketest_busyexp")
        self.under_qualified = make_user("smoketest_underq")

        self.team_a = make_team("smoketest_giga", manager=self.mgr_a, members=[self.inhouse])
        self.team_b = make_team("smoketest_gigb", manager=self.mgr_b)
        self.req = TeamSkillRequirement.objects.create(
            team=self.team_a, skill=self.skill, required_level=3, people_needed=2
        )

        def proficiency(user, level):
            SkillProficiency.objects.create(
                user=user,
                skill=self.skill,
                level=level,
                status=SkillProficiency.Status.APPROVED,
            )

        proficiency(self.inhouse, 4)
        proficiency(self.free_expert, 5)
        proficiency(self.busy_expert, 5)
        proficiency(self.under_qualified, 1)
        make_team("smoketest_busy1", manager=self.mgr_a, members=[self.busy_expert])
        make_team("smoketest_busy2", manager=self.mgr_a, members=[self.busy_expert])

        self.mgr_a_client = self._client(self.mgr_a)
        self.mgr_b_client = self._client(self.mgr_b)
        self.leader_client = self._client(self.leader)

    def _client(self, user):
        client = type(self.client)()
        client.force_login(user)
        return client

    def test_candidates_are_qualified_and_exclude_team_members(self):
        candidates = requirement_candidates(self.req)
        names = {c.user.username for c in candidates}
        self.assertIn("smoketest_freeexp", names)
        self.assertNotIn("smoketest_inhouse", names)
        self.assertNotIn("smoketest_underq", names)

    def test_candidates_rank_experts_by_availability(self):
        candidates = requirement_candidates(self.req)
        self.assertEqual(candidates[0].user.username, "smoketest_freeexp")
        self.assertEqual(candidates[1].user.username, "smoketest_busyexp")

    def test_add_candidate_creates_membership(self):
        response = self.mgr_a_client.post(
            reverse("add_candidate", args=[self.team_a.pk]),
            {"user_id": self.free_expert.pk},
        )
        self.assertRedirects(response, reverse("team_list"))
        self.assertTrue(
            self.team_a.memberships.filter(
                user=self.free_expert, role=TeamMembership.Role.MEMBER
            ).exists()
        )

    def test_add_candidate_deduplicates(self):
        self.mgr_a_client.post(
            reverse("add_candidate", args=[self.team_a.pk]),
            {"user_id": self.inhouse.pk},
        )
        self.assertEqual(self.team_a.memberships.filter(user=self.inhouse).count(), 1)

    def test_manager_blocked_adding_to_other_team(self):
        response = self.mgr_b_client.post(
            reverse("add_candidate", args=[self.team_a.pk]),
            {"user_id": self.free_expert.pk},
        )
        self.assertEqual(response.status_code, 403)
        self.assertFalse(
            self.team_a.memberships.filter(user=self.free_expert).exists()
        )

    def test_employee_blocked(self):
        employee = make_user("smoketest_employee")
        client = self._client(employee)
        response = client.post(
            reverse("add_candidate", args=[self.team_a.pk]),
            {"user_id": self.free_expert.pk},
        )
        self.assertEqual(response.status_code, 403)

    def test_leadership_adds_anywhere(self):
        response = self.leader_client.post(
            reverse("add_candidate", args=[self.team_b.pk]),
            {"user_id": self.free_expert.pk},
        )
        self.assertEqual(response.status_code, 302)
        self.assertTrue(self.team_b.memberships.filter(user=self.free_expert).exists())

    def test_team_list_renders_suited_candidates(self):
        response = self.mgr_a_client.get(reverse("team_list"))
        self.assertEqual(response.status_code, 200)
        content = response.content.decode()
        self.assertIn("Suited candidates", content)
        self.assertIn(self.free_expert.username, content)

    def test_candidates_hidden_when_requirement_fully_covered(self):
        from skills.models import SkillProficiency

        inhouse = SkillProficiency.objects.get(user=self.inhouse, skill=self.skill)
        inhouse.level = 5
        inhouse.save()
        extra = make_user("smoketest_extra")
        make_team("smoketest_aux", manager=self.mgr_a, members=[extra])
        SkillProficiency.objects.create(
            user=extra,
            skill=self.skill,
            level=3,
            status=SkillProficiency.Status.APPROVED,
        )
        self.req.people_needed = 5
        self.req.save()
        # inhouse + extra = 2 met of 5 -> still a gap, block shows.
        response = self.mgr_a_client.get(reverse("team_list"))
        self.assertIn("Suited candidates", response.content.decode())

        self.req.people_needed = 1
        self.req.save()
        # inhouse now meets the only needed spot -> block hidden.
        response = self.mgr_a_client.get(reverse("team_list"))
        self.assertNotIn("Suited candidates", response.content.decode())