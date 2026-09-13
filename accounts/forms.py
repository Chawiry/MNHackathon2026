from django import forms
from django.contrib.auth.forms import UserCreationForm

from .models import User


class SetLeaveDateForm(forms.ModelForm):
    class Meta:
        model = User
        fields = ("expected_leave_date",)
        widgets = {"expected_leave_date": forms.DateInput(attrs={"type": "date"})}


class CreateUserForm(UserCreationForm):
    """Leadership creates fully-provisioned accounts (any tier)."""

    class Meta(UserCreationForm.Meta):
        model = User
        fields = ("username", "first_name", "last_name", "email", "job_title", "tier")

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["first_name"].required = True

    def save(self, commit=True):
        user = super().save(commit=False)
        user.is_active = True
        if commit:
            user.save()
        return user