from django.test import TestCase
from django.urls import reverse

from core.test_utils import make_user

from .models import Tier, User


class ManageUsersPermissionTests(TestCase):
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

    def test_user_list_leadership_only(self):
        self.assertEqual(self.leader_client.get(reverse("user_list")).status_code, 200)
        self.assertEqual(self.manager_client.get(reverse("user_list")).status_code, 403)
        self.assertEqual(self.employee_client.get(reverse("user_list")).status_code, 403)

    def test_create_user_leadership_only(self):
        self.assertEqual(self.manager_client.get(reverse("create_user")).status_code, 403)
        self.assertEqual(self.employee_client.get(reverse("create_user")).status_code, 403)

    def test_leadership_creates_user_with_tier(self):
        response = self.leader_client.post(
            reverse("create_user"),
            {
                "username": "smoketest_newhire",
                "first_name": "New",
                "last_name": "Hire",
                "email": "",
                "job_title": "Engineer",
                "tier": Tier.TEAM_MANAGER,
                "password1": "testpass123",
                "password2": "testpass123",
            },
        )
        self.assertRedirects(response, reverse("user_list"))
        user = User.objects.get(username="smoketest_newhire")
        self.assertEqual(user.tier, Tier.TEAM_MANAGER)
        self.assertTrue(user.is_active)

    def test_change_tier(self):
        response = self.leader_client.post(
            reverse("change_tier", args=[self.employee.pk]), {"tier": Tier.LEADERSHIP}
        )
        self.assertRedirects(response, reverse("user_list"))
        self.employee.refresh_from_db()
        self.assertEqual(self.employee.tier, Tier.LEADERSHIP)

    def test_manager_cannot_change_tier(self):
        response = self.manager_client.post(
            reverse("change_tier", args=[self.employee.pk]), {"tier": Tier.LEADERSHIP}
        )
        self.assertEqual(response.status_code, 403)
        self.employee.refresh_from_db()
        self.assertEqual(self.employee.tier, Tier.EMPLOYEE)

    def test_leadership_toggles_active(self):
        self.leader_client.post(reverse("toggle_active", args=[self.employee.pk]))
        self.employee.refresh_from_db()
        self.assertFalse(self.employee.is_active)
        self.leader_client.post(reverse("toggle_active", args=[self.employee.pk]))
        self.employee.refresh_from_db()
        self.assertTrue(self.employee.is_active)

    def test_cannot_deactivate_self(self):
        self.leader_client.post(reverse("toggle_active", args=[self.leader.pk]))
        self.leader.refresh_from_db()
        self.assertTrue(self.leader.is_active)

    def test_anonymous_gets_403_on_user_list(self):
        self.assertEqual(self.client.get(reverse("user_list")).status_code, 403)


class LeaveDateTests(TestCase):
    def setUp(self):
        from datetime import date, timedelta

        self.today = date.today()
        self.leave = self.today + timedelta(days=120)
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

    def _post(self, client, user, leave=None):
        return client.post(
            reverse("set_leave_date", args=[user.pk]),
            {"expected_leave_date": leave or ""},
        )

    def test_leadership_sets_leave_date(self):
        response = self._post(self.leader_client, self.employee, self.leave.isoformat())
        self.assertRedirects(response, reverse("user_list"))
        self.employee.refresh_from_db()
        self.assertEqual(self.employee.expected_leave_date, self.leave)

    def test_leadership_clears_leave_date(self):
        self.employee.expected_leave_date = self.leave
        self.employee.save()
        self._post(self.leader_client, self.employee)
        self.employee.refresh_from_db()
        self.assertIsNone(self.employee.expected_leave_date)

    def test_manager_and_employee_blocked(self):
        for client, user in (
            (self.manager_client, self.employee),
            (self.employee_client, self.employee),
        ):
            response = self._post(client, user, self.leave.isoformat())
            self.assertEqual(response.status_code, 403)
        self.employee.refresh_from_db()
        self.assertIsNone(self.employee.expected_leave_date)