from io import StringIO
from pathlib import Path

from django.conf import settings
from django.contrib.gis.geos import Point
from django.core.management import call_command
from django.test import TestCase
from mapit_labour.models import UPRN


class AddressBaseImportTest(TestCase):
    """Test the mapit_labour_import_addressbase_core management command"""

    def test_load_addressbase_csv(self):
        self.assertEqual(UPRN.objects.count(), 0)

        fixtures_dir = Path(settings.BASE_DIR) / "mapit_labour" / "tests" / "fixtures"
        stdout, stderr = StringIO(), StringIO()
        call_command(
            "mapit_labour_import_addressbase_core",
            fixtures_dir / "addressbase-core-tiny.csv",
            purge=True,
            stderr=stderr,
            stdout=stdout,
        )

        self.assertEqual(stderr.getvalue(), "")
        self.assertEqual(
            stdout.getvalue(),
            "Imported 2 (2 new, 0 updated)\n\nImported 2 (2 new, 0 updated)\n\n",
        )
        self.assertEqual(UPRN.objects.count(), 2)

        uprn = UPRN.objects.get(uprn=77281020)
        self.assertEqual(uprn.postcode, "TE15TT")
        self.assertEqual(uprn.single_line_address, "13 TEST STREET, TESTVILLE, TE1 5TT")
        self.assertEqual(uprn.location, Point(297350, 92996, srid=27700))
        self.assertDictEqual(
            uprn.addressbase,
            {
                "building_name": "",
                "building_number": "13",
                "change_code": "I",
                "classification_code": "RD",
                "delivery_point_suffix": "2X",
                "easting": "297350",
                "gss_code": "E07000041",
                "island": "",
                "last_update_date": "2020-01-06",
                "latitude": "50.7283373",
                "locality": "",
                "longitude": "-3.5600416",
                "northing": "92996",
                "organisation": "",
                "parent_uprn": "",
                "po_box": "",
                "post_town": "",
                "postcode": "TE1 5TT",
                "rpc": "1",
                "single_line_address": "13 TEST STREET, TESTVILLE, TE1 5TT",
                "street_name": "TEST STREET",
                "sub_building": "",
                "toid": "osgb1000012345678",
                "town_name": "TESTVILLE",
                "udprn": "1309123",
                "uprn": "77281020",
                "usrn": "12309821",
            },
        )
