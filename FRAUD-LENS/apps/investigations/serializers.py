from rest_framework import serializers

from apps.core.utils import mask_identifier

from .models import CaseEvidence, CaseNote, InvestigationCase


class InvestigationCaseSerializer(serializers.ModelSerializer):
    assigned_to_name = serializers.CharField(source="assigned_to.username", read_only=True)
    finding_count = serializers.SerializerMethodField()

    class Meta:
        model = InvestigationCase
        fields = [
            "id", "case_id", "title", "description", "status", "priority", "assigned_to",
            "assigned_to_name", "created_by", "findings", "finding_count", "tags",
            "resolution_notes", "opened_at", "updated_at", "closed_at",
        ]
        read_only_fields = ["id", "case_id", "opened_at", "updated_at"]

    def get_finding_count(self, obj):
        return obj.findings.count()

    def validate(self, attrs):
        if attrs.get("status") in {"resolved", "closed"} and not attrs.get("resolution_notes"):
            raise serializers.ValidationError({"resolution_notes": "Resolution notes are required before closing a case."})
        return attrs


class CaseNoteSerializer(serializers.ModelSerializer):
    author_name = serializers.CharField(source="author.username", read_only=True)

    class Meta:
        model = CaseNote
        fields = ["id", "case", "author", "author_name", "note", "created_at"]
        read_only_fields = ["id", "author", "created_at"]


class CaseEvidenceSerializer(serializers.ModelSerializer):
    added_by_name = serializers.CharField(source="added_by.username", read_only=True)
    masked_file_name = serializers.SerializerMethodField()

    class Meta:
        model = CaseEvidence
        fields = [
            "id", "case", "evidence_type", "title", "description", "file_name", "masked_file_name",
            "content_type", "file_data", "url", "metadata", "added_by", "added_by_name", "created_at",
        ]
        read_only_fields = ["id", "added_by", "created_at"]

    def get_masked_file_name(self, obj):
        return mask_identifier(obj.file_name)


class CaseFromFindingsSerializer(serializers.Serializer):
    finding_ids = serializers.ListField(child=serializers.IntegerField(), allow_empty=False)
    title = serializers.CharField(max_length=180, required=False, allow_blank=True)
    description = serializers.CharField(required=False, allow_blank=True)
    priority = serializers.ChoiceField(choices=InvestigationCase.PRIORITY_CHOICES, default="high")
    assigned_to = serializers.IntegerField(required=False, allow_null=True)
