"""Serializers for the accounts app."""

from rest_framework import serializers

from .models import User


class UserSerializer(serializers.ModelSerializer):
    """List response representation of a User."""

    class Meta:
        model = User
        fields = (
            "id",
            "email",
            "username",
            "first_name",
            "last_name",
            "is_active",
            "created_at",
        )
        read_only_fields = fields


class UserDetailSerializer(serializers.ModelSerializer):
    """Detailed single User representation."""

    class Meta:
        model = User
        fields = (
            "id",
            "email",
            "username",
            "first_name",
            "last_name",
            "is_active",
            "is_staff",
            "created_at",
            "updated_at",
        )
        read_only_fields = fields


class UserCreateSerializer(serializers.ModelSerializer):
    """Validation serializer for user creation."""

    password = serializers.CharField(write_only=True, min_length=8)

    class Meta:
        model = User
        fields = (
            "email",
            "password",
            "first_name",
            "last_name",
            "username",
        )

    def validate_email(self, value):
        normalized_email = value.lower().strip()
        if User.objects.filter(email=normalized_email).exists():
            raise serializers.ValidationError("A user with this email already exists.")
        return normalized_email


class UserUpdateSerializer(serializers.ModelSerializer):
    """Validation serializer for updating user profile fields."""

    class Meta:
        model = User
        fields = (
            "first_name",
            "last_name",
            "username",
        )


class RegisterSerializer(serializers.Serializer):
    """Validation serializer for user registration.

    Handles email normalization, whitespace trimming, password confirmation,
    and Django password strength validation. Contains no business logic —
    user creation is delegated to the service layer.
    """

    email = serializers.EmailField(required=True)
    password = serializers.CharField(write_only=True, required=True, min_length=8)
    confirm_password = serializers.CharField(
        write_only=True, required=True, min_length=8
    )
    first_name = serializers.CharField(required=True, max_length=150)
    last_name = serializers.CharField(required=True, max_length=150)

    def validate_email(self, value):
        normalized = value.lower().strip()
        if User.objects.filter(email=normalized).exists():
            raise serializers.ValidationError("A user with this email already exists.")
        return normalized

    def validate_first_name(self, value):
        return value.strip()

    def validate_last_name(self, value):
        return value.strip()

    def validate(self, attrs):
        password = attrs.get("password")
        confirm_password = attrs.get("confirm_password")

        if password != confirm_password:
            raise serializers.ValidationError(
                {"confirm_password": "Passwords do not match."}
            )

        # Run Django's AUTH_PASSWORD_VALIDATORS against the password
        from django.contrib.auth.password_validation import validate_password

        try:
            validate_password(password)
        except serializers.DjangoValidationError as exc:
            raise serializers.ValidationError({"password": list(exc.messages)})

        return attrs


class LoginSerializer(serializers.Serializer):
    """Validation serializer for user login.

    Validates that email and password are provided, normalises the email.
    Contains no authentication logic — that belongs in the service layer.
    """

    email = serializers.EmailField(required=True)
    password = serializers.CharField(required=True, write_only=True)

    def validate_email(self, value):
        return value.lower().strip()


class TokenRefreshSerializer(serializers.Serializer):
    """Validation serializer for token refresh request."""

    refresh = serializers.CharField(required=True)


class LogoutSerializer(serializers.Serializer):
    """Validation serializer for user logout request."""

    refresh = serializers.CharField(required=True)


class ChangePasswordSerializer(serializers.Serializer):
    """Validation serializer for change password endpoint."""

    current_password = serializers.CharField(required=True, write_only=True)
    new_password = serializers.CharField(required=True, write_only=True, min_length=8)
    confirm_password = serializers.CharField(
        required=True, write_only=True, min_length=8
    )

    def validate(self, attrs):
        current_password = attrs.get("current_password")
        new_password = attrs.get("new_password")
        confirm_password = attrs.get("confirm_password")

        if new_password != confirm_password:
            raise serializers.ValidationError(
                {"confirm_password": "New passwords do not match."}
            )

        if current_password == new_password:
            raise serializers.ValidationError(
                {"new_password": "New password cannot be the same as current password."}
            )

        from django.contrib.auth.password_validation import validate_password

        try:
            validate_password(new_password)
        except serializers.DjangoValidationError as exc:
            raise serializers.ValidationError({"new_password": list(exc.messages)})

        return attrs


class VerifyEmailSerializer(serializers.Serializer):
    """Validation serializer for email verification request."""

    token = serializers.CharField(required=True)


class ResendVerificationSerializer(serializers.Serializer):
    """Validation serializer for resend verification email request."""

    email = serializers.EmailField(required=True)

    def validate_email(self, value):
        return value.lower().strip()


class ForgotPasswordSerializer(serializers.Serializer):
    """Validation serializer for forgot password request."""

    email = serializers.EmailField(required=True)

    def validate_email(self, value):
        return value.lower().strip()


class ResetPasswordSerializer(serializers.Serializer):
    """Validation serializer for reset password request."""

    token = serializers.CharField(required=True)
    new_password = serializers.CharField(required=True, write_only=True, min_length=8)
    confirm_password = serializers.CharField(
        required=True, write_only=True, min_length=8
    )

    def validate(self, attrs):
        new_password = attrs.get("new_password")
        confirm_password = attrs.get("confirm_password")

        if new_password != confirm_password:
            raise serializers.ValidationError(
                {"confirm_password": "Passwords do not match."}
            )

        from django.contrib.auth.password_validation import validate_password

        try:
            validate_password(new_password)
        except serializers.DjangoValidationError as exc:
            raise serializers.ValidationError({"new_password": list(exc.messages)})

        return attrs
