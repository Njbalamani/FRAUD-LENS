import time

from django.conf import settings
from django.db.models import Avg
from django.utils import timezone

from apps.accounts.models import Organization
from apps.core.middleware import suspend_audit
from apps.core.utils import clamp, safe_float, sanitize

from . import ml
from .models import DetectionRun, FraudFinding, RiskScore

SEVERITY_ORDER = {"critical": 4, "high": 3, "medium": 2, "low": 1}


def _risk_level(score):
    if score >= 90:
        return "critical"
    if score >= settings.FRAUDLENS_HIGH_RISK_THRESHOLD:
        return "high"
    if score >= 50:
        return "medium"
    return "low"


def _severity_for_score(score):
    if score >= 90:
        return "critical"
    if score >= settings.FRAUDLENS_HIGH_RISK_THRESHOLD:
        return "high"
    if score >= 50:
        return "medium"
    return "low"


def run_detection(organization, initiated_by=None, force=False, parameters=None):
    if isinstance(organization, int):
        organization = Organization.objects.get(pk=organization)
    started = timezone.now()
    run = DetectionRun.objects.create(
        organization=organization,
        initiated_by=initiated_by,
        mode="rules-ml-hybrid",
        status="running",
        parameters=sanitize(parameters or {}),
    )
    transactions = list(organization.transactions.select_related("account").order_by("timestamp"))
    if not transactions:
        run.status = "completed"
        run.completed_at = timezone.now()
        run.duration_ms = int((run.completed_at - started).total_seconds() * 1000)
        run.save(update_fields=["status", "completed_at", "duration_ms"])
        return {"run_id": run.id, "transactions_analyzed": 0, "findings_created": 0, "high_risk_count": 0, "average_score": 0}

    ordered, model_scores, anomaly_scores, performance, feature_rows = ml.score_transactions(organization, transactions)
    pending_findings = []

    def add_finding(transaction, kind, title, severity, description, confidence, evidence):
        pending_findings.append(
            FraudFinding(
                organization=organization,
                detection_run=run,
                transaction=transaction,
                kind=kind,
                title=title[:180],
                severity=severity,
                description=description,
                confidence=clamp(float(confidence), 0, 100),
                evidence=sanitize(evidence),
                metadata={"source": "automated"},
            )
        )

    for index, transaction in enumerate(ordered):
        row = feature_rows[index]
        model_score = float(model_scores[index])
        anomaly_score = float(anomaly_scores[index])
        rule_score = 0.0

        amount_z = safe_float(row.get("amount_z"))
        if amount_z >= settings.FRAUDLENS_AMOUNT_Z_THRESHOLD:
            rule_score += 28
            add_finding(
                transaction,
                "amount",
                "Transaction amount is unusually high",
                "high" if amount_z >= settings.FRAUDLENS_AMOUNT_Z_THRESHOLD * 1.5 else "medium",
                "The amount is materially above this organization's recent transaction baseline.",
                72 + min(20, amount_z * 2),
                {"amount": str(transaction.amount), "amount_z": round(amount_z, 3)},
            )

        velocity_1h = safe_float(row.get("velocity_1h"))
        velocity_24h = safe_float(row.get("velocity_24h"))
        if velocity_1h >= 6 or velocity_24h >= 18:
            rule_score += 18
            add_finding(
                transaction,
                "velocity",
                "Rapid transaction sequence detected",
                "medium",
                "The account generated an unusually high number of transactions in a short interval.",
                68,
                {"velocity_1h": velocity_1h, "velocity_24h": velocity_24h},
            )

        if row.get("is_new_counterparty") and safe_float(row.get("amount_z")) > 1.2:
            rule_score += 14
            add_finding(
                transaction,
                "counterparty",
                "First-time counterparty with elevated value",
                "medium",
                "The counterparty has not appeared earlier in the analyzed window.",
                61,
                {"counterparty": str(transaction.counterparty_reference)},
            )

        if row.get("is_new_device"):
            rule_score += 16
            add_finding(
                transaction,
                "device",
                "Unrecognized device reference",
                "medium",
                "The transaction used a device not seen earlier in the analyzed window.",
                64,
                {"device": str(transaction.device_reference)},
            )

        if row.get("is_night") and safe_float(row.get("amount_z")) > 0.8:
            rule_score += 10
            add_finding(
                transaction,
                "off_hours",
                "High-value off-hours activity",
                "low",
                "The transaction occurred outside normal daytime activity and had elevated value.",
                55,
                {"hour": transaction.timestamp.hour if transaction.timestamp else None},
            )

        if not row.get("location_seen") and safe_float(row.get("amount_z")) > 1.5:
            rule_score += 8
            add_finding(
                transaction,
                "location",
                "Unrecognized transaction location",
                "low",
                "The location has not appeared earlier in the analyzed window.",
                52,
                {"location": str(transaction.location)},
            )

        if anomaly_score >= 75:
            rule_score += 12
            add_finding(
                transaction,
                "model",
                "Isolation Forest anomaly score is elevated",
                _severity_for_score(anomaly_score),
                "An unsupervised model identified this transaction as unusual relative to the cohort.",
                anomaly_score,
                {"anomaly_score": round(anomaly_score, 2)},
            )

        composite = clamp(rule_score * 0.62 + model_score * 0.28 + anomaly_score * 0.18, 0, 100)
        if model_score >= 85 and row.get("is_new_counterparty"):
            composite = clamp(composite + 6, 0, 100)
        score_value = int(round(composite))
        if score_value >= settings.FRAUDLENS_HIGH_RISK_THRESHOLD:
            severity = _severity_for_score(score_value)
            add_finding(
                transaction,
                "model",
                "Composite risk score exceeds review threshold",
                severity,
                "Rule signals, model probability, and anomaly evidence were combined into a high composite score.",
                score_value,
                {
                    "risk_score": score_value,
                    "rule_score": round(rule_score, 2),
                    "model_score": round(model_score, 2),
                    "anomaly_score": round(anomaly_score, 2),
                },
            )

        risk_score = _risk_level(score_value)
        contributions = ml.feature_contributions(row, model_score, anomaly_score, rule_score)
        with suspend_audit():
            RiskScore.objects.update_or_create(
                organization=organization,
                transaction=transaction,
                defaults={
                    "detection_run": run,
                    "risk_score": score_value,
                    "risk_level": risk_score,
                    "model_score": round(model_score, 3),
                    "anomaly_score": round(anomaly_score, 3),
                    "rule_score": round(rule_score, 3),
                    "reasons": [
                        "Elevated amount relative to baseline",
                        "High transaction velocity",
                        "New counterparty or device",
                        "Model anomaly signal",
                    ][: max(1, min(4, int(score_value / 25)))],
                    "feature_contributions": contributions,
                },
            )

    with suspend_audit():
        FraudFinding.objects.bulk_create(pending_findings, batch_size=200)

    created_findings = list(run.findings.select_related("transaction").order_by("-confidence"))
    finding_map = {}
    for finding in created_findings:
        if finding.transaction_id and finding.transaction_id not in finding_map:
            finding_map[finding.transaction_id] = finding
    for transaction in ordered:
        finding = finding_map.get(transaction.id)
        if not finding:
            continue
        RiskScore.objects.filter(transaction=transaction).update(finding=finding)

    run.transactions_analyzed = len(ordered)
    run.findings_created = len(created_findings)
    run.high_risk_count = RiskScore.objects.filter(detection_run=run, risk_score__gte=settings.FRAUDLENS_HIGH_RISK_THRESHOLD).count()
    run.average_score = float(RiskScore.objects.filter(detection_run=run).aggregate(value=Avg("risk_score"))["value"] or 0)
    run.status = "completed"
    run.completed_at = timezone.now()
    run.duration_ms = int((run.completed_at - started).total_seconds() * 1000)
    run.metrics = {
        "algorithm": performance.algorithm if performance else "rules-isolation-forest",
        "performance_id": performance.id if performance else None,
        "model_used": bool(performance),
    }
    run.save()

    return {
        "run_id": run.id,
        "transactions_analyzed": run.transactions_analyzed,
        "findings_created": run.findings_created,
        "high_risk_count": run.high_risk_count,
        "average_score": round(run.average_score, 2),
        "duration_ms": run.duration_ms,
    }
