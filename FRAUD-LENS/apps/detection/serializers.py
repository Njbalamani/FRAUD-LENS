from rest_framework import serializers

from .models import DetectionRun, FraudFinding, ModelPerformance, RiskScore


class DetectionRunSerializer(serializers.ModelSerializer):
    class Meta:
        model = DetectionRun
        fields = [
            "id", "status", "mode", "transactions_analyzed", "findings_created", "high_risk_count",
            "average_score", "duration_ms", "metrics", "parameters", "started_at", "completed_at",
        ]
        read_only_fields = fields


class FraudFindingSerializer(serializers.ModelSerializer):
    transaction_ref = serializers.CharField(source="transaction.transaction_id", read_only=True)

    class Meta:
        model = FraudFinding
        fields = [
            "id", "transaction", "transaction_ref", "detection_run", "kind", "title", "severity",
            "description", "confidence", "evidence", "metadata", "status", "detected_at",
        ]
        read_only_fields = ["id", "detected_at"]


class RiskScoreSerializer(serializers.ModelSerializer):
    transaction_ref = serializers.CharField(source="transaction.transaction_id", read_only=True)
    finding_title = serializers.CharField(source="finding.title", read_only=True)

    class Meta:
        model = RiskScore
        fields = [
            "id", "transaction", "transaction_ref", "risk_score", "risk_level", "model_score",
            "anomaly_score", "rule_score", "reasons", "feature_contributions", "finding",
            "finding_title", "computed_at",
        ]
        read_only_fields = fields


class ModelPerformanceSerializer(serializers.ModelSerializer):
    class Meta:
        model = ModelPerformance
        fields = [
            "id", "algorithm", "samples", "positive_samples", "accuracy", "precision", "recall",
            "f1_score", "roc_auc", "confusion_matrix", "feature_importance", "threshold",
            "trained_at", "metadata",
        ]
        read_only_fields = fields


class DetectionAnalyzeSerializer(serializers.Serializer):
    force = serializers.BooleanField(default=False)
    days = serializers.IntegerField(min_value=1, max_value=365, required=False)
