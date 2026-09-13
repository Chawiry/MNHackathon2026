from django import forms

from accounts.models import Tier, User
from skills.models import SkillProficiency

from teams.models import Team, TeamMembership, TeamSkillRequirement


class AddMemberForm(forms.ModelForm):
    class Meta:
        model = TeamMembership
        fields = ("team", "user", "role")

    def __init__(self, *args, manager=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["user"].label_from_instance = lambda u: f"{u.username} ({u.get_full_name() or u.job_title or 'no title'})"
        if manager is not None:
            self.fields["team"].queryset = Team.objects.filter(
                memberships__user=manager,
                memberships__role=TeamMembership.Role.MANAGER,
            )


class ChangeRoleForm(forms.ModelForm):
    class Meta:
        model = TeamMembership
        fields = ("role",)


class AddRequirementForm(forms.ModelForm):
    class Meta:
        model = TeamSkillRequirement
        fields = ("skill", "required_level", "importance", "purpose", "people_needed")

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["required_level"].choices = SkillProficiency.Level.choices
        self.fields["purpose"].required = False


class CreateMemberForm(forms.Form):
    """Provision a new employee account and add them to a managed team."""

    username = forms.CharField(max_length=150)
    first_name = forms.CharField(max_length=150, required=False)
    job_title = forms.CharField(max_length=100, required=False)
    password = forms.CharField(
        widget=forms.PasswordInput,
        help_text="Temporary password to share with the new hire.",
    )
    team = forms.ModelChoiceField(queryset=Team.objects.none(), label="Add to team")

    def __init__(self, *args, manager=None, **kwargs):
        super().__init__(*args, **kwargs)
        teams = Team.objects.all()
        if manager is not None and manager.tier != Tier.LEADERSHIP:
            teams = teams.filter(
                memberships__user=manager,
                memberships__role=TeamMembership.Role.MANAGER,
            )
        self.fields["team"].queryset = teams

    def save(self):
        user = User.objects.create_user(
            username=self.cleaned_data["username"],
            password=self.cleaned_data["password"],
            first_name=self.cleaned_data["first_name"],
            job_title=self.cleaned_data["job_title"],
            tier=Tier.EMPLOYEE,
        )
        TeamMembership.objects.create(
            team=self.cleaned_data["team"],
            user=user,
            role=TeamMembership.Role.MEMBER,
        )
        return user