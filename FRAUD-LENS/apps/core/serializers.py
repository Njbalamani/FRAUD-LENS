from rest_framework import serializers

from .models import AuditLog


class AuditLogSerializer(serializers.ModelSerializer):
    user_name = serializers.CharField(source="user.username", read_only=True, default=None)

    class Meta:
        model = AuditLog
        fields = ["id", "organization", "user", "user_name", "action", "content_type_label", "object_id", "details", "ip_address", "path", "created_at"]
        read_only_fields = fields
