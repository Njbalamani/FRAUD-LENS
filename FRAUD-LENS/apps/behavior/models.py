from django.db import models


class AccountBehaviorProfile(models.Model):
    organization = models.ForeignKey("accounts.Organization", on_delete=models.CASCADE, related_name="behavior_profiles")
    account = models.OneToOneField("transactions.FinancialAccount", on_delete=models.CASCADE, related_name="behavior_profile")
    baseline_window_days = models.PositiveIntegerField(default=30)
    transaction_count = models.PositiveIntegerField(default=0)
    avg_amount = models.DecimalField(max_digits=18, decimal_places=2, default=0)
    median_amount = models.DecimalField(max_digits=18, decimal_places=2, default=0)
    std_amount = models.DecimalField(max_digits=18, decimal_places=2, default=0)
    min_amount = models.DecimalField(max_digits=18, decimal_places=2, default=0)
    max_amount = models.DecimalField(max_digits=18, decimal_places=2, default=0)
    avg_daily_count = models.FloatField(default=0)
    typical_hours = models.JSONField(default=list, blank=True)
    common_counterparties = models.JSONField(default=list, blank=True)
    common_locations = models.JSONField(default=list, blank=True)
    common_channels = models.JSONField(default=list, blank=True)
    typical_devices = models.JSONField(default=list, blank=True)
    first_seen = models.DateTimeField(null=True, blank=True)
    last_seen = models.DateTimeField(null=True, blank=True)
    metadata = models.JSONField(default=dict, blank=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["account__account_number"]
        indexes = [models.Index(fields=["organization", "updated_at"])]

    def __str__(self):
        return f"Behavior profile for {self.account.account_number}"
