from django.conf import settings
from django.db import models
from django.utils import timezone


class SkillCategory(models.Model):
    class Domain(models.TextChoices):
        TECHNICAL = "technical", "Technical"
        BUSINESS = "business", "Business"
        LEADERSHIP = "leadership", "Leadership"

    name = models.CharField(max_length=100, unique=True)
    description = models.TextField(blank=True)
    domain = models.CharField(
        max_length=20,
        choices=Domain.choices,
        default=Domain.TECHNICAL,
        help_text="Top-level taxonomy domain this category belongs to.",
    )

    class Meta:
        verbose_name_plural = "skill categories"
        ordering = ["name"]

    def __str__(self):
        return self.name


class SkillRelationship(models.Model):
    """One half of the skills graph.

    The graph lets the platform reason about how one skill can help develop
    another (adjacent skills), which powers successor matching and
    gap-to-recommendation routing.
    """

    class Kind(models.TextChoices):
        RELATED = "related", "Related to"
        PREREQUISITE = "prerequisite", "Prerequisite for"
        TRANSFERS = "transfers", "Transfers to"

    from_skill = models.ForeignKey(
        "Skill", on_delete=models.CASCADE, related_name="outgoing_relationships"
    )
    to_skill = models.ForeignKey(
        "Skill", on_delete=models.CASCADE, related_name="incoming_relationships"
    )
    kind = models.CharField(
        max_length=20, choices=Kind.choices, default=Kind.RELATED
    )
    weight = models.PositiveSmallIntegerField(
        default=1,
        help_text="0–5 affinity; used when a related skill stands in for the target.",
    )

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["from_skill", "to_skill", "kind"],
                name="unique_skill_relationship",
            )
        ]
        ordering = ["from_skill__name", "to_skill__name", "kind"]

    def __str__(self):
        return f"{self.from_skill} → {self.to_skill} ({self.get_kind_display()})"


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
    last_used = models.DateField(
        null=True,
        blank=True,
        help_text="Most recent date this skill was evaluated or actively used.",
    )
    validation_source = models.CharField(
        max_length=30,
        blank=True,
        help_text="How this rating was validated (e.g. self assessment, manager "
        "evaluation, peer feedback, certification, project evidence).",
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
    class Status(models.TextChoices):
        PENDING = "pending", "Pending"
        APPROVED = "approved", "Approved"
        REJECTED = "rejected", "Rejected"

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
    skill = models.ForeignKey(
        Skill,
        on_delete=models.PROTECT,
        related_name="certificate_awards",
        help_text="The skill this certificate confirms.",
    )
    level = models.PositiveSmallIntegerField(
        choices=SkillProficiency.Level.choices,
        help_text="Proficiency level this certificate confirms.",
    )
    obtained_on = models.DateField()
    expires_on = models.DateField(null=True, blank=True)
    credential_url = models.URLField(blank=True)
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.PENDING,
    )
    recorded_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="recorded_certificate_awards",
    )
    approved_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="approved_certificate_awards",
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-obtained_on"]

    def __str__(self):
        return f"{self.user} – {self.certificate}"

    @property
    def is_expired(self):
        return bool(self.expires_on and self.expires_on < timezone.localdate())


class SkillCriticalityAssessment(models.Model):
    """How important a skill is to a business unit, on a 0–100 scale.

    Criticality is scoped per business unit, timestamped and versioned so the
    organization can watch how it changes over time. Criticality ≠ rarity: it
    blends business impact, concentration risk, time-to-replace, and strategic
    relevance.
    """

    department = models.ForeignKey(
        "teams.Department",
        on_delete=models.PROTECT,
        related_name="criticality_assessments",
    )
    skill = models.ForeignKey(
        "Skill", on_delete=models.PROTECT, related_name="criticality_assessments"
    )
    business_impact = models.PositiveSmallIntegerField(
        default=3,
        help_text="1–5: business impact if the skill disappears.",
    )
    strategic_relevance = models.PositiveSmallIntegerField(
        default=3,
        help_text="1–5: how aligned the skill is with the company strategy.",
    )
    time_to_replace_months = models.PositiveIntegerField(
        default=12,
        help_text="Semi-automated: how long to hire/replace externally.",
    )
    criticality_score = models.PositiveSmallIntegerField(
        default=0,
        help_text="0–100 computed score (see insights.services.criticality_formula).",
    )
    assessed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="criticality_assessments",
    )
    version = models.PositiveIntegerField(default=1)
    assessed_at = models.DateTimeField(auto_now_add=True)
    notes = models.TextField(blank=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["department", "skill", "version"],
                name="unique_department_skill_version",
            )
        ]
        ordering = ["-version", "skill__name"]
        verbose_name_plural = "criticality assessments"

    def __str__(self):
        return f"{self.skill} @ {self.department} (v{self.version}, {self.criticality_score})"


class SkillFutureDemand(models.Model):
    """A projection that a skill will grow or shrink in importance.

    Future predictions are inherently uncertain, so every projection has an
    explicit confidence level. Sources are curated external reports or
    AI-assisted synthesis that humans review.
    """

    class Direction(models.TextChoices):
        EMERGING = "emerging", "Emerging"
        GROWING = "growing", "Growing"
        STABLE = "stable", "Stable"
        DECLINING = "declining", "Declining"

    class Confidence(models.TextChoices):
        LOW = "low", "Low"
        MEDIUM = "medium", "Medium"
        HIGH = "high", "High"

    skill = models.ForeignKey(
        "Skill", on_delete=models.PROTECT, related_name="future_demands"
    )
    direction = models.CharField(
        max_length=20, choices=Direction.choices, default=Direction.EMERGING
    )
    future_importance = models.PositiveSmallIntegerField(
        default=3, help_text="1–5 importance within the 5–10 year horizon."
    )
    confidence_level = models.CharField(
        max_length=20,
        choices=Confidence.choices,
        default=Confidence.MEDIUM,
        help_text="How confident we are in this projection.",
    )
    horizon = models.CharField(
        max_length=50,
        default="12–24 months",
        help_text="Time horizon the projection applies to.",
    )
    source = models.CharField(
        max_length=100,
        blank=True,
        help_text="Curated report, market data, or AI-assisted draft.",
    )
    note = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-future_importance", "skill__name"]

    def __str__(self):
        return f"{self.skill} {self.get_direction_display()} ({self.get_confidence_level_display()})"