from django.conf import settings
from django.db import models


class Team(models.Model):
    name = models.CharField(max_length=100, unique=True)
    description = models.TextField(blank=True)

    class Meta:
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