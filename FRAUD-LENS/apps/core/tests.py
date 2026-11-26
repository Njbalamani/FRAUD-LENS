from django.test import Client, TestCase, override_settings
from rest_framework.test import APIClient


class CoreApiTests(TestCase):
    def test_health_endpoint(self):
        client = APIClient()
        response = client.get("/health/")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["status"], "ok")
        self.assertEqual(response.data["version"], "1.0.0")
        self.assertEqual(response.data["checks"]["database"], "ok")

    def test_api_root(self):
        client = APIClient()
        response = client.get("/api/")
        self.assertEqual(response.status_code, 200)
        self.assertIn("endpoints", response.data)

    def test_schema_lists_case_creation_endpoint(self):
        client = APIClient()
        response = client.get("/api/schema/")
        self.assertEqual(response.status_code, 200)
        self.assertIn("/api/investigations/cases/from-findings/", response.data["paths"])

    @override_settings(DEBUG=False, SECURE_SSL_REDIRECT=False)
    def test_custom_404_page(self):
        response = Client().get("/page-that-does-not-exist/")
        self.assertEqual(response.status_code, 404)
        self.assertContains(response, "Page not found", status_code=404)
