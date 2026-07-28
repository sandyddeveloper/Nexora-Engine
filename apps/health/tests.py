from django.test import SimpleTestCase
from django.urls import reverse


class HealthEndpointTests(SimpleTestCase):
    def test_health_endpoint_returns_success(self):
        response = self.client.get(reverse("health-check"))
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.json()["success"])

    def test_version_endpoint_returns_version(self):
        response = self.client.get(reverse("version-info"))
        self.assertEqual(response.status_code, 200)
        self.assertIn("version", response.json()["data"])
