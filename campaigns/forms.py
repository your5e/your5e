from django import forms

from campaigns.models import Campaign


class CampaignForm(forms.ModelForm):
    class Meta:
        model = Campaign
        fields = ["name"]


class CampaignRenameForm(forms.ModelForm):
    class Meta:
        model = Campaign
        fields = ["name"]


class CampaignDescriptionForm(forms.ModelForm):
    class Meta:
        model = Campaign
        fields = ["description"]
