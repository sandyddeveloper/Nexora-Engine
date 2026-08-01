"""Production-grade Django models for the Attendance Foundation Engine."""

from decimal import Decimal
from django.db import models
from django.utils.translation import gettext_lazy as _

from apps.common.models import BaseModel
from apps.employees.models import Employee
from apps.organizations.models import Branch, Department, Designation, Organization, Shift, Team

from .constants import (
    DEFAULT_ATTENDANCE_LOCK_DAYS,
    DEFAULT_EARLY_EXIT_THRESHOLD_MINUTES,
    DEFAULT_FULL_DAY_WORKING_HOURS,
    DEFAULT_GRACE_TIME_MINUTES,
    DEFAULT_LATE_THRESHOLD_MINUTES,
    DEFAULT_MAXIMUM_WORKING_HOURS,
    DEFAULT_MINIMUM_WORKING_HOURS,
)


class AttendanceStatus(models.TextChoices):
    PRESENT = "PRESENT", _("Present")
    ABSENT = "ABSENT", _("Absent")
    HALF_DAY = "HALF_DAY", _("Half Day")
    LATE = "LATE", _("Late Arrival")
    EARLY_EXIT = "EARLY_EXIT", _("Early Departure")
    WORK_FROM_HOME = "WORK_FROM_HOME", _("Work From Home (WFH)")
    REMOTE = "REMOTE", _("Remote Work Location")
    BUSINESS_TRAVEL = "BUSINESS_TRAVEL", _("Official Business Travel")
    ON_DUTY = "ON_DUTY", _("On Official Duty")
    HOLIDAY = "HOLIDAY", _("Public / Company Holiday")
    WEEKLY_OFF = "WEEKLY_OFF", _("Scheduled Weekly Off")
    LEAVE = "LEAVE", _("Approved Leave")
    SUSPENDED = "SUSPENDED", _("Employee Suspended")
    TRAINING = "TRAINING", _("Attending Training")
    MEETING = "MEETING", _("External Client Meeting")


class AttendanceSource(models.TextChoices):
    WEB = "WEB", _("Web Portal Interface")
    MOBILE = "MOBILE", _("Mobile Application")
    BIOMETRIC = "BIOMETRIC", _("Biometric Terminal")
    API = "API", _("REST API Service")
    IMPORT = "IMPORT", _("Bulk File Import")
    ADMIN_ENTRY = "ADMIN_ENTRY", _("Manual Administrative Entry")
    QR_CODE = "QR_CODE", _("QR Code Scanner")
    KIOSK = "KIOSK", _("Attendance Kiosk Device")


class ApprovalStatus(models.TextChoices):
    DRAFT = "DRAFT", _("Draft Entry")
    PENDING = "PENDING", _("Pending Manager Review")
    APPROVED = "APPROVED", _("Approved by Manager / HR")
    REJECTED = "REJECTED", _("Rejected")


class AttendancePolicy(BaseModel):
    """Organization-level policy rules governing grace periods, hours, overtime, and checkout behavior."""

    organization = models.ForeignKey(
        Organization,
        on_delete=models.CASCADE,
        related_name="attendance_policies",
        help_text=_("Associated Organization instance."),
    )
    name = models.CharField(
        max_length=255,
        help_text=_("Policy display name (e.g., Standard 9-to-5 Policy)."),
    )
    code = models.CharField(
        max_length=50,
        db_index=True,
        help_text=_("Unique policy code within organization."),
    )
    grace_time_minutes = models.PositiveIntegerField(
        default=DEFAULT_GRACE_TIME_MINUTES,
        help_text=_("Grace period in minutes before marking late arrival."),
    )
    late_threshold_minutes = models.PositiveIntegerField(
        default=DEFAULT_LATE_THRESHOLD_MINUTES,
        help_text=_("Threshold in minutes to trigger late status deduction."),
    )
    early_exit_threshold_minutes = models.PositiveIntegerField(
        default=DEFAULT_EARLY_EXIT_THRESHOLD_MINUTES,
        help_text=_("Threshold in minutes to trigger early exit status."),
    )
    minimum_working_hours = models.DecimalField(
        max_digits=4,
        decimal_places=2,
        default=Decimal(str(DEFAULT_MINIMUM_WORKING_HOURS)),
        help_text=_("Minimum working hours required for half-day credit."),
    )
    full_day_working_hours = models.DecimalField(
        max_digits=4,
        decimal_places=2,
        default=Decimal(str(DEFAULT_FULL_DAY_WORKING_HOURS)),
        help_text=_("Minimum working hours required for full-day credit."),
    )
    maximum_working_hours = models.DecimalField(
        max_digits=4,
        decimal_places=2,
        default=Decimal(str(DEFAULT_MAXIMUM_WORKING_HOURS)),
        help_text=_("Maximum allowable working hours per day."),
    )
    overtime_allowed = models.BooleanField(
        default=True,
        help_text=_("Flag indicating whether overtime calculation is enabled."),
    )
    half_day_allowed = models.BooleanField(
        default=True,
        help_text=_("Flag indicating whether half-day attendance is permitted."),
    )
    auto_checkout_enabled = models.BooleanField(
        default=False,
        help_text=_("Flag enabling automated checkout at designated time."),
    )
    auto_checkout_time = models.TimeField(
        null=True,
        blank=True,
        help_text=_("Time of day to execute automated system checkout."),
    )
    approval_required = models.BooleanField(
        default=True,
        help_text=_("Flag indicating whether attendance adjustments require approval."),
    )
    is_default = models.BooleanField(
        default=False,
        db_index=True,
        help_text=_("Flag indicating default policy for organization."),
    )

    class Meta:
        verbose_name = _("attendance policy")
        verbose_name_plural = _("attendance policies")
        ordering = ["name"]
        constraints = [
            models.UniqueConstraint(
                fields=["organization", "code"],
                name="unique_attpolicy_org_code",
            )
        ]
        indexes = [
            models.Index(fields=["organization", "is_default"], name="idx_attpolicy_org_default"),
        ]

    def __str__(self):
        return f"{self.name} ({self.code})"


class AttendanceConfiguration(BaseModel):
    """Hierarchical configuration resolution (Organization -> Branch -> Department -> Team)."""

    organization = models.ForeignKey(
        Organization,
        on_delete=models.CASCADE,
        related_name="attendance_configurations",
        help_text=_("Target Organization."),
    )
    branch = models.ForeignKey(
        Branch,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="attendance_configurations",
        help_text=_("Target Branch (null for organization wide)."),
    )
    department = models.ForeignKey(
        Department,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="attendance_configurations",
        help_text=_("Target Department (null for branch wide)."),
    )
    team = models.ForeignKey(
        Team,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="attendance_configurations",
        help_text=_("Target Team (null for department wide)."),
    )
    default_policy = models.ForeignKey(
        AttendancePolicy,
        on_delete=models.PROTECT,
        related_name="configurations",
        help_text=_("Default Attendance Policy applied at this hierarchy level."),
    )
    allow_future_attendance = models.BooleanField(
        default=False,
        help_text=_("Allow logging attendance for future dates."),
    )
    allow_manual_entry = models.BooleanField(
        default=True,
        help_text=_("Allow manual attendance entry by managers."),
    )
    allow_wfh_request = models.BooleanField(
        default=True,
        help_text=_("Allow work-from-home requests."),
    )
    lock_attendance_days = models.PositiveIntegerField(
        default=DEFAULT_ATTENDANCE_LOCK_DAYS,
        help_text=_("Number of days after which past attendance records are locked."),
    )

    class Meta:
        verbose_name = _("attendance configuration")
        verbose_name_plural = _("attendance configurations")
        constraints = [
            models.UniqueConstraint(
                fields=["organization", "branch", "department", "team"],
                name="unique_attconfig_hierarchy",
            )
        ]

    def __str__(self):
        return f"AttendanceConfig: {self.organization.name} (Policy: {self.default_policy.name})"


class AttendanceRecord(BaseModel):
    """Core enterprise daily attendance record for an employee."""

    employee = models.ForeignKey(
        Employee,
        on_delete=models.CASCADE,
        related_name="attendance_records",
        help_text=_("Employee instance."),
    )
    organization = models.ForeignKey(
        Organization,
        on_delete=models.CASCADE,
        related_name="attendance_records",
        help_text=_("Organization instance."),
    )
    branch = models.ForeignKey(
        Branch,
        on_delete=models.PROTECT,
        related_name="attendance_records",
        help_text=_("Branch instance at time of attendance."),
    )
    department = models.ForeignKey(
        Department,
        on_delete=models.PROTECT,
        related_name="attendance_records",
        help_text=_("Department instance at time of attendance."),
    )
    designation = models.ForeignKey(
        Designation,
        on_delete=models.PROTECT,
        related_name="attendance_records",
        help_text=_("Designation instance at time of attendance."),
    )
    team = models.ForeignKey(
        Team,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="attendance_records",
        help_text=_("Team unit instance."),
    )
    shift = models.ForeignKey(
        Shift,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="attendance_records",
        help_text=_("Assigned Shift template."),
    )
    policy = models.ForeignKey(
        AttendancePolicy,
        on_delete=models.PROTECT,
        related_name="records",
        help_text=_("Governing Attendance Policy applied."),
    )
    attendance_date = models.DateField(
        db_index=True,
        help_text=_("Target calendar date of attendance."),
    )
    status = models.CharField(
        max_length=50,
        choices=AttendanceStatus.choices,
        default=AttendanceStatus.PRESENT,
        db_index=True,
        help_text=_("Primary attendance status classification."),
    )
    source = models.CharField(
        max_length=50,
        choices=AttendanceSource.choices,
        default=AttendanceSource.WEB,
        help_text=_("Origin source device/method of attendance."),
    )
    work_location = models.CharField(
        max_length=255,
        blank=True,
        help_text=_("Work location description at time of attendance."),
    )
    approval_status = models.CharField(
        max_length=50,
        choices=ApprovalStatus.choices,
        default=ApprovalStatus.APPROVED,
        db_index=True,
        help_text=_("Manager/HR approval workflow status."),
    )
    working_hours = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=Decimal("0.00"),
        help_text=_("Calculated actual net working hours."),
    )
    break_hours = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=Decimal("0.00"),
        help_text=_("Total break duration hours."),
    )
    overtime_hours = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=Decimal("0.00"),
        help_text=_("Calculated overtime hours."),
    )
    is_night_shift = models.BooleanField(
        default=False,
        help_text=_("Flag indicating attendance crosses midnight (night shift)."),
    )
    is_locked = models.BooleanField(
        default=False,
        db_index=True,
        help_text=_("Flag indicating attendance record is locked against modifications."),
    )
    remarks = models.TextField(
        blank=True,
        help_text=_("Notes or exception remarks."),
    )

    class Meta:
        verbose_name = _("attendance record")
        verbose_name_plural = _("attendance records")
        ordering = ["-attendance_date", "employee"]
        constraints = [
            models.UniqueConstraint(
                fields=["employee", "attendance_date"],
                name="unique_attrecord_emp_date",
            )
        ]
        indexes = [
            models.Index(fields=["employee", "attendance_date"], name="idx_attrec_emp_date"),
            models.Index(fields=["organization", "attendance_date", "status"], name="idx_attrec_org_date_status"),
        ]

    def __str__(self):
        return f"[{self.status}] {self.employee.employee_id} on {self.attendance_date}"


class AttendanceSession(BaseModel):
    """Check-in / Check-out sessions associated with an AttendanceRecord (supports multiple sessions per day)."""

    attendance_record = models.ForeignKey(
        AttendanceRecord,
        on_delete=models.CASCADE,
        related_name="sessions",
        help_text=_("Parent daily AttendanceRecord."),
    )
    check_in = models.DateTimeField(
        help_text=_("Check-in timestamp."),
    )
    check_out = models.DateTimeField(
        null=True,
        blank=True,
        help_text=_("Check-out timestamp."),
    )
    session_duration_minutes = models.PositiveIntegerField(
        default=0,
        help_text=_("Total session duration in minutes."),
    )
    is_auto_checked_out = models.BooleanField(
        default=False,
        help_text=_("Flag indicating system auto checkout."),
    )

    class Meta:
        verbose_name = _("attendance session")
        verbose_name_plural = _("attendance sessions")
        ordering = ["check_in"]

    def __str__(self):
        return f"Session {self.check_in} -> {self.check_out or 'ACTIVE'}"


class AttendanceEvent(BaseModel):
    """Immutable audit trail for attendance creation, updates, locks, and corrections."""

    attendance_record = models.ForeignKey(
        AttendanceRecord,
        on_delete=models.CASCADE,
        related_name="audit_events",
        help_text=_("Associated AttendanceRecord."),
    )
    event_type = models.CharField(
        max_length=50,
        db_index=True,
        help_text=_("Type of audit event (e.g., CREATED, LOCKED, CORRECTED)."),
    )
    actor_user_id = models.CharField(
        max_length=100,
        blank=True,
        help_text=_("User ID of actor executing mutation."),
    )
    actor_email = models.CharField(
        max_length=255,
        blank=True,
        help_text=_("Email address of actor."),
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
        help_text=_("Previous state JSON snapshot."),
    )
    new_state = models.JSONField(
        default=dict,
        blank=True,
        help_text=_("New state JSON snapshot."),
    )
    reason = models.TextField(
        blank=True,
        help_text=_("Rationale for event change."),
    )
    timestamp = models.DateTimeField(
        auto_now_add=True,
        db_index=True,
        help_text=_("Event creation timestamp."),
    )

    class Meta:
        verbose_name = _("attendance audit event")
        verbose_name_plural = _("attendance audit events")
        ordering = ["-timestamp"]
        indexes = [
            models.Index(fields=["attendance_record", "event_type"], name="idx_attevent_rec_type"),
        ]

    def __str__(self):
        return f"[{self.event_type}] Record {self.attendance_record_id} at {self.timestamp}"


class BreakType(models.TextChoices):
    LUNCH = "LUNCH", _("Lunch Break")
    TEA = "TEA", _("Tea / Coffee Break")
    PERSONAL = "PERSONAL", _("Personal Work Break")
    OFFICIAL = "OFFICIAL", _("Official Movement Break")


class CorrectionStatus(models.TextChoices):
    PENDING = "PENDING", _("Pending Approval")
    APPROVED = "APPROVED", _("Approved by Manager / HR")
    REJECTED = "REJECTED", _("Rejected")


class AttendanceBreak(BaseModel):
    """Break intervals (Lunch, Tea, Personal, Official) associated with an AttendanceSession."""

    session = models.ForeignKey(
        AttendanceSession,
        on_delete=models.CASCADE,
        related_name="breaks",
        help_text=_("Associated parent AttendanceSession."),
    )
    break_type = models.CharField(
        max_length=50,
        choices=BreakType.choices,
        default=BreakType.LUNCH,
        help_text=_("Category classification of break."),
    )
    start_time = models.DateTimeField(
        help_text=_("Break start timestamp."),
    )
    end_time = models.DateTimeField(
        null=True,
        blank=True,
        help_text=_("Break end timestamp."),
    )
    duration_minutes = models.PositiveIntegerField(
        default=0,
        help_text=_("Total break duration in minutes."),
    )
    is_paid = models.BooleanField(
        default=False,
        help_text=_("Flag indicating whether break duration counts toward working hours."),
    )

    class Meta:
        verbose_name = _("attendance break")
        verbose_name_plural = _("attendance breaks")
        ordering = ["start_time"]

    def __str__(self):
        return f"{self.break_type} Break ({self.start_time} -> {self.end_time or 'ACTIVE'})"


class AttendanceCorrectionRequest(BaseModel):
    """Formal employee/manager request to adjust or correct historical attendance records."""

    attendance_record = models.ForeignKey(
        AttendanceRecord,
        on_delete=models.CASCADE,
        related_name="correction_requests",
        help_text=_("Target AttendanceRecord to correct."),
    )
    requested_by = models.ForeignKey(
        Employee,
        on_delete=models.CASCADE,
        related_name="submitted_attendance_corrections",
        help_text=_("Employee submitting the correction request."),
    )
    requested_check_in = models.DateTimeField(
        null=True,
        blank=True,
        help_text=_("Proposed corrected check-in timestamp."),
    )
    requested_check_out = models.DateTimeField(
        null=True,
        blank=True,
        help_text=_("Proposed corrected check-out timestamp."),
    )
    requested_status = models.CharField(
        max_length=50,
        choices=AttendanceStatus.choices,
        default=AttendanceStatus.PRESENT,
        help_text=_("Proposed corrected status."),
    )
    reason = models.TextField(
        help_text=_("Operational rationale for attendance adjustment."),
    )
    status = models.CharField(
        max_length=50,
        choices=CorrectionStatus.choices,
        default=CorrectionStatus.PENDING,
        db_index=True,
        help_text=_("Workflow approval status."),
    )
    processed_by_id = models.CharField(
        max_length=100,
        blank=True,
        help_text=_("User ID of manager/HR approving/rejecting request."),
    )
    processed_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text=_("Approval timestamp."),
    )

    class Meta:
        verbose_name = _("attendance correction request")
        verbose_name_plural = _("attendance correction requests")
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["attendance_record", "status"], name="idx_attcorr_rec_status"),
        ]

    def __str__(self):
        return f"Correction for Record {self.attendance_record_id} [{self.status}]"

