from django.conf import settings
from django.db import models


class SkillCategory(models.Model):
    name = models.CharField(max_length=100, unique=True)
    description = models.TextField(blank=True)

    class Meta:
        verbose_name_plural = "skill categories"
        ordering = ["name"]

    def __str__(self):
        return self.name


class Skill(models.Model):
    name = models.CharField(max_length=100)
    category = models.ForeignKey(
        SkillCategory,
        on_delete=models.PROTECT,
        related_name="skills",
    )
    description = models.TextField(blank=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["name", "category"],
                name="unique_skill_name_category",
            )
        ]
        ordering = ["category__name", "name"]

    def __str__(self):
        return self.name


class SkillProficiency(models.Model):
    class Level(models.IntegerChoices):
        NOVICE = 1, "Novice"
        BASIC = 2, "Basic"
        INDEPENDENT = 3, "Independent"
        ADVANCED = 4, "Advanced"
        EXPERT = 5, "Expert"

    class Status(models.TextChoices):
        PENDING = "pending", "Pending"
        APPROVED = "approved", "Approved"
        REJECTED = "rejected", "Rejected"

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="proficiencies",
    )
    skill = models.ForeignKey(
        Skill,
        on_delete=models.CASCADE,
        related_name="proficiencies",
    )
    level = models.PositiveSmallIntegerField(choices=Level.choices)
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.PENDING,
    )
    evidence = models.TextField(
        blank=True,
        help_text="Examples, training, or projects backing this rating.",
    )
    reported_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="reported_proficiencies",
    )
    approved_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="approved_proficiencies",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["user", "skill"],
                name="unique_user_skill",
            )
        ]
        ordering = ["-updated_at"]

    def __str__(self):
        return f"{self.user} – {self.skill} ({self.get_level_display()})"


class Certificate(models.Model):
    name = models.CharField(max_length=200)
    issuer = models.CharField(max_length=200, blank=True)
    description = models.TextField(blank=True)

    class Meta:
        ordering = ["name"]

    def __str__(self):
        return f"{self.name} ({self.issuer})" if self.issuer else self.name


class CertificateAward(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="certificate_awards",
    )
    certificate = models.ForeignKey(
        Certificate,
        on_delete=models.PROTECT,
        related_name="awards",
    )
    obtained_on = models.DateField()
    expires_on = models.DateField(null=True, blank=True)
    credential_url = models.URLField(blank=True)
    recorded_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="recorded_certificate_awards",
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-obtained_on"]

    def __str__(self):
        return f"{self.user} – {self.certificate}"