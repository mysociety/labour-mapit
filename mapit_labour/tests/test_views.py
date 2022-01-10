from django.contrib.auth.models import User
from django.contrib.gis.geos import Polygon
from django.test import TestCase
from mapit.models import Area, Generation, Geometry, Type

from .utils import LoadTestData


class LoginRequiredTestCase(LoadTestData, TestCase):
    def test_redirect_to_login(self):
        self.client.logout()

        self.assertRedirects(
            self.client.get("/"), "/admin/login/?next=/", status_code=302
        )
        self.assertRedirects(
            self.client.get("/uprn/77281020.html"),
            "/admin/login/?next=/uprn/77281020.html",
            status_code=302,
        )

        # Check that the fact a UPRN doesn't exist isn't leaked in response
        self.assertRedirects(
            self.client.get("/uprn/123098123.html"),
            "/admin/login/?next=/uprn/123098123.html",
            status_code=302,
        )

    def test_logged_in_user(self):
        self.assertTrue(self.client.login(username="testuser", password="password"))

        self.assertContains(self.client.get("/"), "MapIt API Documentation")
        self.assertContains(
            self.client.get("/uprn/77281020.html"),
            "UPRN: 77281020",
        )

        self.assertEqual(self.client.get("/uprn/123098123.html").status_code, 404)

    def test_login_not_required(self):
        self.client.logout()
        self.assertContains(
            self.client.get("/health"), "Everything OK", status_code=200
        )

        self.assertTrue(self.client.login(username="testuser", password="password"))
        self.assertContains(
            self.client.get("/health"), "Everything OK", status_code=200
        )


class APIKeyTestCase(LoadTestData, TestCase):
    fixtures = ["uk", "test_areas"]

    def test_api_key_required(self):
        for url in (
            "/uprn/77281020.json",
            "/uprn/123098123.json",
            "/uprn/77281020",
            "/uprn/123098123",
            "/addressbase?single_line_address=testville",
            "/addressbase?street_name=zettabyte+road",
        ):
            self.assertEqual(self.client.get(url).status_code, 403)

    def test_logged_in_api_key_not_required(self):
        self.assertTrue(self.client.login(username="testuser", password="password"))
        for url in (
            f"/uprn/77281020.json",
            f"/uprn/77281020",
            f"/addressbase?single_line_address=testville",
            f"/addressbase?street_name=zettabyte+road",
        ):
            self.assertEqual(self.client.get(url).status_code, 200)

        for url in (
            f"/uprn/123098123.json",
            f"/uprn/123098123",
        ):
            self.assertEqual(self.client.get(url).status_code, 404)

    def test_api_key_accepted(self):
        for url in (
            f"/uprn/77281020.json?api_key={self._api_key}",
            f"/uprn/77281020?api_key={self._api_key}",
            f"/addressbase?single_line_address=testville&api_key={self._api_key}",
            f"/addressbase?street_name=zettabyte+road&api_key={self._api_key}",
        ):
            self.assertEqual(self.client.get(url).status_code, 200)

        for url in (
            f"/uprn/123098123.json?api_key={self._api_key}",
            f"/uprn/123098123?api_key={self._api_key}",
        ):
            self.assertEqual(self.client.get(url).status_code, 404)

    def test_inactive_user_api_key_rejected(self):
        User.objects.filter(username="testuser").update(is_active=False)
        for url in (
            f"/uprn/77281020.json?api_key={self._api_key}",
            f"/uprn/77281020?api_key={self._api_key}",
            f"/uprn/123098123.json?api_key={self._api_key}",
            f"/uprn/123098123?api_key={self._api_key}",
            f"/addressbase?single_line_address=testville&api_key={self._api_key}",
            f"/addressbase?street_name=zettabyte+road&api_key={self._api_key}",
        ):
            self.assertEqual(self.client.get(url).status_code, 403)

    def test_mapit_api_calls(self):
        User.objects.filter(username="testuser").update(is_active=True)
        for url in (
            f"/area/1.json?api_key={self._api_key}",
            f"/area/1?api_key={self._api_key}",
            f"/area/1/geometry?api_key={self._api_key}",
            f"/areas/WMC?api_key={self._api_key}",
            f"/generations?api_key={self._api_key}",
            f"/generations.json?api_key={self._api_key}",
        ):
            self.assertEqual(self.client.get(url).status_code, 200)

        for url in (
            f"/area/1.json",
            f"/area/1",
            f"/area/1/geometry",
            f"/areas/WMC",
            f"/generations",
            f"/generations.json",
        ):
            self.assertEqual(self.client.get(url).status_code, 403)


class UPRNLookupTestCase(LoadTestData, TestCase):
    fixtures = ["uk", "test_areas"]

    def setUp(self):
        self.assertTrue(self.client.login(username="testuser", password="password"))

    def test_uprn_json_output(self):
        self.assertJSONEqual(
            self.client.get("/uprn/77281020.json").content,
            {
                "areas": {
                    "1": {
                        "all_names": {},
                        "codes": {},
                        "country": "",
                        "country_name": "-",
                        "generation_high": 1,
                        "generation_low": 1,
                        "id": 1,
                        "name": "WMC Area A",
                        "parent_area": None,
                        "type": "WMC",
                        "type_name": "UK Parliament constituency",
                    }
                },
                "easting": 297350.0,
                "northing": 92996.0,
                "postcode": "TE15TT",
                "shortcuts": {"WMC": 1},
                "uprn": 77281020,
                "wgs84_lat": 50.72747506213238,
                "wgs84_lon": -3.455748209039153,
                "addressbase_core": {
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
                    "single_line_address": "13 TEST STREET, TESTVILLE, TE1 " "5TT",
                    "street_name": "TEST STREET",
                    "sub_building": "",
                    "toid": "osgb1000012345678",
                    "town_name": "TESTVILLE",
                    "udprn": "1309123",
                    "uprn": "77281020",
                    "usrn": "12309821",
                },
            },
        )

    def test_uprn_html_output(self):
        resp = self.client.get("/uprn/77281020.html")
        html = resp.content.decode()
        self.assertInHTML("<title>Results for “77281020” - MapIt</title>", html)
        self.assertInHTML("<h2>UPRN: 77281020</h2>", html)
        self.assertInHTML("<li>OSGB E/N: 297350.0, 92996.0</li>", html)
        self.assertInHTML(
            """<li>WGS84 lat/lon: <a href="https://tools.wmflabs.org/geohack/geohack.php?params=50.727475;-3.455748">50.727475, -3.455748</a></li>""",
            html,
        )

    def test_missing_uprn(self):
        for url in (
            f"/uprn/123098123.html",
            f"/uprn/123098123.json",
            f"/uprn/123098123",
        ):
            self.assertEqual(self.client.get(url).status_code, 404)


class AddressBaseTestCase(LoadTestData, TestCase):
    maxDiff = None

    _uprn1 = {
        "rpc": "1",
        "toid": "osgb1000012345678",
        "uprn": "77281020",
        "usrn": "12309821",
        "udprn": "1309123",
        "island": "",
        "po_box": "",
        "easting": "297350",
        "gss_code": "E07000041",
        "latitude": "50.7283373",
        "locality": "",
        "northing": "92996",
        "postcode": "TE1 5TT",
        "longitude": "-3.5600416",
        "post_town": "",
        "town_name": "TESTVILLE",
        "change_code": "I",
        "parent_uprn": "",
        "street_name": "TEST STREET",
        "organisation": "",
        "sub_building": "",
        "building_name": "",
        "building_number": "13",
        "last_update_date": "2020-01-06",
        "classification_code": "RD",
        "single_line_address": "13 TEST STREET, TESTVILLE, TE1 5TT",
        "delivery_point_suffix": "2X",
    }
    _uprn2 = {
        "rpc": "2",
        "toid": "osgb1000012233445",
        "uprn": "9913912312",
        "usrn": "14200020",
        "udprn": "1923423423",
        "island": "",
        "po_box": "",
        "easting": "296121.59",
        "gss_code": "E07000041",
        "latitude": "50.741181",
        "locality": "",
        "northing": "96111.42",
        "postcode": "TE5 7TT",
        "longitude": "-3.5384692",
        "post_town": "",
        "town_name": "TESTVILLE",
        "change_code": "I",
        "parent_uprn": "13098123",
        "street_name": "ZETTABYTE ROAD",
        "organisation": "EL CAPITAN CROCKERY",
        "sub_building": "",
        "building_name": "",
        "building_number": "37",
        "last_update_date": "2020-01-06",
        "classification_code": "CO",
        "single_line_address": "EL CAPITAN CROCKERY, 37 ZETTABYTE ROAD, TESTVILLE, TE5 7TT",
        "delivery_point_suffix": "1A",
    }

    def setUp(self):
        self.assertTrue(self.client.login(username="testuser", password="password"))

    def test_fields_lookup(self):

        # test multiple matching records are returned
        self.assertJSONEqual(
            unstream(self.client.get("/addressbase?town_name=testville")),
            [self._uprn1, self._uprn2],
        )

        # test that query parameters are ANDed together
        self.assertJSONEqual(
            unstream(
                self.client.get(
                    "/addressbase?town_name=testville&classification_code=rd"
                )
            ),
            [self._uprn1],
        )

        # # test that query parameter names and values are case-insensitive
        for q in [
            "organisation=EL+CAPITAN+CROCKERY",
            "ORGANISATION=EL+CAPITAN+CROCKERY",
            "organisation=el+capitan+crockery",
            "organisation=El+Capitan+Crockery",
        ]:
            self.assertJSONEqual(
                unstream(self.client.get(f"/addressbase?{q}")),
                [self._uprn2],
            )

    def test_single_line_address_lookup(self):
        pass
        # test that addressbase lookup works for single_line_address

    def test_invalid_query_params(self):
        resp = self.client.get("/addressbase")
        self.assertJSONEqual(
            resp.content,
            {
                "code": 400,
                "error": "At least one AddressBase Core field should be specified in the query parameters.",
            },
        )
        self.assertEqual(resp.status_code, 400)
        # test that addressbase no parameters has no results
        # test that addressbase non-matching params returns no results


def unstream(response):
    # Convert the content of a StreamingHttpResponse back to a single bytestring
    return b"".join(response.streaming_content)
