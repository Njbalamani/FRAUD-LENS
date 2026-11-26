from django.test import Client, TestCase

from apps.accounts.models import Organization, User
from apps.detection.models import FraudFinding


class DashboardTests(TestCase):
    def setUp(self):
        self.organization = Organization.objects.create(name="Dashboard Ltd", slug="dashboard-ltd")
        self.user = User.objects.create_user(
            username="dashboard-admin",
            password="TestingPass123!",
            organization=self.organization,
            role=User.ROLE_ADMIN,
        )
        self.client = Client()

    def test_pages_require_authentication(self):
        response = self.client.get("/")
        self.assertEqual(response.status_code, 302)
        self.assertTrue(response.url.startswith("/login/"))

    def test_pages_render_for_authenticated_user(self):
        self.client.force_login(self.user)
        for path in ("/", "/transactions/", "/network/", "/investigations/", "/reports/"):
            response = self.client.get(path)
            self.assertEqual(response.status_code, 200, path)

    def test_dashboard_shows_analysis_context(self):
        self.client.force_login(self.user)
        response = self.client.get("/")
        self.assertContains(response, "Fraud Intelligence Overview")
        self.assertContains(response, "Detection health")
        self.assertContains(response, "Risk trend")
        self.assertContains(response, "dashboard-ltd".replace("-", " ").title())

    def test_investigations_page_exposes_suggested_findings(self):
        finding = FraudFinding.objects.create(
            organization=self.organization,
            kind="amount",
            title="UI triage finding",
            severity="high",
            confidence=88,
        )
        self.client.force_login(self.user)
        response = self.client.get("/investigations/")
        self.assertContains(response, "Create case from findings")
        self.assertContains(response, str(finding.id))

    def test_transactions_page_exposes_csv_upload(self):
        self.client.force_login(self.user)
        response = self.client.get("/transactions/")
        self.assertContains(response, "Import a synthetic CSV file")
        self.assertContains(response, "upload-csv")

    def test_reports_page_exposes_report_builder(self):
        self.client.force_login(self.user)
        response = self.client.get("/reports/")
        self.assertContains(response, "Create an evidence artifact")
        self.assertContains(response, "report-generate-form")
