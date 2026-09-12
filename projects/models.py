from django.db import models


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
