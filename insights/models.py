from django.conf import settings
from django.db import models


class StrategicInitiative(models.Model):
    """One rung of the leadership cascade.

    The cascade flows down from the CEO/board to teams. AI drafts each level's
    plan based on the level above, but only the human-`approved_content` flows
    to the next level — never `ai_draft_content`.
    """

    class Level(models.TextChoices):
        BOARD = "board", "Board / CEO"
        CSUITE = "csuite", "C-Suite"
        DEPARTMENT = "department", "Department"
        TEAM = "team", "Team"

    class Status(models.TextChoices):
        DRAFT = "draft", "Draft"
        REVIEW = "review", "In review"
        APPROVED = "approved", "Approved"

    title = models.CharField(max_length=200)
    level = models.CharField(
        max_length=20, choices=Level.choices, default=Level.DEPARTMENT
    )
    parent = models.ForeignKey(
        "self",
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="children",
        help_text="The approved plan this initiative cascades from.",
    )
    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="owned_initiatives",
    )
    ai_draft_content = models.TextField(
        blank=True,
        help_text="AI-drafted plan. NOT used by the level below.",
    )
    approved_content = models.TextField(
        blank=True,
        help_text="Human-approved plan — the only content the next level inherits.",
    )
    status = models.CharField(
        max_length=20, choices=Status.choices, default=Status.DRAFT
    )
    approved_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="approved_initiatives",
    )
    approved_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-level", "title"]

    def __str__(self):
        return f"[{self.get_level_display()}] {self.title}"

    def inherited_content(self):
        """The approved source of truth this initiative was drafted from."""
        if self.parent and self.parent.approved_content:
            return self.parent.approved_content
        return ""


class TeamFeedback(models.Model):
    """Upward flag from a team lead about feasibility or a gap.

    Flags roll up into aggregated readiness risks for leadership.
    """

    class IssueType(models.TextChoices):
        FEASIBILITY = "feasibility", "Feasibility gap"
        WORKFORCE = "workforce_shortfall", "Workforce shortfall"
        SKILL = "skill_shortfall", "Skill shortfall"
        READINESS = "readiness", "Readiness problem"
        OTHER = "other", "Other"

    raised_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="raised_feedback",
    )
    initiative = models.ForeignKey(
        StrategicInitiative,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="feedback",
    )
    issue_type = models.CharField(
        max_length=30, choices=IssueType.choices, default=IssueType.READINESS
    )
    description = models.TextField()
    resolved = models.BooleanField(default=False)
    resolution = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    resolved_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.get_issue_type_display()} · {self.description[:60]}"


class ReadinessSnapshot(models.Model):
    """Timestamped organization/department readiness score for trend tracking."""

    scope = models.CharField(
        max_length=30,
        default="org",
        help_text="'org' or the department name this snapshot covers.",
    )
    score = models.PositiveSmallIntegerField(
        default=0, help_text="0–100 readiness headline metric."
    )
    critical_skills_count = models.PositiveSmallIntegerField(default=0)
    detail_json = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [models.Index(fields=["scope", "-created_at"])]

    def __str__(self):
        return f"{self.scope} readiness {self.score} @ {self.created_at:%Y-%m-%d}"