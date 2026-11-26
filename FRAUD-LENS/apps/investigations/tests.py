from django.test import TestCase
from rest_framework.test import APIClient

from apps.accounts.models import Organization, User
from apps.detection.models import FraudFinding

from .models import InvestigationCase


class InvestigationTests(TestCase):
    def setUp(self):
        self.organization = Organization.objects.create(name="Cases Ltd", slug="cases-ltd")
        self.user = User.objects.create_user(
            username="case-admin",
            password="TestingPass123!",
            organization=self.organization,
            role=User.ROLE_ADMIN,
        )

    def test_case_id_is_generated(self):
        case = InvestigationCase.objects.create(
            organization=self.organization,
            title="Review suspicious wire",
            created_by=self.user,
        )
        self.assertTrue(case.case_id.startswith("FL-CASE-"))

    def test_close_requires_resolution_notes(self):
        case = InvestigationCase.objects.create(organization=self.organization, title="Needs notes")
        client = APIClient()
        client.force_authenticate(user=self.user)
        response = client.post(f"/api/investigations/cases/{case.id}/close/", {"resolution_notes": ""}, format="json")
        self.assertEqual(response.status_code, 400)
        response = client.post(f"/api/investigations/cases/{case.id}/close/", {"resolution_notes": "Reviewed and cleared"}, format="json")
        self.assertEqual(response.status_code, 200)

    def test_create_case_from_findings(self):
        findings = [
            FraudFinding.objects.create(
                organization=self.organization,
                kind="amount",
                title="Unusual amount",
                severity="high",
                confidence=91,
            ),
            FraudFinding.objects.create(
                organization=self.organization,
                kind="device",
                title="New device",
                severity="medium",
                confidence=74,
            ),
        ]
        client = APIClient()
        client.force_authenticate(user=self.user)
        response = client.post(
            "/api/investigations/cases/from-findings/",
            {"finding_ids": [finding.id for finding in findings], "priority": "critical"},
            format="json",
        )
        self.assertEqual(response.status_code, 201, response.data)
        case = InvestigationCase.objects.get(id=response.data["id"])
        self.assertEqual(case.findings.count(), 2)
        self.assertEqual(case.priority, "critical")

    def test_create_case_rejects_foreign_findings(self):
        other_organization = Organization.objects.create(name="Other Ltd", slug="other-ltd")
        finding = FraudFinding.objects.create(
            organization=other_organization,
            kind="amount",
            title="Foreign finding",
            severity="high",
        )
        client = APIClient()
        client.force_authenticate(user=self.user)
        response = client.post(
            "/api/investigations/cases/from-findings/",
            {"finding_ids": [finding.id]},
            format="json",
        )
        self.assertEqual(response.status_code, 400)
