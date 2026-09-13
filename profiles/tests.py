from datetime import date

from django.test import TestCase
from django.urls import reverse

from core.test_utils import make_user
from skills.models import Skill, SkillCategory

from .models import (
    DevelopmentActivity,
    ExperienceEntry,
    PerformanceReview,
)


class ProfileEntryViewsTests(TestCase):
    def setUp(self):
        self.user = make_user("profile_user")
        self.other = make_user("profile_other")
        self.client = type(self.client)()
        self.client.force_login(self.user)
        self.category = SkillCategory.objects.create(name="Profile testing")
        self.python = Skill.objects.create(name="Python", category=self.category)

    def test_add_activity_creates_entry_owned_by_user(self):
        response = self.client.post(
            reverse("add_activity"),
            {
                "activity_type": DevelopmentActivity.Type.COURSE,
                "skill": self.python.pk,
                "status": DevelopmentActivity.Status.COMPLETED,
                "completed_at": "2026-08-01",
                "note": "Advanced course.",
            },
        )
        self.assertRedirects(response, reverse("my_skills"))
        activity = self.user.development_activities.get()
        self.assertEqual(activity.user, self.user)
        self.assertEqual(activity.skill, self.python)
        self.assertEqual(activity.status, DevelopmentActivity.Status.COMPLETED)
        self.assertEqual(activity.completed_at, date(2026, 8, 1))

    def test_add_experience_creates_entry(self):
        response = self.client.post(
            reverse("add_experience"),
            {
                "role": "Software Engineer",
                "organization": "Acme",
                "start_date": "2022-03-01",
                "end_date": "",
                "summary": "Backend work.",
            },
        )
        self.assertRedirects(response, reverse("my_skills"))
        entry = self.user.experience_entries.get()
        self.assertEqual(entry.role, "Software Engineer")
        self.assertIsNone(entry.end_date)

    def test_add_review_creates_entry(self):
        response = self.client.post(
            reverse("add_review"),
            {
                "period": "2026 H1",
                "rating": "4",
                "reviewed_at": "2026-06-30",
                "goals": "Grow.",
                "feedback": "Solid.",
                "achievements": "Delivered.",
            },
        )
        self.assertRedirects(response, reverse("my_skills"))
        review = self.user.performance_reviews.get()
        self.assertEqual(review.period, "2026 H1")
        self.assertEqual(review.rating, 4)

    def test_invalid_form_renders_error_page(self):
        response = self.client.post(reverse("add_review"), {"period": ""})
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Couldn't save your performance review")
        self.assertEqual(PerformanceReview.objects.count(), 0)

    def test_anonymous_is_redirected_to_login(self):
        anonymous = type(self.client)()
        response = anonymous.post(reverse("add_activity"))
        self.assertEqual(response.status_code, 302)
        self.assertTrue(response.url.startswith("/accounts/login/"))

    def test_me_page_shows_entries_and_sections(self):
        DevelopmentActivity.objects.create(
            user=self.user,
            activity_type=DevelopmentActivity.Type.COURSE,
            skill=self.python,
            status=DevelopmentActivity.Status.IN_PROGRESS,
            note="Halfway through.",
        )
        ExperienceEntry.objects.create(
            user=self.other,
            role="Other role",
            organization="Elsewhere",
        )
        response = self.client.get(reverse("my_skills"))
        self.assertContains(response, "Development activity")
        self.assertContains(response, "Experience")
        self.assertContains(response, "Performance reviews")
        self.assertContains(response, "Halfway through.")
        # only own entries are shown
        self.assertNotContains(response, "Other role")