"""Domain models for the organizations app extending BaseModel."""

import secrets
import string
import uuid
from django.db import models
from django.utils.translation import gettext_lazy as _

from apps.common.models import BaseModel


class OrganizationStatus(models.TextChoices):
    DRAFT = "DRAFT", _("Draft")
    PENDING_VERIFICATION = "PENDING_VERIFICATION", _("Pending Verification")
    ACTIVE = "ACTIVE", _("Active")
    SUSPENDED = "SUSPENDED", _("Suspended")
    INACTIVE = "INACTIVE", _("Inactive")
    ARCHIVED = "ARCHIVED", _("Archived")


class OrganizationType(models.TextChoices):
    ENTERPRISE = "ENTERPRISE", _("Enterprise")
    COMPANY = "COMPANY", _("Company")
    SUBSIDIARY = "SUBSIDIARY", _("Subsidiary")
    NON_PROFIT = "NON_PROFIT", _("Non Profit")
    PARTNERSHIP = "PARTNERSHIP", _("Partnership")
    SOLE_PROPRIETORSHIP = "SOLE_PROPRIETORSHIP", _("Sole Proprietorship")


class ShiftType(models.TextChoices):
    REGULAR = "REGULAR", _("Regular")
    FLEXIBLE = "FLEXIBLE", _("Flexible")
    NIGHT = "NIGHT", _("Night")
    ROTATIONAL = "ROTATIONAL", _("Rotational")


class HolidayType(models.TextChoices):
    PUBLIC = "PUBLIC", _("Public Holiday")
    NATIONAL = "NATIONAL", _("National Holiday")
    REGIONAL = "REGIONAL", _("Regional Holiday")
    COMPANY = "COMPANY", _("Company Holiday")
    OPTIONAL = "OPTIONAL", _("Optional Holiday")


def _generate_org_code() -> str:
    """Generate a unique 8-character uppercase alphanumeric organization code."""
    chars = string.ascii_uppercase + string.digits
    return "ORG-" + "".join(secrets.choice(chars) for _ in range(6))


class Organization(BaseModel):
    """Root enterprise organization tenant model."""

    name = models.CharField(
        max_length=255,
        help_text=_("Display name of the organization."),
    )
    legal_name = models.CharField(
        max_length=255,
        blank=True,
        help_text=_("Registered legal name of the organization."),
    )
    code = models.CharField(
        max_length=32,
        unique=True,
        db_index=True,
        default=_generate_org_code,
        editable=False,
        help_text=_("Immutable auto-generated unique organization code."),
    )
    registration_number = models.CharField(
        max_length=100,
        blank=True,
        help_text=_("Official business registration number."),
    )
    tax_number = models.CharField(
        max_length=100,
        blank=True,
        help_text=_("Tax Identification Number (TIN)."),
    )
    gst_number = models.CharField(
        max_length=100,
        blank=True,
        help_text=_("Goods and Services Tax (GST) number."),
    )
    email = models.EmailField(
        max_length=255,
        blank=True,
        help_text=_("Primary contact email address."),
    )
    phone = models.CharField(
        max_length=50,
        blank=True,
        help_text=_("Primary contact phone number."),
    )
    website = models.URLField(
        max_length=255,
        blank=True,
        help_text=_("Official website URL."),
    )
    logo = models.URLField(
        max_length=500,
        blank=True,
        help_text=_("URL or path to organization logo."),
    )
    industry = models.CharField(
        max_length=100,
        blank=True,
        help_text=_("Primary industry sector."),
    )
    organization_type = models.CharField(
        max_length=30,
        choices=OrganizationType.choices,
        default=OrganizationType.COMPANY,
        help_text=_("Legal entity structure."),
    )
    currency = models.CharField(
        max_length=10,
        default="USD",
        help_text=_("Default currency code (ISO 4217)."),
    )
    language = models.CharField(
        max_length=10,
        default="en",
        help_text=_("Default language locale code."),
    )
    timezone = models.CharField(
        max_length=100,
        default="UTC",
        help_text=_("Primary operating timezone."),
    )
    date_format = models.CharField(
        max_length=30,
        default="YYYY-MM-DD",
        help_text=_("Preferred date format string."),
    )
    time_format = models.CharField(
        max_length=30,
        default="24H",
        help_text=_("Preferred time format (12H or 24H)."),
    )
    fiscal_year_start = models.CharField(
        max_length=10,
        default="01-01",
        help_text=_("Fiscal year start date (MM-DD)."),
    )
    country = models.CharField(
        max_length=100,
        blank=True,
        help_text=_("Country of registration."),
    )
    state = models.CharField(
        max_length=100,
        blank=True,
        help_text=_("State or region."),
    )
    city = models.CharField(
        max_length=100,
        blank=True,
        help_text=_("City location."),
    )
    address = models.TextField(
        blank=True,
        help_text=_("Full street address."),
    )
    postal_code = models.CharField(
        max_length=20,
        blank=True,
        help_text=_("Postal or ZIP code."),
    )
    status = models.CharField(
        max_length=20,
        choices=OrganizationStatus.choices,
        default=OrganizationStatus.ACTIVE,
        db_index=True,
        help_text=_("Organization operational status."),
    )

    class Meta:
        verbose_name = _("organization")
        verbose_name_plural = _("organizations")
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["code", "status"], name="idx_org_code_status"),
            models.Index(fields=["status", "deleted_at"], name="idx_org_status_deleted"),
        ]

    def __str__(self):
        return f"{self.name} ({self.code})"


class Branch(BaseModel):
    """Single-level operational branch or facility under an Organization."""

    organization = models.ForeignKey(
        Organization,
        on_delete=models.PROTECT,
        related_name="branches",
        help_text=_("Parent organization."),
    )
    code = models.CharField(
        max_length=50,
        help_text=_("Branch code (unique per organization)."),
    )
    name = models.CharField(
        max_length=255,
        help_text=_("Branch display name."),
    )
    email = models.EmailField(
        max_length=255,
        blank=True,
        help_text=_("Branch contact email."),
    )
    phone = models.CharField(
        max_length=50,
        blank=True,
        help_text=_("Branch contact phone."),
    )
    address = models.TextField(
        blank=True,
        help_text=_("Physical address of the branch."),
    )
    city = models.CharField(
        max_length=100,
        blank=True,
        help_text=_("City."),
    )
    state = models.CharField(
        max_length=100,
        blank=True,
        help_text=_("State or province."),
    )
    country = models.CharField(
        max_length=100,
        blank=True,
        help_text=_("Country."),
    )
    postal_code = models.CharField(
        max_length=20,
        blank=True,
        help_text=_("Postal code."),
    )
    latitude = models.DecimalField(
        max_digits=10,
        decimal_places=7,
        null=True,
        blank=True,
        help_text=_("Geographic latitude coordinate."),
    )
    longitude = models.DecimalField(
        max_digits=10,
        decimal_places=7,
        null=True,
        blank=True,
        help_text=_("Geographic longitude coordinate."),
    )
    timezone = models.CharField(
        max_length=100,
        default="UTC",
        help_text=_("Local operating timezone."),
    )
    is_headquarters = models.BooleanField(
        default=False,
        help_text=_("Designates whether this branch is corporate HQ."),
    )
    status = models.CharField(
        max_length=20,
        choices=OrganizationStatus.choices,
        default=OrganizationStatus.ACTIVE,
        db_index=True,
        help_text=_("Branch operational status."),
    )

    class Meta:
        verbose_name = _("branch")
        verbose_name_plural = _("branches")
        ordering = ["name"]
        constraints = [
            models.UniqueConstraint(
                fields=["organization", "code"],
                name="unique_branch_code_per_org",
            )
        ]
        indexes = [
            models.Index(fields=["organization", "status"], name="idx_branch_org_status"),
        ]

    def __str__(self):
        return f"{self.name} ({self.code})"


class Department(BaseModel):
    """Department unit belonging to a Branch and Organization."""

    organization = models.ForeignKey(
        Organization,
        on_delete=models.PROTECT,
        related_name="departments",
        help_text=_("Parent organization."),
    )
    branch = models.ForeignKey(
        Branch,
        on_delete=models.PROTECT,
        related_name="departments",
        help_text=_("Parent branch location."),
    )
    parent_department = models.ForeignKey(
        "self",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="sub_departments",
        help_text=_("Optional parent department for hierarchical structures."),
    )
    name = models.CharField(
        max_length=255,
        help_text=_("Department name."),
    )
    code = models.CharField(
        max_length=50,
        help_text=_("Department code (unique per organization)."),
    )
    description = models.TextField(
        blank=True,
        help_text=_("Detailed department scope description."),
    )
    ordering = models.PositiveIntegerField(
        default=0,
        help_text=_("Display order rank."),
    )
    status = models.CharField(
        max_length=20,
        choices=OrganizationStatus.choices,
        default=OrganizationStatus.ACTIVE,
        db_index=True,
        help_text=_("Department operational status."),
    )

    class Meta:
        verbose_name = _("department")
        verbose_name_plural = _("departments")
        ordering = ["ordering", "name"]
        constraints = [
            models.UniqueConstraint(
                fields=["organization", "code"],
                name="unique_dept_code_per_org",
            )
        ]
        indexes = [
            models.Index(fields=["organization", "branch"], name="idx_dept_org_branch"),
        ]

    def __str__(self):
        return f"{self.name} - {self.branch.name}"


class Designation(BaseModel):
    """Job designation, level, and grade classification."""

    organization = models.ForeignKey(
        Organization,
        on_delete=models.PROTECT,
        related_name="designations",
        help_text=_("Parent organization."),
    )
    department = models.ForeignKey(
        Department,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="designations",
        help_text=_("Optional primary department association."),
    )
    name = models.CharField(
        max_length=255,
        help_text=_("Designation title."),
    )
    code = models.CharField(
        max_length=50,
        help_text=_("Designation code (unique per organization)."),
    )
    grade = models.CharField(
        max_length=50,
        blank=True,
        help_text=_("Salary or organizational grade."),
    )
    level = models.PositiveIntegerField(
        default=1,
        help_text=_("Numeric hierarchy level rank (e.g. 1 = Entry, 5 = Executive)."),
    )
    description = models.TextField(
        blank=True,
        help_text=_("Job role responsibility description."),
    )
    status = models.CharField(
        max_length=20,
        choices=OrganizationStatus.choices,
        default=OrganizationStatus.ACTIVE,
        db_index=True,
        help_text=_("Designation status."),
    )

    class Meta:
        verbose_name = _("designation")
        verbose_name_plural = _("designations")
        ordering = ["level", "name"]
        constraints = [
            models.UniqueConstraint(
                fields=["organization", "code"],
                name="unique_designation_code_per_org",
            )
        ]

    def __str__(self):
        return f"{self.name} ({self.code})"


class Team(BaseModel):
    """Operational team unit belonging to a Department, Branch, and Organization."""

    organization = models.ForeignKey(
        Organization,
        on_delete=models.PROTECT,
        related_name="teams",
        help_text=_("Parent organization."),
    )
    branch = models.ForeignKey(
        Branch,
        on_delete=models.PROTECT,
        related_name="teams",
        help_text=_("Parent branch."),
    )
    department = models.ForeignKey(
        Department,
        on_delete=models.PROTECT,
        related_name="teams",
        help_text=_("Parent department."),
    )
    name = models.CharField(
        max_length=255,
        help_text=_("Team display name."),
    )
    code = models.CharField(
        max_length=50,
        help_text=_("Team code (unique per organization)."),
    )
    description = models.TextField(
        blank=True,
        help_text=_("Team responsibilities description."),
    )
    status = models.CharField(
        max_length=20,
        choices=OrganizationStatus.choices,
        default=OrganizationStatus.ACTIVE,
        db_index=True,
        help_text=_("Team status."),
    )

    class Meta:
        verbose_name = _("team")
        verbose_name_plural = _("teams")
        ordering = ["name"]
        constraints = [
            models.UniqueConstraint(
                fields=["organization", "code"],
                name="unique_team_code_per_org",
            )
        ]

    def __str__(self):
        return f"{self.name} ({self.code})"


class Shift(BaseModel):
    """Reusable shift template for working hours and grace time rules."""

    organization = models.ForeignKey(
        Organization,
        on_delete=models.PROTECT,
        related_name="shifts",
        help_text=_("Parent organization."),
    )
    name = models.CharField(
        max_length=255,
        help_text=_("Shift template name."),
    )
    code = models.CharField(
        max_length=50,
        help_text=_("Shift code (unique per organization)."),
    )
    shift_type = models.CharField(
        max_length=20,
        choices=ShiftType.choices,
        default=ShiftType.REGULAR,
        help_text=_("Shift operational mode."),
    )
    start_time = models.TimeField(
        help_text=_("Shift start time (e.g. 09:00:00)."),
    )
    end_time = models.TimeField(
        help_text=_("Shift end time (e.g. 17:00:00)."),
    )
    grace_time_minutes = models.PositiveIntegerField(
        default=15,
        help_text=_("Allowed grace arrival threshold in minutes."),
    )
    flexible_hours = models.BooleanField(
        default=False,
        help_text=_("Designates if flexible check-in is enabled."),
    )
    is_night_shift = models.BooleanField(
        default=False,
        help_text=_("Designates shifts crossing midnight."),
    )
    break_duration_minutes = models.PositiveIntegerField(
        default=60,
        help_text=_("Unpaid break duration in minutes."),
    )
    working_hours = models.DecimalField(
        max_digits=4,
        decimal_places=2,
        default=8.00,
        help_text=_("Expected daily net working hours."),
    )
    status = models.CharField(
        max_length=20,
        choices=OrganizationStatus.choices,
        default=OrganizationStatus.ACTIVE,
        db_index=True,
        help_text=_("Shift template status."),
    )

    class Meta:
        verbose_name = _("shift")
        verbose_name_plural = _("shifts")
        ordering = ["name"]
        constraints = [
            models.UniqueConstraint(
                fields=["organization", "code"],
                name="unique_shift_code_per_org",
            )
        ]

    def __str__(self):
        return f"{self.name} ({self.start_time.strftime('%H:%M')} - {self.end_time.strftime('%H:%M')})"


class HolidayCalendar(BaseModel):
    """Holiday schedule supporting organization-wide (branch=null) or branch-specific scopes."""

    organization = models.ForeignKey(
        Organization,
        on_delete=models.PROTECT,
        related_name="holidays",
        help_text=_("Parent organization."),
    )
    branch = models.ForeignKey(
        Branch,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="holidays",
        help_text=_("Optional specific branch scope (null indicates organization-wide)."),
    )
    name = models.CharField(
        max_length=255,
        help_text=_("Holiday title."),
    )
    holiday_date = models.DateField(
        db_index=True,
        help_text=_("Specific calendar date of the holiday."),
    )
    holiday_type = models.CharField(
        max_length=20,
        choices=HolidayType.choices,
        default=HolidayType.PUBLIC,
        help_text=_("Classification category of the holiday."),
    )
    description = models.TextField(
        blank=True,
        help_text=_("Holiday details or notes."),
    )
    is_recurring = models.BooleanField(
        default=False,
        help_text=_("Designates annual recurring holiday."),
    )
    status = models.CharField(
        max_length=20,
        choices=OrganizationStatus.choices,
        default=OrganizationStatus.ACTIVE,
        db_index=True,
        help_text=_("Holiday calendar status."),
    )

    class Meta:
        verbose_name = _("holiday calendar")
        verbose_name_plural = _("holiday calendars")
        ordering = ["holiday_date"]
        indexes = [
            models.Index(fields=["organization", "holiday_date"], name="idx_holiday_org_date"),
        ]

    def __str__(self):
        scope = self.branch.name if self.branch else "Organization-Wide"
        return f"{self.name} ({self.holiday_date}) - {scope}"


class OrganizationSetting(BaseModel):
    """Dedicated OneToOne configuration settings model per Organization."""

    organization = models.OneToOneField(
        Organization,
        on_delete=models.PROTECT,
        related_name="setting",
        help_text=_("Associated organization instance."),
    )
    attendance_mode = models.CharField(
        max_length=50,
        default="WEB_AND_MOBILE",
        help_text=_("Primary allowed attendance tracking mode."),
    )
    leave_approval_levels = models.PositiveIntegerField(
        default=1,
        help_text=_("Number of approval hierarchy levels required for leave requests."),
    )
    working_days_mask = models.CharField(
        max_length=20,
        default="MON,TUE,WED,THU,FRI",
        help_text=_("Comma-separated weekly working days mask."),
    )
    weekend_days_mask = models.CharField(
        max_length=20,
        default="SAT,SUN",
        help_text=_("Comma-separated weekly weekend days mask."),
    )
    default_shift = models.ForeignKey(
        Shift,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="default_settings",
        help_text=_("Default organizational fallback shift."),
    )
    default_language = models.CharField(
        max_length=10,
        default="en",
        help_text=_("Default language code."),
    )
    default_currency = models.CharField(
        max_length=10,
        default="USD",
        help_text=_("Default currency code."),
    )
    default_timezone = models.CharField(
        max_length=100,
        default="UTC",
        help_text=_("Default system timezone."),
    )
    notification_config = models.JSONField(
        default=dict,
        blank=True,
        help_text=_("JSON configuration payload for email/SMS notifications."),
    )
    security_config = models.JSONField(
        default=dict,
        blank=True,
        help_text=_("JSON configuration payload for IP whitelist & 2FA rules."),
    )

    class Meta:
        verbose_name = _("organization setting")
        verbose_name_plural = _("organization settings")

    def __str__(self):
        return f"Settings for {self.organization.name}"


class OrganizationLimit(BaseModel):
    """Quota thresholds and limits governing subscription plans per Organization."""

    organization = models.OneToOneField(
        Organization,
        on_delete=models.PROTECT,
        related_name="limit",
        help_text=_("Associated organization instance."),
    )
    max_branches = models.PositiveIntegerField(
        default=10,
        help_text=_("Maximum allowed active branch locations."),
    )
    max_departments = models.PositiveIntegerField(
        default=25,
        help_text=_("Maximum allowed department units."),
    )
    max_teams = models.PositiveIntegerField(
        default=50,
        help_text=_("Maximum allowed team units."),
    )
    max_shifts = models.PositiveIntegerField(
        default=20,
        help_text=_("Maximum allowed shift templates."),
    )
    max_employees = models.PositiveIntegerField(
        default=250,
        help_text=_("Maximum allowed active employees."),
    )
    max_storage_gb = models.PositiveIntegerField(
        default=100,
        help_text=_("Maximum allowed document storage in GB."),
    )
    max_api_calls_per_day = models.PositiveIntegerField(
        default=10000,
        help_text=_("Maximum allowed daily API request calls."),
    )
    max_projects = models.PositiveIntegerField(
        default=50,
        help_text=_("Maximum allowed active projects."),
    )

    class Meta:
        verbose_name = _("organization limit")
        verbose_name_plural = _("organization limits")

    def __str__(self):
        return f"Limits for {self.organization.name}"


class OrganizationFeatureFlag(BaseModel):
    """Organization-level feature toggles governing module access and capability flags."""

    organization = models.OneToOneField(
        Organization,
        on_delete=models.PROTECT,
        related_name="feature_flag",
        help_text=_("Associated organization instance."),
    )
    attendance_enabled = models.BooleanField(
        default=True,
        help_text=_("Toggles Attendance tracking module."),
    )
    payroll_enabled = models.BooleanField(
        default=True,
        help_text=_("Toggles Payroll and compensation module."),
    )
    crm_enabled = models.BooleanField(
        default=True,
        help_text=_("Toggles Customer Relationship Management module."),
    )
    projects_enabled = models.BooleanField(
        default=True,
        help_text=_("Toggles Projects and task tracking module."),
    )
    documents_enabled = models.BooleanField(
        default=True,
        help_text=_("Toggles Document Management module."),
    )
    ai_assistant_enabled = models.BooleanField(
        default=False,
        help_text=_("Toggles Nexora AI Assistant features."),
    )
    automation_enabled = models.BooleanField(
        default=True,
        help_text=_("Toggles Business Process Automation workflows."),
    )
    api_access_enabled = models.BooleanField(
        default=True,
        help_text=_("Toggles REST API external integration access."),
    )

    class Meta:
        verbose_name = _("organization feature flag")
        verbose_name_plural = _("organization feature flags")

    def __str__(self):
        return f"Feature Flags for {self.organization.name}"


class OrganizationAuditEvent(BaseModel):
    """Detailed audit log trail for Organization Engine lifecycle mutations and rule checks."""

    organization = models.ForeignKey(
        Organization,
        on_delete=models.PROTECT,
        related_name="audit_events",
        help_text=_("Associated organization instance."),
    )
    event_type = models.CharField(
        max_length=100,
        db_index=True,
        help_text=_("Category identifier of the audit event."),
    )
    user_id = models.CharField(
        max_length=100,
        blank=True,
        help_text=_("UUID of the initiating user."),
    )
    user_email = models.CharField(
        max_length=255,
        blank=True,
        help_text=_("Email address of the initiating user."),
    )
    ip_address = models.GenericIPAddressField(
        null=True,
        blank=True,
        help_text=_("Client IP address."),
    )
    request_id = models.CharField(
        max_length=100,
        blank=True,
        help_text=_("Correlation request ID."),
    )
    previous_state = models.JSONField(
        default=dict,
        blank=True,
        help_text=_("Previous state values snapshot."),
    )
    new_state = models.JSONField(
        default=dict,
        blank=True,
        help_text=_("New state values snapshot."),
    )
    metadata = models.JSONField(
        default=dict,
        blank=True,
        help_text=_("Additional context metadata."),
    )
    timestamp = models.DateTimeField(
        auto_now_add=True,
        db_index=True,
        help_text=_("Event creation timestamp."),
    )

    class Meta:
        verbose_name = _("organization audit event")
        verbose_name_plural = _("organization audit events")
        ordering = ["-timestamp"]
        indexes = [
            models.Index(fields=["organization", "event_type"], name="idx_orgaudit_org_event"),
            models.Index(fields=["organization", "timestamp"], name="idx_orgaudit_org_time"),
        ]

    def __str__(self):
        return f"[{self.event_type}] {self.organization.name} at {self.timestamp}"


class RosterStatus(models.TextChoices):
    DRAFT = "DRAFT", _("Draft Roster")
    PUBLISHED = "PUBLISHED", _("Published Roster")
    ARCHIVED = "ARCHIVED", _("Archived Roster")


class RosterPeriodType(models.TextChoices):
    DAILY = "DAILY", _("Daily Planning")
    WEEKLY = "WEEKLY", _("Weekly Planning")
    BIWEEKLY = "BIWEEKLY", _("Biweekly Planning")
    MONTHLY = "MONTHLY", _("Monthly Planning")


class RotationType(models.TextChoices):
    WEEKLY = "WEEKLY", _("Weekly Shift Rotation")
    BIWEEKLY = "BIWEEKLY", _("Biweekly Shift Rotation")
    MONTHLY = "MONTHLY", _("Monthly Shift Rotation")
    CUSTOM = "CUSTOM", _("Custom Pattern Rotation")


class SwapStatus(models.TextChoices):
    PENDING = "PENDING", _("Pending Approval")
    APPROVED = "APPROVED", _("Approved by Manager / System")
    REJECTED = "REJECTED", _("Rejected")


class ShiftRoster(BaseModel):
    """Container for versioned shift scheduling plans across daily, weekly, or monthly periods."""

    organization = models.ForeignKey(
        Organization,
        on_delete=models.CASCADE,
        related_name="shift_rosters",
        help_text=_("Associated Organization instance."),
    )
    name = models.CharField(
        max_length=255,
        help_text=_("Roster display name (e.g., Q3 Engineering Shift Schedule)."),
    )
    code = models.CharField(
        max_length=50,
        db_index=True,
        help_text=_("Unique roster identifier code within organization."),
    )
    period_type = models.CharField(
        max_length=50,
        choices=RosterPeriodType.choices,
        default=RosterPeriodType.WEEKLY,
        help_text=_("Roster planning window period."),
    )
    start_date = models.DateField(
        db_index=True,
        help_text=_("Roster effective start date."),
    )
    end_date = models.DateField(
        db_index=True,
        help_text=_("Roster effective end date."),
    )
    status = models.CharField(
        max_length=50,
        choices=RosterStatus.choices,
        default=RosterStatus.DRAFT,
        db_index=True,
        help_text=_("Roster lifecycle publication state."),
    )
    version = models.PositiveIntegerField(
        default=1,
        help_text=_("Roster revision version counter."),
    )

    class Meta:
        verbose_name = _("shift roster")
        verbose_name_plural = _("shift rosters")
        ordering = ["-start_date", "name"]
        constraints = [
            models.UniqueConstraint(
                fields=["organization", "code"],
                name="unique_shiftroster_org_code",
            )
        ]
        indexes = [
            models.Index(fields=["organization", "status", "start_date"], name="idx_sroster_org_status"),
        ]

    def __str__(self):
        return f"{self.name} ({self.code}) [{self.status}]"


class ShiftRosterAssignment(BaseModel):
    """Specific employee assignment to a shift for a single calendar date within a published roster."""

    roster = models.ForeignKey(
        ShiftRoster,
        on_delete=models.CASCADE,
        related_name="assignments",
        help_text=_("Parent ShiftRoster instance."),
    )
    employee = models.ForeignKey(
        "employees.Employee",
        on_delete=models.CASCADE,
        related_name="roster_assignments",
        help_text=_("Assigned Employee instance."),
    )
    shift = models.ForeignKey(
        Shift,
        on_delete=models.PROTECT,
        related_name="roster_assignments",
        help_text=_("Assigned Shift template."),
    )
    date = models.DateField(
        db_index=True,
        help_text=_("Calendar date of shift assignment."),
    )
    is_override = models.BooleanField(
        default=False,
        help_text=_("Flag indicating manual override of default/rotation shift."),
    )
    override_reason = models.TextField(
        blank=True,
        help_text=_("Rationale notes if assignment is an override."),
    )

    class Meta:
        verbose_name = _("shift roster assignment")
        verbose_name_plural = _("shift roster assignments")
        ordering = ["date", "employee"]
        constraints = [
            models.UniqueConstraint(
                fields=["roster", "employee", "date"],
                name="unique_srosterassign_emp_date",
            )
        ]
        indexes = [
            models.Index(fields=["employee", "date"], name="idx_srosterassign_emp_date"),
        ]

    def __str__(self):
        return f"{self.employee.employee_id} -> {self.shift.code} on {self.date}"


class ShiftRotation(BaseModel):
    """Pattern template definition for automated multi-week shift rotations."""

    organization = models.ForeignKey(
        Organization,
        on_delete=models.CASCADE,
        related_name="shift_rotations",
        help_text=_("Associated Organization instance."),
    )
    name = models.CharField(
        max_length=255,
        help_text=_("Rotation pattern name (e.g., 3-Shift Weekly Rotation)."),
    )
    code = models.CharField(
        max_length=50,
        db_index=True,
        help_text=_("Unique rotation code within organization."),
    )
    rotation_type = models.CharField(
        max_length=50,
        choices=RotationType.choices,
        default=RotationType.WEEKLY,
        help_text=_("Rotation cycle frequency."),
    )
    pattern_json = models.JSONField(
        default=list,
        help_text=_("JSON sequence array of shift IDs or codes defining the rotation cycle."),
    )
    cycle_days = models.PositiveIntegerField(
        default=7,
        help_text=_("Total duration of one full rotation cycle in days."),
    )

    class Meta:
        verbose_name = _("shift rotation")
        verbose_name_plural = _("shift rotations")
        ordering = ["name"]
        constraints = [
            models.UniqueConstraint(
                fields=["organization", "code"],
                name="unique_shiftrotation_org_code",
            )
        ]

    def __str__(self):
        return f"{self.name} ({self.code})"


class ShiftSwapRequest(BaseModel):
    """Peer-to-peer shift swap request foundation between two employees."""

    requester = models.ForeignKey(
        "employees.Employee",
        on_delete=models.CASCADE,
        related_name="initiated_shift_swaps",
        help_text=_("Employee requesting the shift swap."),
    )
    target_employee = models.ForeignKey(
        "employees.Employee",
        on_delete=models.CASCADE,
        related_name="received_shift_swaps",
        help_text=_("Target employee to swap shift with."),
    )
    requester_date = models.DateField(
        help_text=_("Original date of requester's shift to swap."),
    )
    target_date = models.DateField(
        help_text=_("Target date of peer's shift to swap."),
    )
    status = models.CharField(
        max_length=50,
        choices=SwapStatus.choices,
        default=SwapStatus.PENDING,
        db_index=True,
        help_text=_("Approval workflow status of swap request."),
    )
    reason = models.TextField(
        blank=True,
        help_text=_("Rationale notes for shift swap."),
    )

    class Meta:
        verbose_name = _("shift swap request")
        verbose_name_plural = _("shift swap requests")
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["requester", "status"], name="idx_sswap_requester_status"),
        ]

    def __str__(self):
        return f"Swap: {self.requester.employee_id} <-> {self.target_employee.employee_id} ({self.status})"


