from rest_framework import serializers

from apps.core.utils import mask_identifier

from .models import AccountBehaviorProfile


class AccountBehaviorProfileSerializer(serializers.ModelSerializer):
    account_number = serializers.CharField(source="account.account_number", read_only=True)
    masked_account_number = serializers.SerializerMethodField()
    account_holder = serializers.CharField(source="account.account_holder", read_only=True)

    class Meta:
        model = AccountBehaviorProfile
        fields = [
            "id", "account", "account_number", "masked_account_number", "account_holder", "baseline_window_days",
            "transaction_count", "avg_amount", "median_amount", "std_amount", "min_amount", "max_amount",
            "avg_daily_count", "typical_hours", "common_counterparties", "common_locations", "common_channels",
            "typical_devices", "first_seen", "last_seen", "metadata", "updated_at",
        ]
        read_only_fields = fields

    def get_masked_account_number(self, obj):
        return mask_identifier(obj.account.account_number)
