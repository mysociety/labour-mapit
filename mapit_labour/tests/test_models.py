from django.test import TestCase
from django.contrib.auth.models import User

from mapit_labour.models import APIKey


class APIKeyTests(TestCase):
    def test_api_key_creation(self):
        self.assertEqual(APIKey.objects.count(), 0)
        user = User.objects.create(username="testuser", email="test@example.org")
        self.assertEqual(APIKey.objects.count(), 1)
        self.assertEqual(user.api_key.count(), 1)
        self.assertEqual(len(user.api_key.first().key), 40)
