from django import forms
from django.contrib.auth.forms import UserCreationForm

from .models import User


class SignupForm(UserCreationForm):
    """Registration form bound to the custom auth user model."""

    email = forms.EmailField(required=False)

    class Meta(UserCreationForm.Meta):
        model = User
        fields = ("username", "email")

    def save(self, commit=True):
        # New self-service accounts are always employees; tier is upgraded
        # by a manager/leadership via the admin.
        user = super().save(commit=False)
        user.email = self.cleaned_data.get("email", "")
        if commit:
            user.save()
        return user