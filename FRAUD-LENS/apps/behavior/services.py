from collections import Counter
from datetime import timedelta
from decimal import Decimal
from statistics import median, pstdev

from django.conf import settings
from django.db.models import Avg, Max, Min
from django.utils import timezone

from apps.core.middleware import suspend_audit

from .models import AccountBehaviorProfile


def rebuild_profiles(organization, days=None):
    window = days or settings.FRAUDLENS_BASELINE_WINDOW_DAYS
    cutoff = timezone.now() - timedelta(days=window)
    profiles = []
    for account in organization.financial_accounts.all():
        transactions = list(account.transactions.filter(timestamp__gte=cutoff).order_by("timestamp"))
        amounts = [float(item.amount) for item in transactions]
        aggregates = account.transactions.filter(timestamp__gte=cutoff).aggregate(
            average=Avg("amount"),
            minimum=Min("amount"),
            maximum=Max("amount"),
        )
        hours = Counter(str(item.timestamp.hour) for item in transactions if item.timestamp)
        counterparties = Counter(item.counterparty_reference for item in transactions if item.counterparty_reference)
        locations = Counter(item.location for item in transactions if item.location)
        channels = Counter(item.channel for item in transactions if item.channel)
        devices = Counter(item.device_reference for item in transactions if item.device_reference)
        span_days = max(1, (timezone.now() - cutoff).days)
        values = {
            "organization": organization,
            "account": account,
            "baseline_window_days": window,
            "transaction_count": len(transactions),
            "avg_amount": aggregates["average"] or Decimal("0"),
            "median_amount": Decimal(str(round(median(amounts), 2))) if amounts else Decimal("0"),
            "std_amount": Decimal(str(round(pstdev(amounts), 2))) if len(amounts) > 1 else Decimal("0"),
            "min_amount": aggregates["minimum"] or Decimal("0"),
            "max_amount": aggregates["maximum"] or Decimal("0"),
            "avg_daily_count": round(len(transactions) / span_days, 3),
            "typical_hours": [int(value) for value, _ in hours.most_common(8)],
            "common_counterparties": [value for value, _ in counterparties.most_common(10)],
            "common_locations": [value for value, _ in locations.most_common(10)],
            "common_channels": [value for value, _ in channels.most_common(8)],
            "typical_devices": [value for value, _ in devices.most_common(10)],
            "first_seen": transactions[0].timestamp if transactions else None,
            "last_seen": transactions[-1].timestamp if transactions else None,
            "metadata": {"synthetic_safe": True, "source": "observed_transactions"},
        }
        with suspend_audit():
            profile, _ = AccountBehaviorProfile.objects.update_or_create(account=account, defaults=values)
        profiles.append(profile)
    return profiles


def explain_anomalies(organization, limit=50):
    from apps.core.utils import safe_float
    from apps.detection.models import RiskScore

    scores = RiskScore.objects.filter(organization=organization, risk_score__gte=50).select_related("transaction", "transaction__account").order_by("-risk_score")[:limit]
    results = []
    for score in scores:
        profile = AccountBehaviorProfile.objects.filter(account=score.transaction.account).first()
        if not profile:
            continue
        transaction = score.transaction
        deviations = []
        if profile.typical_hours and transaction.timestamp.hour not in profile.typical_hours:
            deviations.append("hour outside typical window")
        if profile.typical_devices and transaction.device_reference not in profile.typical_devices:
            deviations.append("device outside baseline")
        if profile.common_counterparties and transaction.counterparty_reference not in profile.common_counterparties:
            deviations.append("counterparty outside baseline")
        if profile.common_locations and transaction.location not in profile.common_locations:
            deviations.append("location outside baseline")
        average = safe_float(profile.avg_amount)
        if average and safe_float(transaction.amount) > average * 3:
            deviations.append("amount above baseline")
        results.append(
            {
                "transaction_id": transaction.transaction_id,
                "account_number": transaction.account.account_number,
                "risk_score": score.risk_score,
                "deviations": deviations,
                "profile": {
                    "avg_amount": float(profile.avg_amount),
                    "std_amount": float(profile.std_amount),
                    "typical_hours": profile.typical_hours,
                    "typical_devices": profile.typical_devices,
                },
            }
        )
    return results
