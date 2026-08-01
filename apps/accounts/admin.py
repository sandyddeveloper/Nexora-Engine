"""Django Admin registration and custom admin interfaces for the accounts domain."""

from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as DjangoUserAdmin
from django.utils.translation import gettext_lazy as _

from .models import (
    Device,
    EmailVerificationToken,
    LoginHistory,
    PasswordResetToken,
    User,
    UserPreference,
    UserProfile,
    UserSession,
)


@admin.register(User)
class UserAdmin(DjangoUserAdmin):
    """Admin configuration for User identity model."""

    list_display = (
        "email",
        "username",
        "first_name",
        "last_name",
        "status",
        "email_verified",
        "is_active",
        "is_staff",
        "created_at",
    )
    list_filter = (
        "status",
        "email_verified",
        "phone_verified",
        "is_active",
        "is_staff",
        "is_superuser",
        "created_at",
    )
    search_fields = ("email", "username", "first_name", "last_name", "phone_number")
    ordering = ("-created_at",)
    readonly_fields = (
        "id",
        "created_at",
        "updated_at",
        "deleted_at",
        "last_login",
        "last_login_ip",
        "last_login_device",
        "failed_login_attempts",
        "locked_until",
        "password_changed_at",
    )

    fieldsets = (
        (None, {"fields": ("email", "username", "password")}),
        (
            _("Personal Information"),
            {
                "fields": (
                    "first_name",
                    "last_name",
                    "display_name",
                    "avatar",
                    "date_of_birth",
                    "gender",
                    "phone_number",
                )
            },
        ),
        (
            _("Status & Verification"),
            {
                "fields": (
                    "status",
                    "is_active",
                    "email_verified",
                    "email_verified_at",
                    "phone_verified",
                    "phone_verified_at",
                )
            },
        ),
        (
            _("Security & Audit"),
            {
                "fields": (
                    "failed_login_attempts",
                    "locked_until",
                    "password_changed_at",
                    "last_login_ip",
                    "last_login_device",
                    "last_login",
                )
            },
        ),
        (
            _("Preferences & Localization"),
            {"fields": ("language", "timezone", "theme")},
        ),
        (
            _("Permissions & Groups"),
            {
                "fields": (
                    "is_staff",
                    "is_superuser",
                    "groups",
                    "user_permissions",
                )
            },
        ),
        (
            _("System Timestamps & Audit"),
            {
                "fields": (
                    "id",
                    "created_at",
                    "updated_at",
                    "created_by",
                    "updated_by",
                    "deleted_at",
                )
            },
        ),
    )

    add_fieldsets = (
        (
            None,
            {
                "classes": ("wide",),
                "fields": (
                    "email",
                    "username",
                    "password1",
                    "password2",
                    "first_name",
                    "last_name",
                ),
            },
        ),
    )

    actions = ["activate_selected_users", "deactivate_selected_users", "soft_delete_users"]

    @admin.action(description=_("Activate selected users"))
    def activate_selected_users(self, request, queryset):
        queryset.update(is_active=True, status="ACTIVE")

    @admin.action(description=_("Deactivate selected users"))
    def deactivate_selected_users(self, request, queryset):
        queryset.update(is_active=False, status="INACTIVE")

    @admin.action(description=_("Soft-delete selected users"))
    def soft_delete_users(self, request, queryset):
        for user in queryset:
            user.delete(soft=True)


@admin.register(UserProfile)
class UserProfileAdmin(admin.ModelAdmin):
    """Admin configuration for UserProfile model."""

    list_display = (
        "user",
        "country",
        "state",
        "city",
        "visibility",
        "created_at",
    )
    list_filter = ("visibility", "country", "created_at")
    search_fields = ("user__email", "user__username", "country", "city", "bio")
    ordering = ("-created_at",)
    readonly_fields = ("id", "created_at", "updated_at", "deleted_at")


@admin.register(UserPreference)
class UserPreferenceAdmin(admin.ModelAdmin):
    """Admin configuration for UserPreference model."""

    list_display = (
        "user",
        "language",
        "timezone",
        "theme",
        "email_notifications",
        "push_notifications",
        "two_factor_enabled",
    )
    list_filter = (
        "theme",
        "language",
        "email_notifications",
        "push_notifications",
        "two_factor_enabled",
    )
    search_fields = ("user__email", "user__username", "timezone")
    ordering = ("-created_at",)
    readonly_fields = ("id", "created_at", "updated_at", "deleted_at")


@admin.register(Device)
class DeviceAdmin(admin.ModelAdmin):
    """Admin configuration for Device tracking model."""

    list_display = (
        "user",
        "device_name",
        "device_type",
        "browser",
        "os",
        "ip_address",
        "is_trusted",
        "last_active",
    )
    list_filter = ("device_type", "is_trusted", "last_active")
    search_fields = ("user__email", "device_name", "fingerprint", "ip_address", "browser", "os")
    ordering = ("-last_active",)
    readonly_fields = ("id", "created_at", "updated_at", "deleted_at", "last_active")


@admin.register(UserSession)
class UserSessionAdmin(admin.ModelAdmin):
    """Admin configuration for UserSession model."""

    list_display = (
        "jti",
        "user",
        "status",
        "device",
        "ip_address",
        "login_time",
        "last_activity",
        "refresh_token_expires_at",
    )
    list_filter = ("status", "login_time", "last_activity")
    search_fields = ("jti", "user__email", "refresh_token_hash", "ip_address")
    ordering = ("-last_activity",)
    readonly_fields = (
        "id",
        "created_at",
        "updated_at",
        "deleted_at",
        "login_time",
        "last_activity",
        "logout_time",
    )
    actions = ["revoke_selected_sessions"]

    @admin.action(description=_("Revoke selected active sessions"))
    def revoke_selected_sessions(self, request, queryset):
        queryset.update(status="REVOKED", is_current=False)


@admin.register(LoginHistory)
class LoginHistoryAdmin(admin.ModelAdmin):
    """Admin configuration for LoginHistory model."""

    list_display = (
        "event_type",
        "user",
        "email_attempted",
        "status",
        "ip_address",
        "location",
        "timestamp",
    )
    list_filter = ("event_type", "status", "timestamp")
    search_fields = ("user__email", "email_attempted", "ip_address", "failure_reason")
    ordering = ("-timestamp",)
    readonly_fields = ("id", "created_at", "updated_at", "deleted_at", "timestamp")


@admin.register(PasswordResetToken)
class PasswordResetTokenAdmin(admin.ModelAdmin):
    """Admin configuration for PasswordResetToken model."""

    list_display = (
        "user",
        "is_used",
        "expires_at",
        "used_at",
        "ip_address",
        "created_at",
    )
    list_filter = ("is_used", "expires_at", "created_at")
    search_fields = ("user__email", "token_hash", "ip_address")
    ordering = ("-created_at",)
    readonly_fields = ("id", "created_at", "updated_at", "deleted_at", "used_at")


@admin.register(EmailVerificationToken)
class EmailVerificationTokenAdmin(admin.ModelAdmin):
    """Admin configuration for EmailVerificationToken model."""

    list_display = (
        "user",
        "is_used",
        "expires_at",
        "used_at",
        "ip_address",
        "created_at",
    )
    list_filter = ("is_used", "expires_at", "created_at")
    search_fields = ("user__email", "token_hash", "ip_address")
    ordering = ("-created_at",)
    readonly_fields = ("id", "created_at", "updated_at", "deleted_at", "used_at")
