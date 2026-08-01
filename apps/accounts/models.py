"""Models for the Nexora Engine Authentication & Accounts Domain."""

from django.conf import settings
from django.contrib.auth.models import AbstractBaseUser, PermissionsMixin
from django.db import models
from django.utils import timezone
from django.utils.translation import gettext_lazy as _

from apps.common.models import BaseModel

from .managers import UserManager


# ── TextChoices Enums ────────────────────────────────────────────────────────


class UserStatus(models.TextChoices):
    """Status states for user account lifecycle."""

    ACTIVE = "ACTIVE", _("Active")
    INACTIVE = "INACTIVE", _("Inactive")
    SUSPENDED = "SUSPENDED", _("Suspended")
    LOCKED = "LOCKED", _("Locked")


class GenderChoices(models.TextChoices):
    """Gender identity options."""

    MALE = "MALE", _("Male")
    FEMALE = "FEMALE", _("Female")
    OTHER = "OTHER", _("Other")
    PREFER_NOT_TO_SAY = "PREFER_NOT_TO_SAY", _("Prefer Not To Say")


class ProfileVisibility(models.TextChoices):
    """Scope of visibility for user profiles."""

    PUBLIC = "PUBLIC", _("Public")
    PRIVATE = "PRIVATE", _("Private")
    ORGANIZATION = "ORGANIZATION", _("Organization")
    CONNECTIONS = "CONNECTIONS", _("Connections")


class DeviceType(models.TextChoices):
    """Hardware device classifications."""

    DESKTOP = "DESKTOP", _("Desktop")
    MOBILE = "MOBILE", _("Mobile")
    TABLET = "TABLET", _("Tablet")
    SMART_TV = "SMART_TV", _("Smart TV")
    OTHER = "OTHER", _("Other")
    UNKNOWN = "UNKNOWN", _("Unknown")


class SessionStatus(models.TextChoices):
    """JWT session lifecycle statuses."""

    ACTIVE = "ACTIVE", _("Active")
    EXPIRED = "EXPIRED", _("Expired")
    REVOKED = "REVOKED", _("Revoked")
    LOGGED_OUT = "LOGGED_OUT", _("Logged Out")


class LoginEventType(models.TextChoices):
    """Types of security and login events in audit history."""

    SUCCESS = "SUCCESS", _("Success")
    FAILED = "FAILED", _("Failed")
    LOGOUT = "LOGOUT", _("Logout")
    PASSWORD_RESET = "PASSWORD_RESET", _("Password Reset")
    EMAIL_VERIFICATION = "EMAIL_VERIFICATION", _("Email Verification")
    ACCOUNT_LOCKED = "ACCOUNT_LOCKED", _("Account Locked")


# ── Domain Models ───────────────────────────────────────────────────────────


class User(AbstractBaseUser, PermissionsMixin, BaseModel):
    """Primary User identity model for Nexora Engine platform."""

    username = models.CharField(
        max_length=150,
        unique=True,
        db_index=True,
        help_text=_("Unique username handle."),
    )
    email = models.EmailField(
        max_length=255,
        unique=True,
        db_index=True,
        help_text=_("Primary email address for login and system communications."),
    )
    phone_number = models.CharField(
        max_length=30,
        blank=True,
        null=True,
        db_index=True,
        help_text=_("User contact phone number in E.164 format."),
    )
    first_name = models.CharField(
        max_length=150,
        blank=True,
        default="",
        help_text=_("User given name."),
    )
    last_name = models.CharField(
        max_length=150,
        blank=True,
        default="",
        help_text=_("User family name."),
    )
    display_name = models.CharField(
        max_length=255,
        blank=True,
        default="",
        help_text=_("Public display name."),
    )
    avatar = models.FileField(
        upload_to="avatars/%Y/%m/",
        max_length=512,
        blank=True,
        null=True,
        help_text=_("Profile avatar image URL or file path."),
    )
    date_of_birth = models.DateField(
        null=True,
        blank=True,
        help_text=_("User date of birth."),
    )
    gender = models.CharField(
        max_length=30,
        choices=GenderChoices.choices,
        default=GenderChoices.PREFER_NOT_TO_SAY,
        help_text=_("User gender identity."),
    )
    status = models.CharField(
        max_length=20,
        choices=UserStatus.choices,
        default=UserStatus.ACTIVE,
        db_index=True,
        help_text=_("User account status."),
    )
    is_staff = models.BooleanField(
        default=False,
        help_text=_("Designates whether user can access administrative tools."),
    )
    email_verified = models.BooleanField(
        default=False,
        help_text=_("Designates whether user primary email has been verified."),
    )
    email_verified_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text=_("Timestamp when email was verified."),
    )
    phone_verified = models.BooleanField(
        default=False,
        help_text=_("Designates whether phone number has been verified."),
    )
    phone_verified_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text=_("Timestamp when phone number was verified."),
    )
    last_login_ip = models.GenericIPAddressField(
        null=True,
        blank=True,
        help_text=_("IP address recorded during most recent login."),
    )
    last_login_device = models.ForeignKey(
        "Device",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="users_last_login",
        help_text=_("Device recorded during most recent login."),
    )
    failed_login_attempts = models.PositiveIntegerField(
        default=0,
        help_text=_("Consecutive failed authentication attempts count."),
    )
    locked_until = models.DateTimeField(
        null=True,
        blank=True,
        help_text=_("Timestamp until which account remains locked."),
    )
    password_changed_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text=_("Timestamp when password was last changed."),
    )
    language = models.CharField(
        max_length=10,
        default="en",
        help_text=_("Preferred user interface locale."),
    )
    timezone = models.CharField(
        max_length=50,
        default="UTC",
        help_text=_("Preferred user timezone."),
    )
    theme = models.CharField(
        max_length=20,
        default="SYSTEM",
        help_text=_("Preferred UI display theme."),
    )

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = ["username", "first_name", "last_name"]

    objects = UserManager()

    class Meta:
        verbose_name = _("user")
        verbose_name_plural = _("users")
        indexes = [
            models.Index(fields=["email", "status"], name="idx_user_email_status"),
            models.Index(
                fields=["status", "deleted_at"], name="idx_user_status_deleted"
            ),
        ]

    def __str__(self) -> str:
        return self.email or self.username or "User"

    @property
    def is_email_verified(self) -> bool:
        """Backward compatible getter for email_verified."""
        return self.email_verified

    @is_email_verified.setter
    def is_email_verified(self, value: bool) -> None:
        """Backward compatible setter for email_verified."""
        self.email_verified = value

    def get_full_name(self) -> str:
        """Return user's combined first name and last name."""
        full = f"{self.first_name} {self.last_name}".strip()
        return full or self.display_name or self.username or self.email

    def get_short_name(self) -> str:
        """Return user's first name, display name, or handle."""
        return self.first_name or self.display_name or self.username or self.email


class UserProfile(BaseModel):
    """Detailed profile data linked 1:1 with User identity."""

    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="profile",
        help_text=_("User owner of this profile."),
    )
    bio = models.TextField(
        blank=True,
        default="",
        help_text=_("User biography summary."),
    )
    address = models.CharField(
        max_length=255,
        blank=True,
        default="",
        help_text=_("Street address."),
    )
    country = models.CharField(
        max_length=100,
        blank=True,
        default="",
        db_index=True,
        help_text=_("Country of residence."),
    )
    state = models.CharField(
        max_length=100,
        blank=True,
        default="",
        help_text=_("State, province, or region."),
    )
    city = models.CharField(
        max_length=100,
        blank=True,
        default="",
        help_text=_("City or municipality."),
    )
    postal_code = models.CharField(
        max_length=20,
        blank=True,
        default="",
        help_text=_("ZIP or postal code."),
    )
    website = models.URLField(
        max_length=255,
        blank=True,
        default="",
        help_text=_("Personal or business website URL."),
    )
    linkedin = models.URLField(
        max_length=255,
        blank=True,
        default="",
        help_text=_("LinkedIn profile URL."),
    )
    github = models.URLField(
        max_length=255,
        blank=True,
        default="",
        help_text=_("GitHub profile URL."),
    )
    visibility = models.CharField(
        max_length=20,
        choices=ProfileVisibility.choices,
        default=ProfileVisibility.PUBLIC,
        db_index=True,
        help_text=_("Profile privacy visibility scope."),
    )

    class Meta:
        verbose_name = _("user profile")
        verbose_name_plural = _("user profiles")
        indexes = [
            models.Index(
                fields=["country", "visibility"], name="idx_profile_country_vis"
            ),
        ]

    def __str__(self) -> str:
        return f"Profile for {self.user.email}"


class UserPreference(BaseModel):
    """User operational preferences and interface customization settings."""

    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="preference",
        help_text=_("User owner of these preferences."),
    )
    language = models.CharField(
        max_length=10,
        default="en",
        help_text=_("Interface language locale."),
    )
    timezone = models.CharField(
        max_length=50,
        default="UTC",
        help_text=_("Primary operational timezone."),
    )
    theme = models.CharField(
        max_length=20,
        default="SYSTEM",
        help_text=_("Preferred UI theme code."),
    )
    email_notifications = models.BooleanField(
        default=True,
        help_text=_("Designates whether email notifications are enabled."),
    )
    push_notifications = models.BooleanField(
        default=True,
        help_text=_("Designates whether push notifications are enabled."),
    )
    two_factor_enabled = models.BooleanField(
        default=False,
        help_text=_("Designates whether two-factor authentication is active."),
    )
    extra_settings = models.JSONField(
        default=dict,
        blank=True,
        help_text=_("Extensible key-value preference configurations."),
    )

    class Meta:
        verbose_name = _("user preference")
        verbose_name_plural = _("user preferences")

    def __str__(self) -> str:
        return f"Preferences for {self.user.email}"


class Device(BaseModel):
    """Tracked user device for multi-device authorization and session security."""

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="devices",
        help_text=_("User owner of this device."),
    )
    device_name = models.CharField(
        max_length=255,
        blank=True,
        default="",
        help_text=_("Human readable device description or hostname."),
    )
    device_type = models.CharField(
        max_length=50,
        choices=DeviceType.choices,
        default=DeviceType.UNKNOWN,
        db_index=True,
        help_text=_("Device hardware category."),
    )
    browser = models.CharField(
        max_length=100,
        blank=True,
        default="",
        help_text=_("Browser client name and version."),
    )
    os = models.CharField(
        max_length=100,
        blank=True,
        default="",
        help_text=_("Operating system name and version."),
    )
    platform = models.CharField(
        max_length=100,
        blank=True,
        default="",
        help_text=_("Platform hardware architecture."),
    )
    user_agent = models.TextField(
        blank=True,
        default="",
        help_text=_("Full HTTP user agent header string."),
    )
    ip_address = models.GenericIPAddressField(
        null=True,
        blank=True,
        help_text=_("Last recorded device IP address."),
    )
    fingerprint = models.CharField(
        max_length=255,
        blank=True,
        default="",
        db_index=True,
        help_text=_("Unique hardware/browser device fingerprint hash."),
    )
    is_trusted = models.BooleanField(
        default=False,
        db_index=True,
        help_text=_("Designates whether user explicitly marked device as trusted."),
    )
    last_active = models.DateTimeField(
        default=timezone.now,
        db_index=True,
        help_text=_("Timestamp of last activity recorded from device."),
    )

    class Meta:
        verbose_name = _("device")
        verbose_name_plural = _("devices")
        indexes = [
            models.Index(
                fields=["user", "fingerprint"], name="idx_device_user_fingerprint"
            ),
            models.Index(
                fields=["user", "last_active"], name="idx_device_user_lastactive"
            ),
        ]

    def __str__(self) -> str:
        name = self.device_name or self.browser or "Device"
        return f"{name} ({self.user.email})"


class UserSession(BaseModel):
    """Concurrent user JWT session record tracking access state, token hash, and expiry."""

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="sessions",
        help_text=_("User owner of this active session."),
    )
    jti = models.CharField(
        max_length=255,
        unique=True,
        db_index=True,
        help_text=_("Unique JWT ID identifier."),
    )
    refresh_token_hash = models.CharField(
        max_length=255,
        db_index=True,
        help_text=_("SHA-256 hash of refresh token value."),
    )
    access_token_expires_at = models.DateTimeField(
        help_text=_("Expiration timestamp of JWT access token."),
    )
    refresh_token_expires_at = models.DateTimeField(
        db_index=True,
        help_text=_("Expiration timestamp of JWT refresh token."),
    )
    device = models.ForeignKey(
        Device,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="sessions",
        help_text=_("Associated user device."),
    )
    location = models.CharField(
        max_length=255,
        blank=True,
        default="",
        help_text=_("Geographic location estimate derived from IP."),
    )
    browser = models.CharField(
        max_length=100,
        blank=True,
        default="",
        help_text=_("Client browser info."),
    )
    ip_address = models.GenericIPAddressField(
        null=True,
        blank=True,
        help_text=_("Client IP address."),
    )
    login_time = models.DateTimeField(
        default=timezone.now,
        help_text=_("Timestamp when session was initiated."),
    )
    last_activity = models.DateTimeField(
        default=timezone.now,
        db_index=True,
        help_text=_("Timestamp of last recorded session activity."),
    )
    logout_time = models.DateTimeField(
        null=True,
        blank=True,
        help_text=_("Timestamp when session was explicitly terminated."),
    )
    status = models.CharField(
        max_length=20,
        choices=SessionStatus.choices,
        default=SessionStatus.ACTIVE,
        db_index=True,
        help_text=_("Current lifecycle status of session."),
    )
    is_current = models.BooleanField(
        default=False,
        help_text=_("Flag indicating whether this represents current user session."),
    )

    class Meta:
        verbose_name = _("user session")
        verbose_name_plural = _("user sessions")
        indexes = [
            models.Index(fields=["user", "status"], name="idx_session_user_status"),
            models.Index(
                fields=["status", "refresh_token_expires_at"],
                name="idx_session_status_exp",
            ),
        ]

    def __str__(self) -> str:
        return f"Session {self.jti[:8]} ({self.user.email})"


class LoginHistory(BaseModel):
    """Audit log of authentication attempts, successes, failures, and security events."""

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.CASCADE,
        related_name="login_history",
        help_text=_("User associated with event, if authenticated."),
    )
    email_attempted = models.EmailField(
        max_length=255,
        blank=True,
        default="",
        db_index=True,
        help_text=_("Email address attempted during authentication event."),
    )
    event_type = models.CharField(
        max_length=50,
        choices=LoginEventType.choices,
        db_index=True,
        help_text=_("Category of authentication event."),
    )
    status = models.CharField(
        max_length=20,
        default="SUCCESS",
        db_index=True,
        help_text=_("Outcome status string."),
    )
    failure_reason = models.CharField(
        max_length=255,
        blank=True,
        default="",
        help_text=_("Description of failure reason if applicable."),
    )
    location = models.CharField(
        max_length=255,
        blank=True,
        default="",
        help_text=_("Geographic location estimate derived from IP."),
    )
    ip_address = models.GenericIPAddressField(
        null=True,
        blank=True,
        db_index=True,
        help_text=_("Client IP address."),
    )
    user_agent = models.TextField(
        blank=True,
        default="",
        help_text=_("Full HTTP User-Agent string."),
    )
    device = models.ForeignKey(
        Device,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="login_logs",
        help_text=_("Device record associated with event."),
    )
    timestamp = models.DateTimeField(
        default=timezone.now,
        db_index=True,
        help_text=_("Event timestamp."),
    )

    class Meta:
        verbose_name = _("login history")
        verbose_name_plural = _("login histories")
        indexes = [
            models.Index(
                fields=["user", "event_type", "timestamp"],
                name="idx_loginhist_user_evt_time",
            ),
            models.Index(
                fields=["email_attempted", "timestamp"],
                name="idx_loginhist_email_time",
            ),
        ]

    def __str__(self) -> str:
        target = self.user.email if self.user else self.email_attempted
        return f"{self.event_type} for {target} at {self.timestamp}"


class PasswordResetToken(BaseModel):
    """One-time hashed tokens for secure password recovery flows."""

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="password_reset_tokens",
        help_text=_("User requesting password reset."),
    )
    token_hash = models.CharField(
        max_length=255,
        unique=True,
        db_index=True,
        help_text=_("SHA-256 hash of single-use password reset token."),
    )
    expires_at = models.DateTimeField(
        db_index=True,
        help_text=_("Token expiration timestamp."),
    )
    is_used = models.BooleanField(
        default=False,
        db_index=True,
        help_text=_("Flag indicating whether token has already been consumed."),
    )
    used_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text=_("Timestamp when token was consumed."),
    )
    ip_address = models.GenericIPAddressField(
        null=True,
        blank=True,
        help_text=_("IP address from which token request originated."),
    )
    user_agent = models.TextField(
        blank=True,
        default="",
        help_text=_("User Agent requesting password reset."),
    )

    class Meta:
        verbose_name = _("password reset token")
        verbose_name_plural = _("password reset tokens")
        indexes = [
            models.Index(
                fields=["user", "is_used", "expires_at"],
                name="idx_pwdtoken_user_used_exp",
            ),
        ]

    def __str__(self) -> str:
        return f"PasswordResetToken for {self.user.email}"


class EmailVerificationToken(BaseModel):
    """One-time hashed tokens for email verification flows."""

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="email_verification_tokens",
        help_text=_("User verifying primary email address."),
    )
    token_hash = models.CharField(
        max_length=255,
        unique=True,
        db_index=True,
        help_text=_("SHA-256 hash of single-use email verification token."),
    )
    expires_at = models.DateTimeField(
        db_index=True,
        help_text=_("Token expiration timestamp."),
    )
    is_used = models.BooleanField(
        default=False,
        db_index=True,
        help_text=_("Flag indicating whether token has already been consumed."),
    )
    used_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text=_("Timestamp when token was consumed."),
    )
    ip_address = models.GenericIPAddressField(
        null=True,
        blank=True,
        help_text=_("IP address from which verification request originated."),
    )
    user_agent = models.TextField(
        blank=True,
        default="",
        help_text=_("User Agent verifying email."),
    )

    class Meta:
        verbose_name = _("email verification token")
        verbose_name_plural = _("email verification tokens")
        indexes = [
            models.Index(
                fields=["user", "is_used", "expires_at"],
                name="idx_emailtoken_user_used_exp",
            ),
        ]

    def __str__(self) -> str:
        return f"EmailVerificationToken for {self.user.email}"
