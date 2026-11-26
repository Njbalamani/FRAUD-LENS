from django.conf import settings
from django.db import models


class DetectionRun(models.Model):
    STATUS_CHOICES = (
        ("running", "Running"),
        ("completed", "Completed"),
        ("failed", "Failed"),
    )

    organization = models.ForeignKey("accounts.Organization", on_delete=models.CASCADE, related_name="detection_runs")
    initiated_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="running")
    mode = models.CharField(max_length=30, default="rules-ml-hybrid")
    transactions_analyzed = models.PositiveIntegerField(default=0)
    findings_created = models.PositiveIntegerField(default=0)
    high_risk_count = models.PositiveIntegerField(default=0)
    average_score = models.FloatField(default=0)
    duration_ms = models.PositiveIntegerField(default=0)
    metrics = models.JSONField(default=dict, blank=True)
    parameters = models.JSONField(default=dict, blank=True)
    error_message = models.TextField(blank=True)
    started_at = models.DateTimeField(auto_now_add=True)
    completed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-started_at"]

    def __str__(self):
        return f"DetectionRun #{self.pk} - {self.organization.name}"


class FraudFinding(models.Model):
    KIND_CHOICES = (
        ("amount", "Unusual amount"),
        ("velocity", "Velocity anomaly"),
        ("counterparty", "New counterparty"),
        ("device", "New device"),
        ("location", "Location anomaly"),
        ("off_hours", "Off-hours activity"),
        ("model", "Model anomaly"),
        ("graph", "Graph anomaly"),
        ("custom", "Custom rule"),
    )
    SEVERITY_CHOICES = (("low", "Low"), ("medium", "Medium"), ("high", "High"), ("critical", "Critical"))
    STATUS_CHOICES = (("open", "Open"), ("investigating", "Investigating"), ("resolved", "Resolved"), ("dismissed", "Dismissed"))

    organization = models.ForeignKey("accounts.Organization", on_delete=models.CASCADE, related_name="findings")
    detection_run = models.ForeignKey(DetectionRun, on_delete=models.CASCADE, related_name="findings", null=True, blank=True)
    transaction = models.ForeignKey("transactions.Transaction", on_delete=models.CASCADE, related_name="findings", null=True, blank=True)
    kind = models.CharField(max_length=30, choices=KIND_CHOICES, default="custom")
    title = models.CharField(max_length=180)
    severity = models.CharField(max_length=20, choices=SEVERITY_CHOICES, default="medium")
    description = models.TextField(blank=True)
    confidence = models.FloatField(default=0)
    evidence = models.JSONField(default=dict, blank=True)
    metadata = models.JSONField(default=dict, blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="open")
    detected_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-detected_at"]
        indexes = [
            models.Index(fields=["organization", "severity"]),
            models.Index(fields=["organization", "status"]),
        ]

    def __str__(self):
        return self.title


class RiskScore(models.Model):
    LEVEL_CHOICES = (("low", "Low"), ("medium", "Medium"), ("high", "High"), ("critical", "Critical"))

    organization = models.ForeignKey("accounts.Organization", on_delete=models.CASCADE, related_name="risk_scores")
    transaction = models.OneToOneField("transactions.Transaction", on_delete=models.CASCADE, related_name="risk_score")
    detection_run = models.ForeignKey(DetectionRun, on_delete=models.SET_NULL, null=True, blank=True, related_name="risk_scores")
    finding = models.ForeignKey(FraudFinding, on_delete=models.SET_NULL, null=True, blank=True, related_name="risk_scores")
    risk_score = models.PositiveSmallIntegerField(default=0)
    risk_level = models.CharField(max_length=20, choices=LEVEL_CHOICES, default="low")
    model_score = models.FloatField(default=0)
    anomaly_score = models.FloatField(default=0)
    rule_score = models.FloatField(default=0)
    reasons = models.JSONField(default=list, blank=True)
    feature_contributions = models.JSONField(default=dict, blank=True)
    computed_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-risk_score"]
        indexes = [
            models.Index(fields=["organization", "risk_score"]),
            models.Index(fields=["risk_level"]),
        ]

    def __str__(self):
        return f"{self.transaction.transaction_id}: {self.risk_score}"


class ModelPerformance(models.Model):
    organization = models.ForeignKey("accounts.Organization", on_delete=models.CASCADE, related_name="model_performance")
    algorithm = models.CharField(max_length=80)
    samples = models.PositiveIntegerField(default=0)
    positive_samples = models.PositiveIntegerField(default=0)
    accuracy = models.FloatField(null=True, blank=True)
    precision = models.FloatField(null=True, blank=True)
    recall = models.FloatField(null=True, blank=True)
    f1_score = models.FloatField(null=True, blank=True)
    roc_auc = models.FloatField(null=True, blank=True)
    confusion_matrix = models.JSONField(default=list, blank=True)
    feature_importance = models.JSONField(default=dict, blank=True)
    threshold = models.FloatField(default=0.5)
    trained_at = models.DateTimeField(auto_now_add=True)
    metadata = models.JSONField(default=dict, blank=True)

    class Meta:
        ordering = ["-trained_at"]

    def __str__(self):
        return f"{self.algorithm} - {self.trained_at:%Y-%m-%d}"
