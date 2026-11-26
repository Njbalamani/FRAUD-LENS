from django.test import TestCase
from django.utils import timezone
from rest_framework.test import APIClient

from apps.accounts.models import Organization, User
from apps.transactions.models import FinancialAccount, Transaction

from .models import DetectionRun, RiskScore
from .services import run_detection


class DetectionTests(TestCase):
    def setUp(self):
        self.organization = Organization.objects.create(name="Detection Ltd", slug="detection-ltd")
        self.user = User.objects.create_user(
            username="detection-admin",
            password="TestingPass123!",
            organization=self.organization,
            role=User.ROLE_ADMIN,
        )
        self.account = FinancialAccount.objects.create(
            organization=self.organization,
            account_number="DET-0001",
            account_holder="Detection Holder",
        )
        for index in range(12):
            fraudulent = index < 4
            Transaction.objects.create(
                organization=self.organization,
                transaction_id=f"DET-{index:04d}",
                account=self.account,
                counterparty_reference=f"CP-{index % 3}",
                device_reference=f"DEV-{index % 2}",
                amount=9000 if fraudulent else 120,
                timestamp=timezone.now(),
                is_fraud_label=fraudulent,
            )

    def test_run_detection_creates_scores_and_findings(self):
        result = run_detection(self.organization, initiated_by=self.user)
        self.assertEqual(result["transactions_analyzed"], 12)
        self.assertEqual(RiskScore.objects.filter(organization=self.organization).count(), 12)
        self.assertGreater(DetectionRun.objects.filter(organization=self.organization).count(), 0)
        self.assertGreater(result["findings_created"], 0)

    def test_explain_endpoint(self):
        run_detection(self.organization, initiated_by=self.user)
        client = APIClient()
        client.force_authenticate(user=self.user)
        response = client.get("/api/detection/explain/")
        self.assertEqual(response.status_code, 200)
        self.assertIn("feature_importance", response.data)
