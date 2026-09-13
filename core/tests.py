from django.test import TestCase
from django.urls import reverse

from accounts.models import Tier

from .test_utils import make_user


class HomeDashboardTests(TestCase):
    def test_employee_home_renders_dashboard(self):
        user = make_user("alice", Tier.EMPLOYEE)
        self.client.force_login(user)
        response = self.client.get(reverse("home"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Skills recorded")

    def test_manager_home_renders_dashboard(self):
        user = make_user("bob", Tier.TEAM_MANAGER)
        self.client.force_login(user)
        response = self.client.get(reverse("home"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Pending approvals")

    def test_leadership_home_renders_dashboard(self):
        user = make_user("carol", Tier.LEADERSHIP)
        self.client.force_login(user)
        response = self.client.get(reverse("home"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Active projects")

    def test_home_requires_login(self):
        response = self.client.get(reverse("home"))
        self.assertEqual(response.status_code, 302)
        self.assertIn(reverse("login"), response.url)


class SearchTests(TestCase):
    def setUp(self):
        self.user = make_user("dave", Tier.EMPLOYEE)

    def test_search_json_returns_result_shape(self):
        self.client.force_login(self.user)
        r = self.client.get(reverse("search"), {"q": "py", "format": "json"})
        self.assertEqual(r.status_code, 200)
        data = r.json()
        self.assertIn("results", data)
        self.assertSetEqual(
            set(data["results"].keys()), {"users", "skills", "teams", "projects"}
        )

    def test_search_page_renders(self):
        self.client.force_login(self.user)
        r = self.client.get(reverse("search"), {"q": "py"})
        self.assertEqual(r.status_code, 200)
        self.assertContains(r, "py")


class RegisterRemovedTests(TestCase):
    def test_register_url_is_gone(self):
        from django.urls import NoReverseMatch

        with self.assertRaises(NoReverseMatch):
            reverse("register")


class ErrorPageTests(TestCase):
    def test_404_uses_custom_template(self):
        r = self.client.get("/definitely-not-a-page/")
        self.assertEqual(r.status_code, 404)
        self.assertContains(r, "Page not found", status_code=404)