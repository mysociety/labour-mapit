from django.test import TestCase
from django.contrib.auth.models import User

from mapit_labour.models import APIKey, UPRN
from .utils import LoadTestData


class APIKeyTests(TestCase):
    def test_api_key_creation(self):
        self.assertEqual(APIKey.objects.count(), 0)
        user = User.objects.create(username="testuser", email="test@example.org")
        self.assertEqual(APIKey.objects.count(), 1)
        self.assertEqual(user.api_key.count(), 1)
        key = user.api_key.first()
        self.assertEqual(len(key.key), 40)
        self.assertEqual(str(key), f"testuser: {key.key}")


class UPRNTests(LoadTestData, TestCase):
    def test_urpn(self):
        uprn = UPRN.objects.get(uprn=77281020)
        self.assertEqual(str(uprn), "77281020")
