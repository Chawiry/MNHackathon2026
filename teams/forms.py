from django import forms

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
        fields = ("skill", "required_level", "importance", "people_needed")

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["required_level"].choices = SkillProficiency.Level.choices