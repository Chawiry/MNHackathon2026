from django import forms

from .models import DevelopmentActivity, ExperienceEntry, PerformanceReview


class DevelopmentActivityForm(forms.ModelForm):
    class Meta:
        model = DevelopmentActivity
        fields = ("activity_type", "skill", "status", "completed_at", "note")
        widgets = {
            "completed_at": forms.DateInput(attrs={"type": "date"}),
        }


class ExperienceEntryForm(forms.ModelForm):
    class Meta:
        model = ExperienceEntry
        fields = ("role", "organization", "start_date", "end_date", "summary")
        widgets = {
            "start_date": forms.DateInput(attrs={"type": "date"}),
            "end_date": forms.DateInput(attrs={"type": "date"}),
        }


class PerformanceReviewForm(forms.ModelForm):
    class Meta:
        model = PerformanceReview
        fields = ("period", "rating", "reviewed_at", "goals", "feedback", "achievements")
        widgets = {
            "reviewed_at": forms.DateInput(attrs={"type": "date"}),
        }