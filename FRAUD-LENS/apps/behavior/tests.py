from django.test import TestCase
from django.utils import timezone

from apps.accounts.models import Organization
from apps.transactions.models import FinancialAccount, Transaction

from .models import AccountBehaviorProfile
from .services import rebuild_profiles


class BehaviorTests(TestCase):
    def setUp(self):
        self.organization = Organization.objects.create(name="Behavior Ltd", slug="behavior-ltd")
        self.account = FinancialAccount.objects.create(
            organization=self.organization,
            account_number="BEH-0001",
            account_holder="Behavior Holder",
        )
        for index in range(6):
            Transaction.objects.create(
                organization=self.organization,
                transaction_id=f"BEH-{index:04d}",
                account=self.account,
                counterparty_reference=f"CP-{index % 2}",
                device_reference="DEVICE-KNOWN",
                location="Austin",
                amount=100 + index,
                timestamp=timezone.now(),
            )

    def test_rebuild_profiles_captures_devices(self):
        profiles = rebuild_profiles(self.organization)
        self.assertEqual(len(profiles), 1)
        profile = AccountBehaviorProfile.objects.get(account=self.account)
        self.assertIn("DEVICE-KNOWN", profile.typical_devices)
        self.assertEqual(profile.transaction_count, 6)
