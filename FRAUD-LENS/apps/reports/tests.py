from django.test import TestCase
from rest_framework.test import APIClient

from apps.accounts.models import Organization, User

from .models import Report
from .services import generate_report


class ReportTests(TestCase):
    def setUp(self):
        self.organization = Organization.objects.create(name="Reports Ltd", slug="reports-ltd")

    def test_generate_json_report(self):
        report = generate_report(self.organization, kind="summary", file_format="json", parameters={"days": 7})
        self.assertEqual(report.file_format, "json")
        self.assertIn(b'"summary"', bytes(report.file_data))

    def test_generate_csv_report(self):
        report = generate_report(self.organization, kind="summary", file_format="csv")
        self.assertEqual(report.file_format, "csv")
        self.assertEqual(Report.objects.count(), 1)

    def test_generate_report_api(self):
        user = User.objects.create_user(
            username="report-admin",
            password="TestingPass123!",
            organization=self.organization,
            role=User.ROLE_ADMIN,
        )
        client = APIClient()
        client.force_authenticate(user=user)
        response = client.post(
            "/api/reports/generate/",
            {"title": "API report", "kind": "summary", "file_format": "json", "days": 7},
            format="json",
        )
        self.assertEqual(response.status_code, 201, response.data)
        self.assertEqual(response.data["title"], "API report")
        self.assertEqual(Report.objects.count(), 1)
