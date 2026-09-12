from django import forms

from .models import Certificate, CertificateAward, Skill, SkillProficiency


class SelfReportForm(forms.ModelForm):
    class Meta:
        model = SkillProficiency
        fields = ("skill", "level", "evidence")
        widgets = {
            "evidence": forms.Textarea(attrs={"rows": 2}),
        }


class RecordSkillForm(forms.ModelForm):
    class Meta:
        model = SkillProficiency
        fields = ("user", "skill", "level", "evidence")
        widgets = {
            "evidence": forms.Textarea(attrs={"rows": 2}),
        }


class CertificateSubmitForm(forms.ModelForm):
    class Meta:
        model = CertificateAward
        fields = ("certificate", "obtained_on", "expires_on", "credential_url")
        widgets = {
            "obtained_on": forms.DateInput(attrs={"type": "date"}),
            "expires_on": forms.DateInput(attrs={"type": "date"}),
        }


class RecordCertificateForm(CertificateSubmitForm):
    class Meta(CertificateSubmitForm.Meta):
        fields = ("user",) + CertificateSubmitForm.Meta.fields