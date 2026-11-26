from django.conf import settings
from django.db import models


class FinancialAccount(models.Model):
    ACCOUNT_TYPES = (
        ("checking", "Checking"),
        ("savings", "Savings"),
        ("credit", "Credit"),
        ("business", "Business"),
    )
    STATUS_CHOICES = (("active", "Active"), ("review", "Review"), ("closed", "Closed"))

    organization = models.ForeignKey("accounts.Organization", on_delete=models.CASCADE, related_name="financial_accounts")
    account_number = models.CharField(max_length=80)
    account_holder = models.CharField(max_length=180)
    account_type = models.CharField(max_length=30, choices=ACCOUNT_TYPES, default="checking")
    currency = models.CharField(max_length=10, default="USD")
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="active")
    opened_at = models.DateTimeField(null=True, blank=True)
    metadata = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["account_number"]
        constraints = [models.UniqueConstraint(fields=["organization", "account_number"], name="uniq_account_per_org")]
        indexes = [models.Index(fields=["organization", "status"])]

    def __str__(self):
        return f"{self.account_number} - {self.account_holder}"


class Transaction(models.Model):
    SOURCE_CHOICES = (("synthetic", "Synthetic"), ("csv", "CSV import"), ("api", "API"))
    STATUS_CHOICES = (("completed", "Completed"), ("pending", "Pending"), ("failed", "Failed"), ("reversed", "Reversed"))

    organization = models.ForeignKey("accounts.Organization", on_delete=models.CASCADE, related_name="transactions")
    transaction_id = models.CharField(max_length=120)
    account = models.ForeignKey(FinancialAccount, on_delete=models.CASCADE, related_name="transactions")
    counterparty_reference = models.CharField(max_length=120)
    amount = models.DecimalField(max_digits=18, decimal_places=2)
    currency = models.CharField(max_length=10, default="USD")
    transaction_type = models.CharField(max_length=40, default="transfer")
    channel = models.CharField(max_length=40, default="online")
    location = models.CharField(max_length=120, blank=True)
    device_reference = models.CharField(max_length=120, blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="completed")
    timestamp = models.DateTimeField()
    description = models.TextField(blank=True)
    is_fraud_label = models.BooleanField(null=True, blank=True)
    source = models.CharField(max_length=20, choices=SOURCE_CHOICES, default="synthetic")
    raw_payload = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-timestamp"]
        constraints = [models.UniqueConstraint(fields=["organization", "transaction_id"], name="uniq_transaction_id_per_org")]
        indexes = [
            models.Index(fields=["organization", "timestamp"]),
            models.Index(fields=["account", "timestamp"]),
            models.Index(fields=["organization", "amount"]),
        ]

    def __str__(self):
        return f"{self.transaction_id} {self.amount}"


class TransactionImport(models.Model):
    STATUS_CHOICES = (("pending", "Pending"), ("completed", "Completed"), ("partial", "Partial"), ("failed", "Failed"))

    organization = models.ForeignKey("accounts.Organization", on_delete=models.CASCADE, related_name="transaction_imports")
    imported_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True)
    file_name = models.CharField(max_length=255)
    column_mapping = models.JSONField(default=dict, blank=True)
    rows_total = models.PositiveIntegerField(default=0)
    rows_imported = models.PositiveIntegerField(default=0)
    rows_rejected = models.PositiveIntegerField(default=0)
    duplicate_count = models.PositiveIntegerField(default=0)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="pending")
    error_summary = models.JSONField(default=list, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.file_name} ({self.status})"


class TransactionRelationship(models.Model):
    RELATIONSHIP_TYPES = (
        ("direct", "Direct transfer"),
        ("fan_in", "Fan-in cluster"),
        ("fan_out", "Fan-out cluster"),
        ("cycle", "Circular chain"),
        ("sequence", "Suspicious sequence"),
    )

    organization = models.ForeignKey("accounts.Organization", on_delete=models.CASCADE, related_name="transaction_relationships")
    source_account = models.ForeignKey(FinancialAccount, on_delete=models.CASCADE, related_name="outgoing_relationships", null=True, blank=True)
    target_account = models.ForeignKey(FinancialAccount, on_delete=models.CASCADE, related_name="incoming_relationships", null=True, blank=True)
    source_identifier = models.CharField(max_length=120)
    target_identifier = models.CharField(max_length=120)
    relationship_type = models.CharField(max_length=30, choices=RELATIONSHIP_TYPES, default="direct")
    transaction_count = models.PositiveIntegerField(default=0)
    total_amount = models.DecimalField(max_digits=20, decimal_places=2, default=0)
    first_seen = models.DateTimeField(null=True, blank=True)
    last_seen = models.DateTimeField(null=True, blank=True)
    evidence = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-last_seen"]
        indexes = [models.Index(fields=["organization", "relationship_type"])]

    def __str__(self):
        return f"{self.source_identifier} -> {self.target_identifier}"
