from io import StringIO
from pathlib import Path

from django.conf import settings
from django.contrib.auth.models import User
from django.core.management import call_command


class LoadTestData:
    _api_key = None

    @classmethod
    def setUpTestData(cls):
        user = User.objects.create_user("testuser", "", "password")
        cls._api_key = user.api_key.first().key

        fixtures_dir = Path(settings.BASE_DIR) / "mapit_labour" / "tests" / "fixtures"
        call_command(
            "mapit_labour_import_addressbase_core",
            fixtures_dir / "addressbase-core-tiny.csv",
            purge=True,
            stderr=StringIO(),
            stdout=StringIO(),
        )
