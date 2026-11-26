from django.test import TestCase
from django.utils import timezone

from apps.accounts.models import Organization
from apps.transactions.models import FinancialAccount, Transaction

from .services import build_graph, detect_clusters


class GraphTests(TestCase):
    def setUp(self):
        self.organization = Organization.objects.create(name="Graph Ltd", slug="graph-ltd")
        self.account = FinancialAccount.objects.create(
            organization=self.organization,
            account_number="GRP-0001",
            account_holder="Graph Holder",
        )
        for index in range(4):
            Transaction.objects.create(
                organization=self.organization,
                transaction_id=f"GRP-{index:04d}",
                account=self.account,
                counterparty_reference="SHARED-CP",
                amount=100 + index,
                timestamp=timezone.now(),
            )

    def test_build_graph_returns_nodes_and_edges(self):
        payload = build_graph(self.organization)["graph"]
        self.assertEqual(payload["stats"]["transaction_count"], 4)
        self.assertGreaterEqual(payload["stats"]["node_count"], 2)
        self.assertEqual(payload["stats"]["edge_count"], 1)

    def test_detect_clusters(self):
        payload = detect_clusters(self.organization)
        self.assertEqual(len(payload["clusters"]), 1)
