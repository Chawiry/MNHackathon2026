"""Lightweight employee profile records.

These sit alongside proficiencies and certificates on the employee profile
page: how people are developing (courses, mentoring, rotations), where they
have worked, and how recent performance reviews went. Kept intentionally
simple — no workflow, just provenance timestamps.
"""

from django.conf import settings
from django.db import models


class DevelopmentActivity(models.Model):
    class Type(models.TextChoices):
        COURSE = "course", "Course"
        MENTORING = "mentoring", "Mentoring"
        JOB_ROTATION = "job_rotation", "Job rotation"

    class Status(models.TextChoices):
        PLANNED = "planned", "Planned"
        IN_PROGRESS = "in_progress", "In progress"
        COMPLETED = "completed", "Completed"

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="development_activities",
    )
    activity_type = models.CharField(
        max_length=20, choices=Type.choices, default=Type.COURSE
    )
    skill = models.ForeignKey(
        "skills.Skill",
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="development_activities",
    )
    status = models.CharField(
        max_length=20, choices=Status.choices, default=Status.PLANNED
    )
    completed_at = models.DateField(
        null=True, blank=True, help_text="When the activity is (or will be) done."
    )
    note = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]
        verbose_name_plural = "development activities"

    def __str__(self):
        return f"{self.user} – {self.get_activity_type_display()}: {self.skill or '—'}"


class ExperienceEntry(models.Model):
    """A past or current position shown on the employee profile."""

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="experience_entries",
    )
    role = models.CharField(max_length=120)
    organization = models.CharField(max_length=120)
    start_date = models.DateField(null=True, blank=True)
    end_date = models.DateField(
        null=True, blank=True, help_text="Leave blank if it's the current role."
    )
    summary = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-start_date"]

    def __str__(self):
        return f"{self.user} – {self.role} @ {self.organization}"


class PerformanceReview(models.Model):
    class Rating(models.IntegerChoices):
        NEEDS_IMPROVEMENT = 1, "Needs improvement"
        DEVELOPING = 2, "Developing"
        MEETS_EXPECTATIONS = 3, "Meets expectations"
        EXCEEDS_EXPECTATIONS = 4, "Exceeds expectations"
        OUTSTANDING = 5, "Outstanding"

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="performance_reviews",
    )
    period = models.CharField(
        max_length=50, help_text="e.g. 2026 H1 or 2025 annual"
    )
    rating = models.PositiveSmallIntegerField(
        choices=Rating.choices,
        null=True,
        blank=True,
    )
    goals = models.TextField(blank=True)
    feedback = models.TextField(blank=True)
    achievements = models.TextField(blank=True)
    reviewed_at = models.DateField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-reviewed_at", "-created_at"]

    def __str__(self):
        return f"{self.user} – {self.period}"