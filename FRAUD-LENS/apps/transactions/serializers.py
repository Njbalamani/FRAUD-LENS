from rest_framework import serializers

from apps.core.utils import mask_identifier

from .models import FinancialAccount, Transaction, TransactionImport, TransactionRelationship


class FinancialAccountSerializer(serializers.ModelSerializer):
    masked_account_number = serializers.SerializerMethodField()

    class Meta:
        model = FinancialAccount
        fields = [
            "id", "masked_account_number", "account_holder", "account_type",
            "currency", "status", "opened_at", "metadata", "created_at",
        ]
        read_only_fields = fields

    def get_masked_account_number(self, obj):
        return mask_identifier(obj.account_number)


class TransactionSerializer(serializers.ModelSerializer):
    masked_account_number = serializers.SerializerMethodField()
    masked_counterparty = serializers.SerializerMethodField()
    masked_device = serializers.SerializerMethodField()
    risk_score = serializers.IntegerField(source="risk_score.risk_score", read_only=True, default=None)

    class Meta:
        model = Transaction
        fields = [
            "id", "transaction_id", "account", "masked_account_number", "masked_counterparty",
            "amount", "currency", "transaction_type", "channel", "location", "masked_device",
            "status", "timestamp", "description", "is_fraud_label", "source", "risk_score", "created_at",
        ]
        read_only_fields = fields

    def get_masked_account_number(self, obj):
        return mask_identifier(obj.account.account_number)

    def get_masked_counterparty(self, obj):
        return mask_identifier(obj.counterparty_reference)

    def get_masked_device(self, obj):
        return mask_identifier(obj.device_reference)


class TransactionImportSerializer(serializers.ModelSerializer):
    class Meta:
        model = TransactionImport
        fields = [
            "id", "file_name", "column_mapping", "rows_total", "rows_imported", "rows_rejected",
            "duplicate_count", "status", "error_summary", "created_at",
        ]
        read_only_fields = fields


class TransactionRelationshipSerializer(serializers.ModelSerializer):
    masked_source = serializers.SerializerMethodField()
    masked_target = serializers.SerializerMethodField()

    class Meta:
        model = TransactionRelationship
        fields = [
            "id", "masked_source", "masked_target", "relationship_type", "transaction_count",
            "total_amount", "first_seen", "last_seen", "evidence", "created_at",
        ]
        read_only_fields = fields

    def get_masked_source(self, obj):
        return mask_identifier(obj.source_identifier)

    def get_masked_target(self, obj):
        return mask_identifier(obj.target_identifier)
