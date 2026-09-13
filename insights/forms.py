from django import forms

from insights.models import StrategicInitiative, TeamFeedback
from skills.models import SkillCriticalityAssessment

SCALE_CHOICES = [(str(i), str(i)) for i in range(1, 6)]


class CriticalityFactorsForm(forms.ModelForm):
    """Leadership edit form for the criticality *factor inputs*.

    The score itself is never edited directly — it is recomputed from these
    inputs plus live high-proficiency concentration.
    """

    business_impact = forms.ChoiceField(
        choices=SCALE_CHOICES,
        label="Business impact (1–5)",
    )
    strategic_relevance = forms.ChoiceField(
        choices=SCALE_CHOICES,
        label="Strategic relevance (1–5)",
    )
    time_to_replace_months = forms.IntegerField(
        min_value=0,
        max_value=120,
        label="Time to replace (months)",
    )

    class Meta:
        model = SkillCriticalityAssessment
        fields = ("business_impact", "strategic_relevance", "time_to_replace_months")


class InitiativeCreateForm(forms.ModelForm):
    """Leadership form to start a strategic initiative in the cascade.

    The parent is restricted to *approved* plans so children always inherit an
    approved source of truth, never a draft.
    """

    parent = forms.ModelChoiceField(
        queryset=StrategicInitiative.objects.filter(
            status=StrategicInitiative.Status.APPROVED
        ),
        required=False,
        label="Cascades from",
        help_text="Leave empty for a board/CEO initiative at the top of the cascade.",
    )

    class Meta:
        model = StrategicInitiative
        fields = ("title", "level", "parent")


class FeedbackForm(forms.ModelForm):
    """Team leads raise an upward flag about feasibility or a gap."""

    class Meta:
        model = TeamFeedback
        fields = ("issue_type", "initiative", "description")
        widgets = {"description": forms.Textarea(attrs={"rows": 3})}
        labels = {
            "issue_type": "Issue type",
            "initiative": "Related initiative (optional)",
            "description": "What you're flagging",
        }


class FeedbackResolutionForm(forms.ModelForm):
    """Leadership resolution note for a raised flag."""

    class Meta:
        model = TeamFeedback
        fields = ("resolution",)
        widgets = {"resolution": forms.Textarea(attrs={"rows": 3})}
        labels = {"resolution": "Resolution"}