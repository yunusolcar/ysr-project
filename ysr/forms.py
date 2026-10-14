from django import forms

from .models import Respondent


class StartForm(forms.ModelForm):
    class Meta:
        model = Respondent
        fields = ["code", "gender", "age", "grade"]
        widgets = {"gender": forms.RadioSelect}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["gender"].choices = Respondent.Gender.choices
