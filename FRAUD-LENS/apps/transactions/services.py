import csv
import io
import json
from datetime import datetime, timezone as dt_timezone
from decimal import Decimal, InvalidOperation

from django.conf import settings
from django.utils import timezone
from django.utils.dateparse import parse_datetime

from apps.core.middleware import suspend_audit

from .models import FinancialAccount, Transaction, TransactionImport

DEFAULT_COLUMN_MAPPING = {
    "transaction_id": "transaction_id",
    "account_number": "account_number",
    "account_holder": "account_holder",
    "counterparty_reference": "counterparty_reference",
    "amount": "amount",
    "currency": "currency",
    "transaction_type": "transaction_type",
    "channel": "channel",
    "location": "location",
    "device_reference": "device_reference",
    "status": "status",
    "timestamp": "timestamp",
    "description": "description",
    "is_fraud_label": "is_fraud_label",
}

REQUIRED_FIELDS = ("transaction_id", "account_number", "counterparty_reference", "amount", "timestamp")


def parse_bool(value):
    if value is None or value == "":
        return None
    return str(value).strip().lower() in {"1", "true", "yes", "y", "fraud"}


def parse_timestamp(value):
    if isinstance(value, datetime):
        parsed = value
    else:
        parsed = parse_datetime(str(value).strip()) or datetime.fromisoformat(str(value).strip().replace("Z", "+00:00"))
    if timezone.is_naive(parsed):
        parsed = parsed.replace(tzinfo=dt_timezone.utc)
    return parsed


def normalize_row(row, mapping):
    raw = {}
    for canonical, source in mapping.items():
        raw[canonical] = row.get(source, "")
    errors = []
    for field in REQUIRED_FIELDS:
        if raw.get(field) in (None, ""):
            errors.append(f"missing {field}")
    if errors:
        return None, errors

    try:
        amount = Decimal(str(raw["amount"]).replace(",", "").strip())
    except (InvalidOperation, ValueError):
        errors.append("invalid amount")
        amount = None
    if amount is not None and amount <= 0:
        errors.append("amount must be positive")

    try:
        timestamp = parse_timestamp(raw["timestamp"])
    except (ValueError, TypeError):
        errors.append("invalid timestamp")
        timestamp = None
    if errors:
        return None, errors

    status = str(raw.get("status") or "completed").strip().lower()
    if status not in dict(Transaction.STATUS_CHOICES):
        errors.append("invalid status")
    if errors:
        return None, errors

    return (
        {
            "transaction_id": str(raw["transaction_id"]).strip()[:120],
            "account_number": str(raw["account_number"]).strip()[:80],
            "account_holder": str(raw.get("account_holder") or "Unknown account holder").strip()[:180],
            "counterparty_reference": str(raw["counterparty_reference"]).strip()[:120],
            "amount": amount,
            "currency": str(raw.get("currency") or "USD").strip()[:10].upper(),
            "transaction_type": str(raw.get("transaction_type") or "transfer").strip()[:40],
            "channel": str(raw.get("channel") or "online").strip()[:40],
            "location": str(raw.get("location") or "").strip()[:120],
            "device_reference": str(raw.get("device_reference") or "").strip()[:120],
            "status": status,
            "timestamp": timestamp,
            "description": str(raw.get("description") or "").strip(),
            "is_fraud_label": parse_bool(raw.get("is_fraud_label")),
        },
        [],
    )


def resolve_column_mapping(mapping):
    if not mapping:
        return dict(DEFAULT_COLUMN_MAPPING)
    if isinstance(mapping, str):
        mapping = json.loads(mapping)
    if not isinstance(mapping, dict):
        raise ValueError("column_mapping must be a JSON object")
    resolved = dict(DEFAULT_COLUMN_MAPPING)
    for canonical, source in mapping.items():
        if canonical not in DEFAULT_COLUMN_MAPPING:
            raise ValueError(f"Unsupported canonical field: {canonical}")
        resolved[canonical] = str(source)
    return resolved


def import_transactions_csv(organization, file_obj, file_name, mapping=None, imported_by=None):
    column_mapping = resolve_column_mapping(mapping)
    import_record = TransactionImport.objects.create(
        organization=organization,
        imported_by=imported_by,
        file_name=file_name,
        column_mapping=column_mapping,
        status="pending",
    )

    max_bytes = settings.FRAUDLENS_MAX_UPLOAD_MB * 1024 * 1024
    if getattr(file_obj, "size", 0) > max_bytes:
        import_record.status = "failed"
        import_record.error_summary = [{"row": 0, "errors": [f"file exceeds {settings.FRAUDLENS_MAX_UPLOAD_MB} MB limit"]}]
        import_record.save(update_fields=["status", "error_summary"])
        return import_record

    wrapped = io.TextIOWrapper(file_obj.file, encoding="utf-8-sig", newline="") if hasattr(file_obj, "file") else io.TextIOWrapper(file_obj, encoding="utf-8-sig", newline="")
    reader = csv.DictReader(wrapped)
    existing_ids = set(Transaction.objects.filter(organization=organization).values_list("transaction_id", flat=True))
    account_cache = {}
    prepared = []
    errors = []
    duplicate_count = 0
    rows_total = 0

    for index, row in enumerate(reader, start=2):
        rows_total += 1
        normalized, row_errors = normalize_row(row, column_mapping)
        if row_errors:
            errors.append({"row": index, "errors": row_errors})
            continue
        if normalized["transaction_id"] in existing_ids:
            duplicate_count += 1
            continue
        existing_ids.add(normalized["transaction_id"])
        number = normalized.pop("account_number")
        holder = normalized.pop("account_holder")
        if number not in account_cache:
            account, _ = FinancialAccount.objects.get_or_create(
                organization=organization,
                account_number=number,
                defaults={"account_holder": holder},
            )
            account_cache[number] = account
        prepared.append(Transaction(organization=organization, account=account_cache[number], source="csv", raw_payload={"row": index}, **normalized))

    with suspend_audit():
        Transaction.objects.bulk_create(prepared, batch_size=200)

    import_record.rows_total = rows_total
    import_record.rows_imported = len(prepared)
    import_record.rows_rejected = len(errors)
    import_record.duplicate_count = duplicate_count
    import_record.error_summary = errors[:25]
    import_record.status = "completed" if not errors and rows_total else ("failed" if not prepared and errors else "partial")
    import_record.save()
    return import_record


def import_transactions_from_path(organization, path, mapping=None, imported_by=None):
    with open(path, "rb") as handle:
        handle.name = str(path)
        return import_transactions_csv(organization, handle, path.name, mapping=mapping, imported_by=imported_by)
