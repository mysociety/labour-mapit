from django.contrib.auth.models import User
from django.test import TestCase
from pprint import pprint

from .utils import LoadTestData


class UPRNAdminTestCase(LoadTestData, TestCase):
    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()
        User.objects.create_user(
            "superuser", "", "password", is_superuser=True, is_staff=True
        )

    def setUp(self):
        self.assertTrue(self.client.login(username="superuser", password="password"))

    def test_uprn_list(self):
        resp = self.client.get("/admin/mapit_labour/uprn/")
        html = resp.content.decode()
        self.assertInHTML(
            """<td class="field-single_line_address"><a href="/admin/mapit_labour/uprn/77281020/change/">13 TEST STREET, TESTVILLE, TE1 5TT""",
            html,
        )

    def test_uprn_search(self):
        resp = self.client.get("/admin/mapit_labour/uprn/", {"q": "test street"})
        self.assertNotContains(resp, "EL CAPITAN CROCKERY")
        self.assertContains(resp, "13 TEST STREET, TESTVILLE, TE1 5TT")

    def test_uprn_edit(self):
        resp = self.client.get("/admin/mapit_labour/uprn/77281020/change/")
        self.assertInHTML(
            """<a href="/uprn/77281020.html" class="viewsitelink">View on site</a>""",
            resp.content.decode(),
        )
