from django import forms
from django.contrib.auth import get_user_model

from teams.models import Team

from .models import Project

User = get_user_model()


def _user_label(user):
    title = user.get_full_name() or user.job_title or "no title"
    return f"{user.username} ({title})"


class ProjectCreateForm(forms.ModelForm):
    class Meta:
        model = Project
        fields = ("name", "description", "status", "start_date", "end_date")
        widgets = {
            "start_date": forms.DateInput(attrs={"type": "date"}),
            "end_date": forms.DateInput(attrs={"type": "date"}),
        }

    team_name = forms.CharField(
        max_length=100,
        required=False,
        help_text="Defaults to the project name.",
        label="Initial team name",
    )
    manager = forms.ModelChoiceField(
        queryset=User.objects.filter(is_active=True).order_by("username"),
        label="Team manager",
        help_text="Leads the project's initial team.",
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["manager"].label_from_instance = _user_label


class AddTeamForm(forms.ModelForm):
    class Meta:
        model = Team
        fields = ("name",)

    manager = forms.ModelChoiceField(
        queryset=User.objects.filter(is_active=True).order_by("username"),
        label="Team manager",
        help_text="Leads this team.",
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["manager"].label_from_instance = _user_label