from django import forms

from notebooks.models import Notebook, NotebookPermission


class NotebookCreateForm(forms.Form):
    name = forms.CharField(max_length=255)
    visibility = forms.ChoiceField(
        choices=Notebook.Visibility.choices,
        initial=Notebook.Visibility.PRIVATE,
    )
    description = forms.CharField(
        required=False,
        widget=forms.Textarea(attrs={"rows": 10, "cols": 80}),
    )


class CollaboratorForm(forms.Form):
    collaborator_username = forms.CharField(
        max_length=150,
        required=False,
    )
    collaborator_role = forms.ChoiceField(
        choices=NotebookPermission.Role.choices,
        required=False,
    )


class PageForm(forms.Form):
    filename = forms.CharField(
        max_length=255,
        required=False,
        widget=forms.TextInput(attrs={"size": 80}),
    )
    content = forms.CharField(
        required=False,
        widget=forms.Textarea(attrs={"rows": 20, "cols": 80}),
    )
    file = forms.FileField(required=False)


class RestoreForm(forms.Form):
    filename = forms.CharField(
        max_length=255,
        required=False,
        widget=forms.TextInput(attrs={
            "placeholder": "New location (optional)",
        }),
    )
