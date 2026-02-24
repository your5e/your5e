from django import forms


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
