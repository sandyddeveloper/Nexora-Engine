"""Serializers for the roles app."""

from rest_framework import serializers

from .models import Role


class RoleSerializer(serializers.ModelSerializer):
    """List response representation of a Role."""

    class Meta:
        model = Role
        fields = [
            "id",
            "name",
            "code",
            "description",
            "is_system",
            "is_active",
            "created_at",
        ]
        read_only_fields = fields


class RoleDetailSerializer(serializers.ModelSerializer):
    """Detailed single Role representation."""

    class Meta:
        model = Role
        fields = [
            "id",
            "name",
            "code",
            "description",
            "is_system",
            "is_active",
            "created_at",
            "updated_at",
        ]
        read_only_fields = fields


class RoleCreateSerializer(serializers.Serializer):
    """Validation serializer for creating a role."""

    name = serializers.CharField(max_length=100)
    code = serializers.CharField(max_length=50)
    description = serializers.CharField(required=False, default="", allow_blank=True)
    is_system = serializers.BooleanField(required=False, default=False)

    def validate_code(self, value):
        value = value.upper().strip()
        if Role.objects.filter(code=value).exists():
            raise serializers.ValidationError("A role with this code already exists.")
        return value


class RoleUpdateSerializer(serializers.Serializer):
    """Validation serializer for updating a role."""

    name = serializers.CharField(max_length=100, required=False)
    description = serializers.CharField(required=False, allow_blank=True)
    is_active = serializers.BooleanField(required=False)
