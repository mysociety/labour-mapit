from django import forms


class BranchUploadForm(forms.Form):
    file = forms.FileField(required=True, allow_empty_file=False)

    def create_branches(self):
        pass
