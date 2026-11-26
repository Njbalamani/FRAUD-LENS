import importlib.util
import math
from collections import Counter
from pathlib import Path

import numpy as np

from django.conf import settings

from apps.core.utils import clamp, safe_float

from .models import ModelPerformance, RiskScore

FEATURE_NAMES = (
    "amount_log",
    "amount_z",
    "hour",
    "is_night",
    "velocity_1h",
    "velocity_24h",
    "counterparty_seen",
    "device_seen",
    "location_seen",
    "is_new_counterparty",
    "is_new_device",
    "transaction_type_code",
    "channel_code",
    "status_code",
)


def categorical_code(value):
    text = str(value or "").lower()
    if not text:
        return 0.0
    total = 0
    for index, char in enumerate(text[:32]):
        total += (index + 1) * ord(char)
    return (total % 997) / 997.0


def normalize_importance(values):
    array = np.asarray(values, dtype=float)
    if array.ndim == 3:
        array = np.mean(np.abs(array), axis=2)
    if array.ndim == 2:
        array = np.mean(np.abs(array), axis=0)
    array = np.abs(array).reshape(-1)
    if array.size == 0:
        return {}
    return {name: float(value) for name, value in zip(FEATURE_NAMES[: array.size], array)}


def build_feature_frame(transactions):
    ordered = sorted(transactions, key=lambda item: item.timestamp)
    amounts = np.array([safe_float(item.amount) for item in ordered], dtype=float)
    mean = float(amounts.mean()) if amounts.size else 0.0
    std = float(amounts.std()) if amounts.size else 0.0
    timestamps = np.array([item.timestamp.timestamp() if item.timestamp else 0.0 for item in ordered], dtype=float)

    seen_counterparties = set()
    seen_devices = set()
    seen_locations = set()
    rows = []

    for index, transaction in enumerate(ordered):
        timestamp = timestamps[index]
        hour = transaction.timestamp.hour if transaction.timestamp else 12
        velocity_1h = int(np.sum((timestamps[max(0, index - 30) : index + 1] >= timestamp - 3600)))
        velocity_24h = int(np.sum((timestamps[max(0, index - 200) : index + 1] >= timestamp - 86400)))
        counterparty = transaction.counterparty_reference or ""
        device = transaction.device_reference or ""
        location = transaction.location or ""
        row = {
            "amount_log": math.log1p(max(0.0, safe_float(transaction.amount))),
            "amount_z": (safe_float(transaction.amount) - mean) / std if std else 0.0,
            "hour": float(hour),
            "is_night": 1.0 if hour < 6 or hour >= 22 else 0.0,
            "velocity_1h": float(velocity_1h),
            "velocity_24h": float(velocity_24h),
            "counterparty_seen": 1.0 if counterparty and counterparty in seen_counterparties else 0.0,
            "device_seen": 1.0 if device and device in seen_devices else 0.0,
            "location_seen": 1.0 if location and location in seen_locations else 0.0,
            "is_new_counterparty": 0.0 if counterparty and counterparty in seen_counterparties else 1.0,
            "is_new_device": 0.0 if device and device in seen_devices else 1.0,
            "transaction_type_code": categorical_code(transaction.transaction_type),
            "channel_code": categorical_code(transaction.channel),
            "status_code": categorical_code(transaction.status),
        }
        rows.append(row)
        if counterparty:
            seen_counterparties.add(counterparty)
        if device:
            seen_devices.add(device)
        if location:
            seen_locations.add(location)
    return ordered, np.array([[row[name] for name in FEATURE_NAMES] for row in rows], dtype=float), rows


def artifact_path(organization):
    directory = Path(settings.FRAUDLENS_MODEL_DIR)
    directory.mkdir(parents=True, exist_ok=True)
    return directory / f"organization_{organization.id}_fraud_model.joblib"


def score_transactions(organization, transactions):
    ordered, matrix, rows = build_feature_frame(transactions)
    if matrix.size == 0:
        return [], [], [], None, rows

    try:
        import joblib
        from sklearn.ensemble import IsolationForest
    except ImportError:
        return ordered, [0.0] * len(ordered), [0.0] * len(ordered), None, rows

    anomaly_scores = [0.0] * len(ordered)
    if len(ordered) >= 8:
        detector = IsolationForest(n_estimators=120, contamination="auto", random_state=42, n_jobs=1)
        detector.fit(matrix)
        raw_scores = -detector.score_samples(matrix)
        low = float(np.percentile(raw_scores, 5))
        high = float(np.percentile(raw_scores, 95))
        if high > low:
            anomaly_scores = [clamp(float((value - low) / (high - low) * 100), 0, 100) for value in raw_scores]
        else:
            anomaly_scores = [50.0] * len(ordered)

    labels = np.array([1 if transaction.is_fraud_label else 0 for transaction in ordered], dtype=int)
    counts = Counter(labels.tolist())
    model_scores = [float(value) for value in anomaly_scores]
    performance = None

    if len(ordered) >= 12 and len(counts) == 2 and min(counts.values()) >= 2:
        try:
            from sklearn.metrics import accuracy_score, confusion_matrix, f1_score, precision_score, recall_score, roc_auc_score

            xgboost_enabled = settings.FRAUDLENS_ENABLE_XGBOOST and importlib.util.find_spec("xgboost") is not None
            if xgboost_enabled:
                from xgboost import XGBClassifier

                classifier = XGBClassifier(
                    n_estimators=120,
                    max_depth=4,
                    learning_rate=0.08,
                    subsample=0.9,
                    colsample_bytree=0.9,
                    eval_metric="logloss",
                    random_state=42,
                )
                algorithm = "XGBClassifier"
            else:
                from sklearn.ensemble import RandomForestClassifier

                classifier = RandomForestClassifier(
                    n_estimators=160,
                    min_samples_leaf=2,
                    max_features="sqrt",
                    class_weight="balanced_subsample",
                    random_state=42,
                    n_jobs=1,
                )
                algorithm = "RandomForestClassifier"
            classifier.fit(matrix, labels)
            probabilities = classifier.predict_proba(matrix)
            positive_index = list(classifier.classes_).index(1)
            probabilities = probabilities[:, positive_index]
            model_scores = [clamp(float(value * 100), 0, 100) for value in probabilities]
            predictions = (probabilities >= 0.5).astype(int)
            importance = normalize_importance(getattr(classifier, "feature_importances_", []))
            confusion = confusion_matrix(labels, predictions).tolist()
            performance = ModelPerformance.objects.create(
                organization=organization,
                algorithm=algorithm,
                samples=len(ordered),
                positive_samples=counts.get(1, 0),
                accuracy=float(accuracy_score(labels, predictions)),
                precision=float(precision_score(labels, predictions, zero_division=0)),
                recall=float(recall_score(labels, predictions, zero_division=0)),
                f1_score=float(f1_score(labels, predictions, zero_division=0)),
                roc_auc=float(roc_auc_score(labels, probabilities)) if len(set(labels.tolist())) == 2 else None,
                confusion_matrix=confusion,
                feature_importance=importance,
                threshold=0.5,
                metadata={"feature_names": list(FEATURE_NAMES), "xgboost": xgboost_enabled},
            )
            joblib.dump(
                {
                    "classifier": classifier,
                    "detector": detector if len(ordered) >= 8 else None,
                    "features": list(FEATURE_NAMES),
                    "algorithm": algorithm,
                },
                artifact_path(organization),
            )
        except Exception:
            model_scores = [float(value) for value in anomaly_scores]
            performance = None

    return ordered, model_scores, anomaly_scores, performance, rows


def feature_contributions(row, model_score, anomaly_score, rule_score):
    weights = {
        "amount_log": row.get("amount_z", 0.0) * 16,
        "amount_z": row.get("amount_z", 0.0) * 18,
        "hour": row.get("is_night", 0.0) * 12,
        "is_night": row.get("is_night", 0.0) * 14,
        "velocity_1h": min(row.get("velocity_1h", 0.0), 8) * 4,
        "velocity_24h": min(row.get("velocity_24h", 0.0), 30) * 0.8,
        "is_new_counterparty": row.get("is_new_counterparty", 0.0) * 11,
        "is_new_device": row.get("is_new_device", 0.0) * 12,
        "location_seen": (1.0 - row.get("location_seen", 0.0)) * 6,
        "counterparty_seen": (1.0 - row.get("counterparty_seen", 0.0)) * 6,
        "device_seen": (1.0 - row.get("device_seen", 0.0)) * 6,
        "model_score": (model_score - 50) * 0.35,
        "anomaly_score": (anomaly_score - 50) * 0.25,
        "rule_score": rule_score * 0.2,
    }
    return {key: round(float(value), 3) for key, value in weights.items()}


def global_explanation(organization):
    performance = ModelPerformance.objects.filter(organization=organization).order_by("-trained_at").first()
    scores = list(RiskScore.objects.filter(organization=organization).order_by("-risk_score")[:500])
    importance = dict(performance.feature_importance or {}) if performance else {}
    if not importance:
        totals = Counter()
        for score in scores:
            for name, value in (score.feature_contributions or {}).items():
                totals[name] += abs(safe_float(value))
        importance = dict(totals)
    total = sum(abs(safe_float(value)) for value in importance.values()) or 1.0
    ranked = sorted(
        ((name, round(abs(safe_float(value)) / total * 100, 2)) for name, value in importance.items()),
        key=lambda item: item[1],
        reverse=True,
    )
    finding_counts = Counter(
        finding.kind
        for score in scores
        if score.finding
        for finding in [score.finding]
    )
    return {
        "status": "ready" if performance or scores else "not_trained",
        "algorithm": performance.algorithm if performance else "rules-and-heuristics",
        "metrics": {
            "samples": performance.samples if performance else len(scores),
            "accuracy": performance.accuracy if performance else None,
            "precision": performance.precision if performance else None,
            "recall": performance.recall if performance else None,
            "f1_score": performance.f1_score if performance else None,
            "roc_auc": performance.roc_auc if performance else None,
            "confusion_matrix": performance.confusion_matrix if performance else [],
        },
        "feature_importance": [{"feature": name, "percent": value} for name, value in ranked[:20]],
        "finding_counts": dict(finding_counts),
        "high_risk_count": sum(1 for score in scores if score.risk_score >= settings.FRAUDLENS_HIGH_RISK_THRESHOLD),
        "evaluated_transactions": len(scores),
        "limitations": [
            "Scores are decision support and must not automatically block accounts or transactions.",
            "Synthetic labels can overstate real-world performance; false positives and false negatives are expected.",
            "Investigators must review evidence before escalating or closing a case.",
        ],
    }


def explain_transaction(risk_score):
    contributions = risk_score.feature_contributions or {}
    ranked = sorted(contributions.items(), key=lambda item: abs(safe_float(item[1])), reverse=True)
    return {
        "transaction_id": risk_score.transaction.transaction_id,
        "risk_score": risk_score.risk_score,
        "risk_level": risk_score.risk_level,
        "reasons": risk_score.reasons or [],
        "contributions": [{"feature": name, "value": float(value)} for name, value in ranked],
        "model_score": risk_score.model_score,
        "anomaly_score": risk_score.anomaly_score,
        "rule_score": risk_score.rule_score,
    }
