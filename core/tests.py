from django.test import TestCase
from django.urls import reverse

from accounts.models import Tier

from .test_utils import make_user


class HomeRedirectTests(TestCase):
    def test_employee_home_redirects_to_my_skills(self):
        user = make_user("alice", Tier.EMPLOYEE)
        self.client.force_login(user)
        response = self.client.get(reverse("home"))
        self.assertRedirects(response, reverse("my_skills"))

    def test_manager_home_redirects_to_teams(self):
        user = make_user("bob", Tier.TEAM_MANAGER)
        self.client.force_login(user)
        response = self.client.get(reverse("home"))
        self.assertRedirects(response, reverse("team_list"))

    def test_leadership_home_redirects_to_projects(self):
        user = make_user("carol", Tier.LEADERSHIP)
        self.client.force_login(user)
        response = self.client.get(reverse("home"))
        self.assertRedirects(response, reverse("project_list"))

    def test_home_requires_login(self):
        response = self.client.get(reverse("home"))
        self.assertEqual(response.status_code, 302)
        self.assertIn(reverse("login"), response.url)


class RegisterRemovedTests(TestCase):
    def test_register_url_is_gone(self):
        from django.urls import NoReverseMatch

        with self.assertRaises(NoReverseMatch):
            reverse("register")