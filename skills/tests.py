from django.test import TestCase
from django.urls import reverse

from accounts.models import Tier
from core.test_utils import make_team, make_user
from teams.models import TeamMembership

from .models import Certificate, CertificateAward, Skill, SkillCategory, SkillProficiency


class SkillSetupMixin:
    def setUp(self):
        self.category = SkillCategory.objects.create(name="Testing")
        self.skill = Skill.objects.create(name="Python", category=self.category)
        self.cert = Certificate.objects.create(name="Python Expert", issuer="Demo Corp")

        self.leader = make_user("smoketest_leader", Tier.LEADERSHIP)
        self.mgr_a = make_user("smoketest_mgra", Tier.TEAM_MANAGER)
        self.mgr_b = make_user("smoketest_mgrb", Tier.TEAM_MANAGER)
        self.emp_a = make_user("smoketest_empa")
        self.emp_b = make_user("smoketest_empb")
        self.team_a = make_team(
            "smoketest_atea", manager=self.mgr_a, members=[self.emp_a]
        )
        self.team_b = make_team(
            "smoketest_bteam", manager=self.mgr_b, members=[self.emp_b]
        )

        self.leader_client = self._client(self.leader)
        self.mgr_a_client = self._client(self.mgr_a)
        self.mgr_b_client = self._client(self.mgr_b)
        self.emp_a_client = self._client(self.emp_a)
        self.emp_b_client = self._client(self.emp_b)

    def _client(self, user):
        client = type(self.client)()
        client.force_login(user)
        return client


class ApprovalScopeTests(SkillSetupMixin, TestCase):
    def test_employee_gets_403_on_approvals_page(self):
        response = self.emp_a_client.get(reverse("approvals"))
        self.assertEqual(response.status_code, 403)

    def test_pending_submission_visible_only_to_own_manager_and_leadership(self):
        self.emp_a_client.post(
            reverse("self_assess"),
            {"skill": self.skill.pk, "level": 3, "evidence": "did stuff"},
        )
        prof = SkillProficiency.objects.get(user=self.emp_a, skill=self.skill)

        own = self.mgr_a_client.get(reverse("approvals"))
        self.assertContains(own, self.skill.name)
        self.assertContains(own, self.emp_a.username)

        other = self.mgr_b_client.get(reverse("approvals"))
        self.assertNotContains(other, self.emp_a.username)

        org = self.leader_client.get(reverse("approvals"))
        self.assertContains(org, self.emp_a.username)

    def test_manager_cannot_approve_other_teams_pending(self):
        self.emp_a_client.post(
            reverse("self_assess"),
            {"skill": self.skill.pk, "level": 3, "evidence": ""},
        )
        prof = SkillProficiency.objects.get(user=self.emp_a, skill=self.skill)
        response = self.mgr_b_client.post(
            reverse("approve_proficiency", args=[prof.pk])
        )
        self.assertEqual(response.status_code, 403)
        prof.refresh_from_db()
        self.assertEqual(prof.status, SkillProficiency.Status.PENDING)

    def test_leadership_can_approve_any_user(self):
        self.emp_a_client.post(
            reverse("self_assess"),
            {"skill": self.skill.pk, "level": 3, "evidence": ""},
        )
        prof = SkillProficiency.objects.get(user=self.emp_a, skill=self.skill)
        response = self.leader_client.post(
            reverse("approve_proficiency", args=[prof.pk])
        )
        self.assertRedirects(response, reverse("approvals"))
        prof.refresh_from_db()
        self.assertEqual(prof.status, SkillProficiency.Status.APPROVED)
        self.assertEqual(prof.approved_by, self.leader)

    def test_manager_approves_own_team(self):
        self.emp_a_client.post(
            reverse("self_assess"),
            {"skill": self.skill.pk, "level": 2, "evidence": "cm"},
        )
        prof = SkillProficiency.objects.get(user=self.emp_a, skill=self.skill)
        self.mgr_a_client.post(reverse("approve_proficiency", args=[prof.pk]))
        prof.refresh_from_db()
        self.assertEqual(prof.status, SkillProficiency.Status.APPROVED)

    def test_reject_sets_rejected(self):
        self.emp_a_client.post(
            reverse("self_assess"),
            {"skill": self.skill.pk, "level": 5, "evidence": ""},
        )
        prof = SkillProficiency.objects.get(user=self.emp_a, skill=self.skill)
        self.mgr_a_client.post(reverse("reject_proficiency", args=[prof.pk]))
        prof.refresh_from_db()
        self.assertEqual(prof.status, SkillProficiency.Status.REJECTED)


class ManagerRecordTests(SkillSetupMixin, TestCase):
    def test_manager_records_skill_for_member_approved(self):
        self.mgr_a_client.post(
            reverse("record_skill"),
            {"user": self.emp_a.pk, "skill": self.skill.pk, "level": 4, "evidence": ""},
        )
        prof = SkillProficiency.objects.get(user=self.emp_a, skill=self.skill)
        self.assertEqual(prof.status, SkillProficiency.Status.APPROVED)
        self.assertEqual(prof.approved_by, self.mgr_a)

    def test_manager_cannot_record_for_other_teams_member(self):
        response = self.mgr_b_client.post(
            reverse("record_skill"),
            {"user": self.emp_a.pk, "skill": self.skill.pk, "level": 4, "evidence": ""},
        )
        self.assertEqual(response.status_code, 403)
        self.assertFalse(
            SkillProficiency.objects.filter(user=self.emp_a).exists()
        )

    def test_employee_gets_403_on_record_skill(self):
        response = self.emp_a_client.post(
            reverse("record_skill"),
            {"user": self.emp_a.pk, "skill": self.skill.pk, "level": 4},
        )
        self.assertEqual(response.status_code, 403)

    def test_manager_records_certificate_for_member_approved(self):
        self.mgr_a_client.post(
            reverse("record_certificate"),
            {
                "user": self.emp_a.pk,
                "certificate": self.cert.pk,
                "skill": self.skill.pk,
                "level": 4,
                "obtained_on": "2026-01-01",
                "expires_on": "",
                "credential_url": "",
            },
        )
        award = CertificateAward.objects.get(user=self.emp_a)
        self.assertEqual(award.status, CertificateAward.Status.APPROVED)
        self.assertEqual(award.approved_by, self.mgr_a)
        self.assertEqual(award.skill, self.skill)

    def test_manager_cannot_record_certificate_for_other_teams_member(self):
        response = self.mgr_b_client.post(
            reverse("record_certificate"),
            {
                "user": self.emp_a.pk,
                "certificate": self.cert.pk,
                "skill": self.skill.pk,
                "level": 4,
                "obtained_on": "2026-01-01",
            },
        )
        self.assertEqual(response.status_code, 403)
        self.assertFalse(CertificateAward.objects.filter(user=self.emp_a).exists())


class SelfReportTests(SkillSetupMixin, TestCase):
    def test_employee_self_assess_creates_pending(self):
        self.emp_a_client.post(
            reverse("self_assess"),
            {"skill": self.skill.pk, "level": 3, "evidence": "built things"},
        )
        prof = SkillProficiency.objects.get(user=self.emp_a, skill=self.skill)
        self.assertEqual(prof.status, SkillProficiency.Status.PENDING)
        self.assertEqual(prof.reported_by, self.emp_a)

    def test_employee_can_resubmit_own_report(self):
        self.emp_a_client.post(
            reverse("self_assess"),
            {"skill": self.skill.pk, "level": 2, "evidence": "v1"},
        )
        self.emp_a_client.post(
            reverse("self_assess"),
            {"skill": self.skill.pk, "level": 4, "evidence": "v2"},
        )
        prof = SkillProficiency.objects.get(user=self.emp_a, skill=self.skill)
        self.assertEqual(prof.level, 4)
        self.assertEqual(prof.status, SkillProficiency.Status.PENDING)

    def test_employee_cannot_override_manager_recorded_rating(self):
        SkillProficiency.objects.create(
            user=self.emp_a,
            skill=self.skill,
            level=4,
            status=SkillProficiency.Status.APPROVED,
            reported_by=self.mgr_a,
            approved_by=self.mgr_a,
        )
        self.emp_a_client.post(
            reverse("self_assess"),
            {"skill": self.skill.pk, "level": 2, "evidence": ""},
        )
        prof = SkillProficiency.objects.get(user=self.emp_a, skill=self.skill)
        self.assertEqual(prof.level, 4)
        self.assertEqual(prof.status, SkillProficiency.Status.APPROVED)


class DevelopmentPlanTests(SkillSetupMixin, TestCase):
    def test_me_page_shows_development_plan_for_gap(self):
        from teams.models import TeamSkillRequirement

        TeamSkillRequirement.objects.create(
            team=self.team_a, skill=self.skill, required_level=4
        )
        SkillProficiency.objects.create(
            user=self.emp_a,
            skill=self.skill,
            level=1,
            status=SkillProficiency.Status.APPROVED,
        )
        response = self.emp_a_client.get(reverse("my_skills"))
        self.assertContains(response, "Your development plan")
        self.assertContains(response, self.skill.name)

    def test_me_page_omits_empty_development_plan(self):
        response = self.emp_a_client.get(reverse("my_skills"))
        self.assertNotContains(response, "Your development plan")


class CertificateSubmitTests(SkillSetupMixin, TestCase):
    def setUp(self):
        super().setUp()

    def test_employee_submit_certificate_is_pending(self):
        self.emp_a_client.post(
            reverse("submit_certificate"),
            {
                "certificate": self.cert.pk,
                "skill": self.skill.pk,
                "level": 4,
                "obtained_on": "2026-02-01",
                "expires_on": "",
                "credential_url": "",
            },
        )
        award = CertificateAward.objects.get(user=self.emp_a)
        self.assertEqual(award.status, CertificateAward.Status.PENDING)
        self.assertEqual(award.recorded_by, self.emp_a)
        self.assertEqual(award.skill, self.skill)

    def _submit_cert(self, client, user, level=4, expires_on=""):
        return client.post(
            reverse("submit_certificate"),
            {
                "certificate": self.cert.pk,
                "skill": self.skill.pk,
                "level": level,
                "obtained_on": "2026-02-01",
                "expires_on": expires_on,
                "credential_url": "",
            },
        )

    def test_approve_certificate_creates_proficiency(self):
        self._submit_cert(self.emp_a_client, self.emp_a)
        award = CertificateAward.objects.get(user=self.emp_a)
        response = self.mgr_a_client.post(
            reverse("approve_certificate", args=[award.pk])
        )
        self.assertRedirects(response, reverse("approvals"))
        award.refresh_from_db()
        self.assertEqual(award.status, CertificateAward.Status.APPROVED)
        prof = SkillProficiency.objects.get(user=self.emp_a, skill=self.skill)
        self.assertEqual(prof.level, 4)
        self.assertEqual(prof.status, SkillProficiency.Status.APPROVED)
        self.assertEqual(prof.approved_by, self.mgr_a)
        self.assertEqual(prof.reported_by, self.emp_a)
        self.assertIn(self.cert.name, prof.evidence)

    def test_approve_certificate_supersedes_pending_self_report(self):
        self.emp_a_client.post(
            reverse("self_assess"),
            {"skill": self.skill.pk, "level": 2, "evidence": "old self-report"},
        )
        self._submit_cert(self.emp_a_client, self.emp_a)
        award = CertificateAward.objects.get(user=self.emp_a)
        self.mgr_a_client.post(reverse("approve_certificate", args=[award.pk]))
        prof = SkillProficiency.objects.get(user=self.emp_a, skill=self.skill)
        self.assertEqual(prof.level, 4)
        self.assertEqual(prof.status, SkillProficiency.Status.APPROVED)

    def test_reject_certificate_does_not_touch_proficiency(self):
        SkillProficiency.objects.create(
            user=self.emp_a, skill=self.skill, level=2,
            status=SkillProficiency.Status.PENDING, reported_by=self.emp_a,
        )
        self._submit_cert(self.emp_a_client, self.emp_a)
        award = CertificateAward.objects.get(user=self.emp_a)
        self.mgr_a_client.post(reverse("reject_certificate", args=[award.pk]))
        award.refresh_from_db()
        self.assertEqual(award.status, CertificateAward.Status.REJECTED)
        prof = SkillProficiency.objects.get(user=self.emp_a, skill=self.skill)
        self.assertEqual(prof.status, SkillProficiency.Status.PENDING)
        self.assertEqual(prof.level, 2)

    def test_manager_cannot_approve_other_teams_certificate(self):
        self._submit_cert(self.emp_a_client, self.emp_a)
        award = CertificateAward.objects.get(user=self.emp_a)
        response = self.mgr_b_client.post(
            reverse("approve_certificate", args=[award.pk])
        )
        self.assertEqual(response.status_code, 403)
        award.refresh_from_db()
        self.assertEqual(award.status, CertificateAward.Status.PENDING)
        self.assertFalse(
            SkillProficiency.objects.filter(user=self.emp_a, skill=self.skill).exists()
        )

    def test_certificate_is_expired_flag(self):
        from datetime import date, timedelta

        from django.utils import timezone

        start = timezone.localdate() - timedelta(days=400)
        self._submit_cert(self.emp_a_client, self.emp_a, expires_on=start.isoformat())
        award = CertificateAward.objects.get(user=self.emp_a)
        self.assertTrue(award.is_expired)