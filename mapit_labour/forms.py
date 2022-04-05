import os
from tempfile import NamedTemporaryFile

from django import forms
from django.conf import settings

from django_q.tasks import async_task

from mapit_labour.importers import BranchCSVImporter


class ImportCSVForm(forms.Form):
    file = forms.FileField(required=True, allow_empty_file=False)
    commit = forms.BooleanField(initial=False, required=False)
    purge = forms.BooleanField(initial=True, required=False)

    def add_import_task(self):
        data = self.cleaned_data
        task_id = async_task(
            BranchCSVImporter.import_from_csv,
            path=self.copy_csv(data["file"]),
            commit=data["commit"],
            purge=data["purge"],
            generation=None,
        )
        return task_id

    def copy_csv(self, src):
        os.makedirs(settings.CSV_UPLOAD_DIR, exist_ok=True)

        dst = NamedTemporaryFile(
            dir=settings.CSV_UPLOAD_DIR, suffix=".csv", delete=False
        )
        for chunk in src.chunks():
            dst.write(chunk)
        dst.close()
        return dst.name
