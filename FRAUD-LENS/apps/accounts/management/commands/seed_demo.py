from django.core.management.base import BaseCommand
from django.utils.dateparse import parse_datetime

from apps.accounts.models import Organization, User
from apps.behavior.services import rebuild_profiles
from apps.core.middleware import suspend_audit
from apps.detection.models import FraudFinding
from apps.detection.services import run_detection
from apps.graph.services import sync_transaction_relationships
from apps.investigations.models import InvestigationCase
from apps.investigations.services import create_case_from_findings
from apps.reports.services import generate_report
from apps.transactions.models import FinancialAccount, Transaction
from apps.transactions.synthetic import build_dataset

DEMO_PASSWORD = "FraudLensDemo!"


class Command(BaseCommand):
    help = "Create a synthetic organization, users, transactions, detection run, and report."

    def add_arguments(self, parser):
        parser.add_argument("--transactions", type=int, default=360)
        parser.add_argument("--accounts", type=int, default=8)
        parser.add_argument("--password", default=DEMO_PASSWORD)
        parser.add_argument("--skip-detection", action="store_true")

    def handle(self, *args, **options):
        organization, _ = Organization.objects.get_or_create(
            slug="aurora-financial-labs",
            defaults={
                "name": "Aurora Financial Labs",
                "industry": "synthetic-financial-services",
                "description": "Demonstration data only. No real accounts or transactions are used.",
            },
        )
        users = {}
        for username, role, is_superuser in (
            ("fraud-admin", User.ROLE_ADMIN, True),
            ("fraud-analyst", User.ROLE_ANALYST, False),
            ("fraud-viewer", User.ROLE_VIEWER, False),
        ):
            user, _ = User.objects.get_or_create(
                username=username,
                defaults={"organization": organization, "role": role, "is_superuser": is_superuser, "is_staff": is_superuser},
            )
            user.organization = organization
            user.role = role
            user.is_superuser = is_superuser
            user.is_staff = is_superuser
            user.set_password(options["password"])
            user.save()
            users[username] = user

        account_rows, transaction_rows = build_dataset(organization.id, options["accounts"], options["transactions"])
        with suspend_audit():
            account_map = {}
            for row in account_rows:
                account, _ = FinancialAccount.objects.update_or_create(
                    organization=organization,
                    account_number=row["account_number"],
                    defaults={key: value for key, value in row.items() if key not in {"organization_id", "account_number"}},
                )
                account_map[row["account_number"]] = account
            existing = set(Transaction.objects.filter(organization=organization).values_list("transaction_id", flat=True))
            prepared = []
            for row in transaction_rows:
                if row["transaction_id"] in existing:
                    continue
                payload = dict(row)
                account_number = payload.pop("account_number")
                payload.pop("organization_id")
                payload.pop("account_holder", None)
                payload["timestamp"] = parse_datetime(payload["timestamp"])
                prepared.append(Transaction(organization=organization, account=account_map[account_number], source="synthetic", **payload))
            Transaction.objects.bulk_create(prepared, batch_size=200)

        transaction_count = Transaction.objects.filter(organization=organization).count()
        result = None
        profile_count = 0
        if not options["skip_detection"]:
            result = run_detection(organization, initiated_by=users["fraud-admin"], force=True)
            profile_count = len(rebuild_profiles(organization))
            sync_transaction_relationships(organization)
            top_findings = list(
                FraudFinding.objects.filter(organization=organization)
                .order_by("-confidence")[:3]
            )
            if top_findings and not InvestigationCase.objects.filter(
                organization=organization,
                title="Synthetic high-risk review",
            ).exists():
                create_case_from_findings(
                    organization,
                    [finding.id for finding in top_findings],
                    created_by=users["fraud-analyst"],
                    title="Synthetic high-risk review",
                    description="Automatically grouped top synthetic findings for analyst demonstration.",
                    priority="high",
                    assigned_to=users["fraud-analyst"],
                )
            generate_report(
                organization,
                created_by=users["fraud-admin"],
                kind="summary",
                file_format="pdf",
                title="FraudLens synthetic demo summary",
                parameters={"days": 30},
            )

        self.stdout.write(self.style.SUCCESS(f"Organization: {organization.name}"))
        self.stdout.write(self.style.SUCCESS(f"Accounts: {len(account_map)} · Transactions: {transaction_count}"))
        self.stdout.write(self.style.SUCCESS(f"Behavior profiles: {profile_count}"))
        self.stdout.write(self.style.SUCCESS(f"Demo login: fraud-admin / {options['password']}"))
        if result:
            self.stdout.write(self.style.SUCCESS(f"Detection: {result['findings_created']} findings, {result['high_risk_count']} high-risk transactions"))
