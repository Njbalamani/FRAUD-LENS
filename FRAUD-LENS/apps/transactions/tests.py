import io

from django.test import TestCase
from django.utils import timezone
from rest_framework.test import APIClient

from apps.accounts.models import Organization, User
from apps.core.middleware import suspend_audit

from .models import FinancialAccount, Transaction
from .services import import_transactions_csv


class TransactionTests(TestCase):
    def setUp(self):
        self.organization = Organization.objects.create(name="Transactions Ltd", slug="transactions-ltd")
        self.account = FinancialAccount.objects.create(
            organization=self.organization,
            account_number="TEST-0001",
            account_holder="Test Holder",
        )
        with suspend_audit():
            self.user = User.objects.create_user(
                username="tx-admin",
                password="TestingPass123!",
                organization=self.organization,
                role=User.ROLE_ADMIN,
                is_staff=True,
                is_superuser=True,
            )

    def test_import_validates_and_creates_transactions(self):
        content = (
            "transaction_id,account_number,counterparty_reference,amount,timestamp,status\n"
            "TX-1,TEST-0001,CP-1,120.50,2026-01-01T10:00:00Z,completed\n"
            "TX-2,TEST-0001,CP-2,-10,2026-01-01T11:00:00Z,completed\n"
        ).encode("utf-8")
        handle = io.BytesIO(content)
        handle.name = "sample.csv"
        record = import_transactions_csv(self.organization, handle, "sample.csv")
        self.assertEqual(record.rows_total, 2)
        self.assertEqual(record.rows_imported, 1)
        self.assertEqual(record.rows_rejected, 1)
        self.assertEqual(Transaction.objects.count(), 1)

    def test_transaction_serializer_masks_identifiers(self):
        transaction = Transaction.objects.create(
            organization=self.organization,
            transaction_id="TX-MASK",
            account=self.account,
            counterparty_reference="COUNTERPARTY-9999",
            amount=100,
            device_reference="DEVICE-9999",
            timestamp=timezone.now(),
        )
        client = APIClient()
        client.force_authenticate(user=self.user)
        response = client.get("/api/transactions/transactions/")
        self.assertEqual(response.status_code, 200)
        row = next(item for item in response.data["results"] if item["id"] == transaction.id)
        self.assertNotEqual(row["masked_counterparty"], "COUNTERPARTY-9999")
        self.assertTrue(row["masked_counterparty"].endswith("9999"))

    def test_global_summary_endpoint(self):
        Transaction.objects.create(
            organization=self.organization,
            transaction_id="TX-SUMMARY",
            account=self.account,
            counterparty_reference="CP-SUMMARY",
            amount=250,
            timestamp=timezone.now(),
        )
        client = APIClient()
        client.force_authenticate(user=self.user)
        response = client.get("/api/transactions/summary/")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["count"], 1)
