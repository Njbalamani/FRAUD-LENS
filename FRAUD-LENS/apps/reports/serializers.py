from rest_framework import serializers

from .models import Report


class ReportSerializer(serializers.ModelSerializer):
    created_by_name = serializers.CharField(source="created_by.username", read_only=True)

    class Meta:
        model = Report
        fields = [
            "id", "title", "kind", "file_format", "file_name", "content_type", "summary",
            "parameters", "created_by", "created_by_name", "created_at",
        ]
        read_only_fields = fields


class ReportGenerateSerializer(serializers.Serializer):
    kind = serializers.ChoiceField(choices=["summary", "transactions", "findings", "cases", "custom"], default="summary")
    file_format = serializers.ChoiceField(choices=["pdf", "csv", "json"], default="pdf")
    title = serializers.CharField(max_length=180, required=False, allow_blank=True)
    days = serializers.IntegerField(min_value=1, max_value=365, default=30)
