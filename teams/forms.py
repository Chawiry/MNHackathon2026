from django import forms

from teams.models import Team, TeamMembership


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