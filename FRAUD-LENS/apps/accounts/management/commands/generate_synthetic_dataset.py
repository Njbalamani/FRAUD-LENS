import csv
from pathlib import Path

from django.conf import settings
from django.core.management.base import BaseCommand

from apps.transactions.synthetic import build_dataset


class Command(BaseCommand):
    help = "Write a deterministic synthetic transaction CSV for demonstrations and tests."

    def add_arguments(self, parser):
        parser.add_argument("--output", default=str(settings.BASE_DIR / "datasets" / "transactions_synthetic.csv"))
        parser.add_argument("--transactions", type=int, default=360)
        parser.add_argument("--accounts", type=int, default=8)
        parser.add_argument("--seed", type=int, default=42)

    def handle(self, *args, **options):
        _, transactions = build_dataset(
            organization_id=1,
            account_count=options["accounts"],
            transaction_count=options["transactions"],
            seed=options["seed"],
        )
        output = Path(options["output"])
        output.parent.mkdir(parents=True, exist_ok=True)
        fieldnames = list(transactions[0].keys())
        with output.open("w", encoding="utf-8", newline="") as handle:
            writer = csv.DictWriter(handle, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(transactions)
        self.stdout.write(self.style.SUCCESS(f"Wrote {len(transactions)} synthetic transactions to {output}"))
