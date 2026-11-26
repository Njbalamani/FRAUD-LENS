import random
from datetime import timedelta

from django.utils import timezone

ACCOUNT_TYPES = ("checking", "savings", "business", "credit")
CHANNELS = ("online", "mobile", "card", "wire", "atm")
LOCATIONS = ("Austin", "Denver", "Seattle", "Boston", "Chicago", "Portland")
DEVICES = ("device-silver-01", "device-silver-02", "device-silver-03", "device-silver-04")
COUNTERPARTIES = (
    "vendor-north-01", "vendor-east-02", "supplier-west-03", "partner-central-04",
    "vendor-north-05", "supplier-east-06", "partner-west-07", "vendor-central-08",
)


def build_accounts(organization_id, count=8):
    accounts = []
    for index in range(1, count + 1):
        accounts.append(
            {
                "organization_id": organization_id,
                "account_number": f"SYN-ACC-{organization_id:03d}-{index:04d}",
                "account_holder": f"Synthetic Holder {index:02d}",
                "account_type": ACCOUNT_TYPES[index % len(ACCOUNT_TYPES)],
                "currency": "USD",
                "status": "active",
                "opened_at": timezone.now() - timedelta(days=400 - index * 7),
                "metadata": {"synthetic": True, "seed_index": index},
            }
        )
    return accounts


def build_transactions(organization_id, accounts, count=360, seed=42):
    generator = random.Random(seed)
    start = timezone.now() - timedelta(days=30)
    rows = []
    fraudulent_indices = set(range(0, count, 19)) | set(range(3, count, 97))
    for index in range(count):
        account = accounts[index % len(accounts)]
        is_fraud = index in fraudulent_indices
        if is_fraud:
            amount = round(generator.uniform(2800, 9800), 2)
            hour = generator.choice([0, 1, 2, 3, 4, 5, 22, 23])
            counterparty = f"unseen-entity-{generator.randint(100, 999)}"
            location = generator.choice(["Unknown", "Cross-border", "Unrecognized"])
            device = f"device-new-{generator.randint(10, 99)}"
            transaction_type = generator.choice(["wire", "transfer", "card"])
        else:
            amount = round(generator.uniform(18, 780), 2)
            hour = generator.randint(8, 19)
            counterparty = generator.choice(COUNTERPARTIES)
            location = generator.choice(LOCATIONS)
            device = generator.choice(DEVICES)
            transaction_type = generator.choice(["transfer", "card", "payment"])
        timestamp = start + timedelta(days=generator.randint(0, 29), hours=hour, minutes=generator.randint(0, 59))
        rows.append(
            {
                "transaction_id": f"SYN-{organization_id:03d}-{index + 1:05d}",
                "organization_id": organization_id,
                "account_number": account["account_number"],
                "account_holder": account["account_holder"],
                "counterparty_reference": counterparty,
                "amount": amount,
                "currency": "USD",
                "transaction_type": transaction_type,
                "channel": generator.choice(CHANNELS) if not is_fraud else "wire",
                "location": location,
                "device_reference": device,
                "status": "completed",
                "timestamp": timestamp.isoformat(),
                "description": "Synthetic transaction for demonstration and testing",
                "is_fraud_label": is_fraud,
            }
        )
    return rows


def build_dataset(organization_id=1, account_count=8, transaction_count=360, seed=42):
    accounts = build_accounts(organization_id, account_count)
    return accounts, build_transactions(organization_id, accounts, transaction_count, seed)
