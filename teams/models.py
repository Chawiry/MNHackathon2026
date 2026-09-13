from django.conf import settings
from django.db import models

from skills.models import SkillProficiency


class Department(models.Model):
    """A business unit. Criticality, readiness, and aggregations are scoped here."""

    name = models.CharField(max_length=100, unique=True)
    description = models.TextField(blank=True)

    class Meta:
        ordering = ["name"]

    def __str__(self):
        return self.name


class Team(models.Model):
    name = models.CharField(max_length=100)
    description = models.TextField(blank=True)
    project = models.ForeignKey(
        "projects.Project",
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="teams",
        help_text="The project this team works on. Teams are spawned by projects.",
    )
    department = models.ForeignKey(
        Department,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="teams",
        help_text="Business unit this team reports into.",
    )

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["project", "name"],
                name="unique_project_team_name",
            )
        ]
        ordering = ["name"]

    def __str__(self):
        return self.name


class TeamMembership(models.Model):
    class Role(models.TextChoices):
        MANAGER = "manager", "Manager"
        MEMBER = "member", "Member"

    team = models.ForeignKey(Team, on_delete=models.CASCADE, related_name="memberships")
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="team_memberships",
    )
    role = models.CharField(max_length=20, choices=Role.choices, default=Role.MEMBER)
    joined_at = models.DateField(auto_now_add=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["team", "user"],
                name="unique_team_membership",
            )
        ]
        ordering = ["team__name", "user__username"]

    def __str__(self):
        return f"{self.user} — {self.role} @ {self.team}"


class TeamSkillRequirement(models.Model):
    class Importance(models.TextChoices):
        CRITICAL = "critical", "Critical"
        IMPORTANT = "important", "Important"
        OPTIONAL = "optional", "Optional"

    class Purpose(models.TextChoices):
        CURRENT = "current", "Current role"
        PROMOTION = "promotion", "Next position"

    team = models.ForeignKey(
        Team,
        on_delete=models.CASCADE,
        related_name="skill_requirements",
    )
    skill = models.ForeignKey(
        "skills.Skill",
        on_delete=models.PROTECT,
        related_name="team_requirements",
    )
    required_level = models.PositiveSmallIntegerField(
        choices=SkillProficiency.Level.choices,
        default=SkillProficiency.Level.INDEPENDENT,
    )
    importance = models.CharField(
        max_length=20,
        choices=Importance.choices,
        default=Importance.IMPORTANT,
    )
    purpose = models.CharField(
        max_length=20,
        choices=Purpose.choices,
        default=Purpose.CURRENT,
        help_text="'Current role' gaps block today's work; 'Next position' gaps "
        "define promotion-readiness.",
    )
    people_needed = models.PositiveSmallIntegerField(
        null=True,
        blank=True,
        help_text="How many people need this skill at the required level.",
    )

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["team", "skill"],
                name="unique_team_skill",
            )
        ]
        ordering = ["-importance", "skill__name"]

    def __str__(self):
        return f"{self.team} needs {self.skill}"