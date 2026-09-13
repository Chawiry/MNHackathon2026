from django.contrib.auth.models import AbstractUser
from django.db import models


class Tier(models.TextChoices):
    EMPLOYEE = "employee", "Employee"
    TEAM_MANAGER = "team_manager", "Team manager"
    LEADERSHIP = "leadership", "Leadership"


class User(AbstractUser):
    tier = models.CharField(
        max_length=20,
        choices=Tier.choices,
        default=Tier.EMPLOYEE,
        help_text="Determines what the user can see and change.",
    )
    job_title = models.CharField(max_length=100, blank=True)
    hire_date = models.DateField(null=True, blank=True)
    expected_leave_date = models.DateField(
        null=True,
        blank=True,
        help_text="Date leadership expects this person to leave.",
    )

    def __str__(self):
        return self.get_full_name() or self.username