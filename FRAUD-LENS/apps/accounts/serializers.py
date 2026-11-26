from rest_framework import serializers

from .models import Organization, User


class OrganizationSerializer(serializers.ModelSerializer):
    class Meta:
        model = Organization
        fields = ["id", "name", "slug", "industry", "description", "created_at", "updated_at"]
        read_only_fields = ["id", "created_at", "updated_at"]


class UserSerializer(serializers.ModelSerializer):
    organization_name = serializers.CharField(source="organization.name", read_only=True)

    class Meta:
        model = User
        fields = ["id", "username", "email", "role", "organization", "organization_name", "phone", "is_active", "created_at"]
        read_only_fields = ["id", "created_at"]
