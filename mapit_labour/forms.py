import os
from tempfile import NamedTemporaryFile

from django import forms
from django.conf import settings

from django_q.tasks import async_task
from crispy_forms_gds.helper import FormHelper
from crispy_forms_gds.layout import Submit


from mapit.models import Generation

from mapit_labour.importers import BranchCSVImporter
from .models import CSVImportTaskProgress


def get_generation_choices():
    choices = []
    if current := Generation.objects.current():
        choices.append((current.id, f"{current.id}: {current.description}"))

    if new := Generation.objects.new():
        choices.append((new.id, f"{new.id}: {new.description}"))
    else:
        choices.append(("new", "-- create new generation --"))

    return choices


class ImportCSVForm(forms.Form):
    file = forms.FileField(required=True, allow_empty_file=False)
    commit = forms.BooleanField(
        initial=False,
        required=False,
        help_text="Leave unticked to do a dry-run and not change the database.",
    )
    purge = forms.BooleanField(
        initial=False, required=False, label="Delete existing branches/regions"
    )
    generation = forms.ChoiceField(
        choices=get_generation_choices,
        required=True,
        label="Generation",
    )
    generation_description = forms.CharField(
        required=False,
        label="New generation description",
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.add_input(Submit("submit", "Submit"))

    def add_import_task(self):
        progress = CSVImportTaskProgress.objects.create(progress="Waiting to start...")
        data = self.cleaned_data
        task_id = async_task(
            BranchCSVImporter.import_from_csv,
            path=self.copy_csv(data["file"]),
            commit=data["commit"],
            purge=data["purge"],
            generation=data["generation"],
            generation_description=data["generation_description"],
            progress_id=progress.id,
        )
        progress.task_id = task_id
        progress.save()
        return task_id

    def clean(self):
        cleaned_data = super().clean()
        if cleaned_data["generation"] == "new" and not cleaned_data.get(
            "generation_description"
        ):
            self.add_error("generation_description", "Please provide a description")

    def copy_csv(self, src):
        os.makedirs(settings.CSV_UPLOAD_DIR, exist_ok=True)

        dst = NamedTemporaryFile(
            dir=settings.CSV_UPLOAD_DIR, suffix=".csv", delete=False
        )
        for chunk in src.chunks():
            dst.write(chunk)
        dst.close()
        return dst.name
