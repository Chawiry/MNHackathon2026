from django.db import models

from skills.models import SkillProficiency


class Project(models.Model):
    class Status(models.TextChoices):
        ACTIVE = "active", "Active"
        PLANNED = "planned", "Planned"
        COMPLETED = "completed", "Completed"

    name = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.ACTIVE,
    )
    start_date = models.DateField(null=True, blank=True)
    end_date = models.DateField(null=True, blank=True)

    class Meta:
        ordering = ["name"]

    def __str__(self):
        return self.name


class ProjectSkillRequirement(models.Model):
    class Importance(models.TextChoices):
        CRITICAL = "critical", "Critical"
        IMPORTANT = "important", "Important"
        OPTIONAL = "optional", "Optional"

    project = models.ForeignKey(
        Project,
        on_delete=models.CASCADE,
        related_name="skill_requirements",
    )
    skill = models.ForeignKey(
        "skills.Skill",
        on_delete=models.PROTECT,
        related_name="project_requirements",
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
    people_needed = models.PositiveSmallIntegerField(
        null=True,
        blank=True,
        help_text="How many people need this skill at the required level.",
    )

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["project", "skill"],
                name="unique_project_skill",
            )
        ]
        ordering = ["-importance", "skill__name"]

    def __str__(self):
        return f"{self.project} needs {self.skill}"