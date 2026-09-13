from django.test import TestCase
from django.urls import reverse

from accounts.models import Tier
from core.test_utils import make_team, make_user
from projects.models import Project
from skills.models import Skill, SkillCategory, SkillProficiency
from teams.models import Team, TeamMembership


class ProjectCreationTests(TestCase):
    def setUp(self):
        self.leader = make_user("smoketest_leader", Tier.LEADERSHIP)
        self.mgr = make_user("smoketest_mgr", Tier.TEAM_MANAGER)
        self.emp = make_user("smoketest_emp")
        self.leader_client = self._client(self.leader)
        self.mgr_client = self._client(self.mgr)
        self.emp_client = self._client(self.emp)

    def _client(self, user):
        client = type(self.client)()
        client.force_login(user)
        return client

    def test_create_project_spawns_team_and_manager(self):
        response = self.leader_client.post(
            reverse("create_project"),
            {
                "name": "smoketest_proj",
                "status": "active",
                "description": "",
                "start_date": "",
                "end_date": "",
                "team_name": "",
                "manager": self.mgr.pk,
            },
        )
        project = Project.objects.get(name="smoketest_proj")
        self.assertRedirects(response, reverse("project_detail", args=[project.pk]))
        self.assertEqual(project.teams.count(), 1)
        team = project.teams.first()
        self.assertEqual(team.skill_requirements.count(), 0)
        self.assertTrue(
            team.memberships.filter(user=self.mgr, role=TeamMembership.Role.MANAGER).exists()
        )

    def test_only_leadership_can_create_project(self):
        blocked = self.mgr_client.post(reverse("create_project"), {"name": "x"})
        self.assertEqual(blocked.status_code, 403)
        self.assertFalse(Project.objects.filter(name="x").exists())

    def test_manager_cannot_view_projects(self):
        self.assertEqual(self.mgr_client.get(reverse("project_list")).status_code, 403)

    def test_employee_cannot_view_projects(self):
        self.assertEqual(self.emp_client.get(reverse("project_list")).status_code, 403)

    def test_add_team_to_project(self):
        project = Project.objects.create(name="smoketest_proj2", status=Project.Status.ACTIVE)
        response = self.leader_client.post(
            reverse("add_team", args=[project.pk]),
            {"name": "smoketest_eagle", "manager": self.mgr.pk},
        )
        self.assertRedirects(response, reverse("project_detail", args=[project.pk]))
        team = project.teams.get(name="smoketest_eagle")
        self.assertTrue(
            team.memberships.filter(user=self.mgr, role=TeamMembership.Role.MANAGER).exists()
        )

    def test_remove_team_redirects_to_project(self):
        project = Project.objects.create(name="smoketest_proj3", status=Project.Status.ACTIVE)
        team = Team.objects.create(name="smoketest_gone", project=project)
        response = self.leader_client.post(reverse("remove_team", args=[team.pk]))
        self.assertRedirects(response, reverse("project_detail", args=[project.pk]))
        self.assertFalse(project.teams.filter(pk=team.pk).exists())


class ProjectCoverageSummaryTests(TestCase):
    def setUp(self):
        self.leader = make_user("smoketest_leader", Tier.LEADERSHIP)
        self.mgr = make_user("smoketest_mgr", Tier.TEAM_MANAGER)
        self.emp = make_user("smoketest_emp")
        self.client.force_login(self.leader)

        self.category = SkillCategory.objects.create(name="Testing")
        self.skill = Skill.objects.create(name="Python", category=self.category)
        self.project = Project.objects.create(name="smoketest_pcov", status=Project.Status.ACTIVE)
        self.team = Team.objects.create(name="smoketest_cov", project=self.project)
        TeamMembership.objects.create(
            team=self.team, user=self.mgr, role=TeamMembership.Role.MANAGER
        )
        TeamMembership.objects.create(team=self.team, user=self.emp, role=TeamMembership.Role.MEMBER)

    def test_project_list_shows_coverage_summary(self):
        from teams.models import TeamSkillRequirement

        TeamSkillRequirement.objects.create(team=self.team, skill=self.skill, required_level=3)
        SkillProficiency.objects.create(
            user=self.emp, skill=self.skill, level=4, status=SkillProficiency.Status.APPROVED
        )
        response = self.client.get(reverse("project_list"))
        self.assertContains(response, "1 met")

    def test_project_detail_shows_team_coverage_and_requirements(self):
        from teams.models import TeamSkillRequirement

        TeamSkillRequirement.objects.create(team=self.team, skill=self.skill, required_level=3)
        response = self.client.get(reverse("project_detail", args=[self.project.pk]))
        self.assertContains(response, self.skill.name)
        self.assertContains(response, "Skill requirements")

    def test_project_detail_renders_suited_candidates(self):
        from teams.models import Team, TeamSkillRequirement

        SkillProficiency.objects.create(
            user=self.emp, skill=self.skill, level=4, status=SkillProficiency.Status.APPROVED
        )
        other = make_user("smoketest_other")
        team2 = Team.objects.create(name="smoketest_otherteam")
        TeamMembership.objects.create(
            team=team2, user=other, role=TeamMembership.Role.MEMBER
        )
        SkillProficiency.objects.create(
            user=other, skill=self.skill, level=4, status=SkillProficiency.Status.APPROVED
        )
        TeamSkillRequirement.objects.create(team=self.team, skill=self.skill, required_level=3)
        response = self.client.get(reverse("project_detail", args=[self.project.pk]))
        content = response.content.decode()
        self.assertIn("Suited candidates", content)
        self.assertIn(other.username, content)