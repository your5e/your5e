from django import forms

from users.models import ProfileLink, User


class ProfileForm(forms.ModelForm):
    class Meta:
        model = User
        fields = ["name", "short_name", "description"]


class ProfileLinkForm(forms.ModelForm):
    class Meta:
        model = ProfileLink
        fields = ["url", "label"]
