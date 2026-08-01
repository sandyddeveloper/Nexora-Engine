"""Production-grade Django models for the Leave Management Foundation Engine."""

from decimal import Decimal
from django.db import models
from django.utils.translation import gettext_lazy as _

from apps.common.models import BaseModel
from apps.employees.models import Employee
from apps.organizations.models import Branch, Department, Designation, Organization

from .constants import (
    DEFAULT_ACCRUAL_CAP_DAYS,
    DEFAULT_ATTACHMENT_THRESHOLD_DAYS,
    DEFAULT_CARRY_FORWARD_EXPIRY_DAYS,
    DEFAULT_LEAVE_NOTICE_PERIOD_DAYS,
    DEFAULT_MAX_CARRY_FORWARD_DAYS,
    DEFAULT_MAX_CONSECUTIVE_LEAVE_DAYS,
    DEFAULT_MIN_GAP_BETWEEN_LEAVES_DAYS,
)
from .enums import (
    AccrualFrequency,
    AccrualMethod,
    ApprovalLevel,
    BalanceAdjustmentType,
    HalfDayPeriod,
    LeaveCategory,
    LeaveRequestStatus,
    ModificationType,
    ResetPeriod,
)


class GenderSuitability(models.TextChoices):
    ALL = "ALL", _("All Gender Suitability")
    MALE_ONLY = "MALE_ONLY", _("Male Employees Only")
    FEMALE_ONLY = "FEMALE_ONLY", _("Female Employees Only")


class LeaveType(BaseModel):
    """Enterprise leave category definitions (Annual, Casual, Sick, Earned, Comp Off, Maternity, etc.)."""

    organization = models.ForeignKey(
        Organization,
        on_delete=models.CASCADE,
        related_name="leave_types",
        help_text=_("Associated Organization."),
    )
    name = models.CharField(
        max_length=255,
        help_text=_("Display name of the leave category."),
    )
    code = models.CharField(
        max_length=50,
        db_index=True,
        help_text=_("Unique leave type code within organization."),
    )
    category = models.CharField(
        max_length=50,
        choices=LeaveCategory.choices,
        default=LeaveCategory.CASUAL,
        db_index=True,
        help_text=_("Standard leave category classification."),
    )
    description = models.TextField(
        blank=True,
        help_text=_("Detailed description of leave category rules and purpose."),
    )
    is_paid = models.BooleanField(
        default=True,
        help_text=_("Flag indicating whether this leave is paid by payroll."),
    )
    is_encashable = models.BooleanField(
        default=False,
        help_text=_("Flag indicating whether unused balance can be encashed."),
    )
    is_wfh_placeholder = models.BooleanField(
        default=False,
        help_text=_("Flag indicating WFH placeholder classification."),
    )
    is_compensatory_off = models.BooleanField(
        default=False,
        help_text=_("Flag indicating compensatory off leave type."),
    )
    requires_attachment = models.BooleanField(
        default=False,
        help_text=_("Flag indicating medical/document attachment is mandatory."),
    )
    gender_suitability = models.CharField(
        max_length=20,
        choices=GenderSuitability.choices,
        default=GenderSuitability.ALL,
        help_text=_("Gender eligibility suitability constraint."),
    )
    is_active = models.BooleanField(
        default=True,
        db_index=True,
        help_text=_("Active status flag for leave type."),
    )

    class Meta:
        verbose_name = _("leave type")
        verbose_name_plural = _("leave types")
        ordering = ["name"]
        constraints = [
            models.UniqueConstraint(
                fields=["organization", "code"],
                name="unique_leavetype_org_code",
            )
        ]

    def __str__(self):
        return f"{self.name} ({self.code})"


class LeavePolicy(BaseModel):
    """Leave policy governing leave accruals, limits, notice periods, carry forward, and expiry rules."""

    organization = models.ForeignKey(
        Organization,
        on_delete=models.CASCADE,
        related_name="leave_policies",
        help_text=_("Target Organization."),
    )
    leave_type = models.ForeignKey(
        LeaveType,
        on_delete=models.CASCADE,
        related_name="policies",
        help_text=_("Target LeaveType."),
    )
    name = models.CharField(
        max_length=255,
        help_text=_("Policy display name."),
    )
    code = models.CharField(
        max_length=50,
        db_index=True,
        help_text=_("Unique policy code within organization."),
    )
    max_leave_per_year = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=Decimal("12.00"),
        help_text=_("Maximum allowable leave quota per year."),
    )
    min_leave_per_request = models.DecimalField(
        max_digits=4,
        decimal_places=2,
        default=Decimal("0.50"),
        help_text=_("Minimum leave duration allowed per request."),
    )
    max_leave_per_request = models.DecimalField(
        max_digits=4,
        decimal_places=2,
        default=Decimal("15.00"),
        help_text=_("Maximum leave duration allowed per request."),
    )
    half_day_allowed = models.BooleanField(
        default=True,
        help_text=_("Flag indicating whether half-day requests are permitted."),
    )
    hourly_leave_allowed = models.BooleanField(
        default=False,
        help_text=_("Placeholder flag for hourly leave requests."),
    )
    negative_balance_allowed = models.BooleanField(
        default=False,
        help_text=_("Flag indicating whether negative leave balances are allowed."),
    )
    max_negative_balance = models.DecimalField(
        max_digits=4,
        decimal_places=2,
        default=Decimal("0.00"),
        help_text=_("Maximum permitted negative balance limit."),
    )
    carry_forward_allowed = models.BooleanField(
        default=False,
        help_text=_("Flag permitting unused balance carry-forward to next period."),
    )
    max_carry_forward_days = models.DecimalField(
        max_digits=4,
        decimal_places=2,
        default=Decimal(str(DEFAULT_MAX_CARRY_FORWARD_DAYS)),
        help_text=_("Maximum days permitted to carry forward."),
    )
    carry_forward_percentage = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=Decimal("100.00"),
        help_text=_("Percentage of unused balance eligible for carry forward."),
    )
    carry_forward_expiry_days = models.PositiveIntegerField(
        default=DEFAULT_CARRY_FORWARD_EXPIRY_DAYS,
        help_text=_("Days after period reset when carried-forward balance expires."),
    )
    notice_period_days = models.PositiveIntegerField(
        default=DEFAULT_LEAVE_NOTICE_PERIOD_DAYS,
        help_text=_("Required notice period in advance for leave requests."),
    )
    max_consecutive_days = models.PositiveIntegerField(
        default=DEFAULT_MAX_CONSECUTIVE_LEAVE_DAYS,
        help_text=_("Maximum allowable consecutive leave days."),
    )
    min_gap_between_leaves_days = models.PositiveIntegerField(
        default=DEFAULT_MIN_GAP_BETWEEN_LEAVES_DAYS,
        help_text=_("Minimum mandatory gap days required between two leave applications."),
    )
    attachment_required_threshold_days = models.PositiveIntegerField(
        default=DEFAULT_ATTACHMENT_THRESHOLD_DAYS,
        help_text=_("Leave duration threshold in days triggering mandatory attachment."),
    )
    reset_period = models.CharField(
        max_length=50,
        choices=ResetPeriod.choices,
        default=ResetPeriod.CALENDAR_YEAR,
        help_text=_("Annual balance reset cycle (Calendar, Financial, or Anniversary)."),
    )
    is_default = models.BooleanField(
        default=False,
        db_index=True,
        help_text=_("Default policy flag for the leave type within organization."),
    )
    is_active = models.BooleanField(
        default=True,
        db_index=True,
        help_text=_("Active state of policy."),
    )

    class Meta:
        verbose_name = _("leave policy")
        verbose_name_plural = _("leave policies")
        ordering = ["name"]
        constraints = [
            models.UniqueConstraint(
                fields=["organization", "code"],
                name="unique_leavepolicy_org_code",
            )
        ]

    def __str__(self):
        return f"{self.name} ({self.code})"


class LeaveConfiguration(BaseModel):
    """Hierarchical policy resolution override (Organization -> Branch -> Department -> Designation)."""

    organization = models.ForeignKey(
        Organization,
        on_delete=models.CASCADE,
        related_name="leave_configurations",
        help_text=_("Target Organization."),
    )
    branch = models.ForeignKey(
        Branch,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="leave_configurations",
        help_text=_("Target Branch."),
    )
    department = models.ForeignKey(
        Department,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="leave_configurations",
        help_text=_("Target Department."),
    )
    designation = models.ForeignKey(
        Designation,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="leave_configurations",
        help_text=_("Target Designation."),
    )
    default_policy = models.ForeignKey(
        LeavePolicy,
        on_delete=models.PROTECT,
        related_name="configurations",
        help_text=_("Governing default LeavePolicy."),
    )

    class Meta:
        verbose_name = _("leave configuration")
        verbose_name_plural = _("leave configurations")
        constraints = [
            models.UniqueConstraint(
                fields=["organization", "branch", "department", "designation", "default_policy"],
                name="unique_leaveconfig_hierarchy",
            )
        ]

    def __str__(self):
        return f"LeaveConfig: {self.organization.name} -> Policy: {self.default_policy.name}"


class LeaveBalance(BaseModel):
    """Live leave balance record enforcing strictly one record per employee per leave type."""

    employee = models.ForeignKey(
        Employee,
        on_delete=models.CASCADE,
        related_name="leave_balances",
        help_text=_("Target Employee."),
    )
    organization = models.ForeignKey(
        Organization,
        on_delete=models.CASCADE,
        related_name="leave_balances",
        help_text=_("Target Organization."),
    )
    leave_type = models.ForeignKey(
        LeaveType,
        on_delete=models.PROTECT,
        related_name="balances",
        help_text=_("Associated LeaveType."),
    )
    policy = models.ForeignKey(
        LeavePolicy,
        on_delete=models.PROTECT,
        related_name="balances",
        help_text=_("Governing LeavePolicy."),
    )
    opening_balance = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=Decimal("0.00"),
        help_text=_("Initial balance allocated at cycle start."),
    )
    allocated_accrued = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=Decimal("0.00"),
        help_text=_("Cumulative accrued credits in current cycle."),
    )
    used_balance = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=Decimal("0.00"),
        help_text=_("Total approved used leave days."),
    )
    pending_balance = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=Decimal("0.00"),
        help_text=_("Pending requested leave days awaiting approval."),
    )
    reserved_balance = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=Decimal("0.00"),
        help_text=_("Reserved balance for future approved leaves."),
    )
    expired_balance = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=Decimal("0.00"),
        help_text=_("Lapsed / expired balance days."),
    )
    carry_forward_balance = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=Decimal("0.00"),
        help_text=_("Balance carried forward from prior cycle."),
    )
    available_balance = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=Decimal("0.00"),
        db_index=True,
        help_text=_("Net available leave balance for application."),
    )
    last_accrual_date = models.DateField(
        null=True,
        blank=True,
        help_text=_("Date of last processed accrual."),
    )
    is_active = models.BooleanField(
        default=True,
        db_index=True,
        help_text=_("Active status flag for balance record."),
    )
    is_locked = models.BooleanField(
        default=False,
        db_index=True,
        help_text=_("Lock flag preventing mutations during payroll or year-end processing."),
    )

    class Meta:
        verbose_name = _("leave balance")
        verbose_name_plural = _("leave balances")
        ordering = ["employee", "leave_type"]
        constraints = [
            models.UniqueConstraint(
                fields=["employee", "leave_type"],
                name="unique_leavebalance_emp_leavetype",
            )
        ]
        indexes = [
            models.Index(fields=["employee", "leave_type"], name="idx_leavebal_emp_type"),
            models.Index(fields=["organization", "available_balance"], name="idx_leavebal_org_avail"),
        ]

    def recalculate_available_balance(self):
        """Recalculate available balance adhering to mathematical formula: (opening + accrued + carry_forward) - (used + pending + reserved + expired)."""
        self.available_balance = (
            self.opening_balance + self.allocated_accrued + self.carry_forward_balance
        ) - (self.used_balance + self.pending_balance + self.reserved_balance + self.expired_balance)
        return self.available_balance

    def __str__(self):
        return f"[{self.leave_type.code}] {self.employee.employee_id}: {self.available_balance} available"


class LeaveBalanceHistory(BaseModel):
    """Immutable ledger audit trail recording every balance mutation (Credit, Debit, Accrual, Expiry, Reset)."""

    leave_balance = models.ForeignKey(
        LeaveBalance,
        on_delete=models.CASCADE,
        related_name="history",
        help_text=_("Parent LeaveBalance record."),
    )
    employee = models.ForeignKey(
        Employee,
        on_delete=models.CASCADE,
        related_name="leave_balance_history",
        help_text=_("Target Employee."),
    )
    organization = models.ForeignKey(
        Organization,
        on_delete=models.CASCADE,
        related_name="leave_balance_history",
        help_text=_("Target Organization."),
    )
    leave_type = models.ForeignKey(
        LeaveType,
        on_delete=models.PROTECT,
        related_name="balance_history",
        help_text=_("Associated LeaveType."),
    )
    adjustment_type = models.CharField(
        max_length=50,
        choices=BalanceAdjustmentType.choices,
        db_index=True,
        help_text=_("Mutation classification (Credit, Debit, Accrual, Expiry, etc.)."),
    )
    delta = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        help_text=_("Magnitude of balance change."),
    )
    previous_available_balance = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        help_text=_("Prior available balance."),
    )
    new_available_balance = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        help_text=_("New available balance after adjustment."),
    )
    reason = models.TextField(
        blank=True,
        help_text=_("Operational rationale for adjustment."),
    )
    actor_user_id = models.CharField(
        max_length=100,
        blank=True,
        help_text=_("User ID of actor initiating mutation."),
    )
    actor_email = models.CharField(
        max_length=255,
        blank=True,
        help_text=_("Actor email address."),
    )

    class Meta:
        verbose_name = _("leave balance history")
        verbose_name_plural = _("leave balance histories")
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["leave_balance", "adjustment_type"], name="idx_leavebalhist_bal_type"),
        ]

    def __str__(self):
        return f"[{self.adjustment_type}] {self.employee.employee_id}: {self.delta} -> {self.new_available_balance}"


class LeaveAccrualRule(BaseModel):
    """Accrual calculation schedule rule associated with a LeavePolicy."""

    policy = models.ForeignKey(
        LeavePolicy,
        on_delete=models.CASCADE,
        related_name="accrual_rules",
        help_text=_("Parent LeavePolicy."),
    )
    accrual_frequency = models.CharField(
        max_length=50,
        choices=AccrualFrequency.choices,
        default=AccrualFrequency.MONTHLY,
        help_text=_("Frequency of scheduled accrual processing."),
    )
    accrual_method = models.CharField(
        max_length=50,
        choices=AccrualMethod.choices,
        default=AccrualMethod.FRONT_LOADED,
        help_text=_("Accrual calculation method."),
    )
    accrual_amount = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=Decimal("1.00"),
        help_text=_("Accrual credit amount per cycle."),
    )
    max_accrual_cap = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=Decimal(str(DEFAULT_ACCRUAL_CAP_DAYS)),
        help_text=_("Maximum cumulative balance cap for accruals."),
    )
    prorata_on_joining = models.BooleanField(
        default=True,
        help_text=_("Flag indicating whether pro-rata accrual applies during first joining month."),
    )

    class Meta:
        verbose_name = _("leave accrual rule")
        verbose_name_plural = _("leave accrual rules")

    def __str__(self):
        return f"AccrualRule: {self.policy.name} ({self.accrual_frequency}: {self.accrual_amount} days)"


class LeaveAccrualLog(BaseModel):
    """Execution log for automated and manual leave accruals."""

    leave_balance = models.ForeignKey(
        LeaveBalance,
        on_delete=models.CASCADE,
        related_name="accrual_logs",
        help_text=_("Target LeaveBalance."),
    )
    employee = models.ForeignKey(
        Employee,
        on_delete=models.CASCADE,
        related_name="accrual_logs",
        help_text=_("Target Employee."),
    )
    organization = models.ForeignKey(
        Organization,
        on_delete=models.CASCADE,
        related_name="leave_accrual_logs",
        help_text=_("Target Organization."),
    )
    leave_type = models.ForeignKey(
        LeaveType,
        on_delete=models.PROTECT,
        related_name="accrual_logs",
        help_text=_("Target LeaveType."),
    )
    accrual_date = models.DateField(
        db_index=True,
        help_text=_("Calendar date of accrual execution."),
    )
    accrued_amount = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        help_text=_("Amount credited during accrual run."),
    )
    accrual_frequency = models.CharField(
        max_length=50,
        choices=AccrualFrequency.choices,
        default=AccrualFrequency.MONTHLY,
        help_text=_("Accrual frequency cycle executed."),
    )
    status = models.CharField(
        max_length=50,
        default="SUCCESS",
        help_text=_("Execution status (SUCCESS, FAILED)."),
    )

    class Meta:
        verbose_name = _("leave accrual log")
        verbose_name_plural = _("leave accrual logs")
        ordering = ["-accrual_date"]

    def __str__(self):
        return f"AccrualLog {self.employee.employee_id}: +{self.accrued_amount} on {self.accrual_date}"


class LeaveCarryForwardRecord(BaseModel):
    """Audit record of year-end carry forward transactions."""

    employee = models.ForeignKey(
        Employee,
        on_delete=models.CASCADE,
        related_name="carry_forward_records",
        help_text=_("Target Employee."),
    )
    organization = models.ForeignKey(
        Organization,
        on_delete=models.CASCADE,
        related_name="leave_carry_forward_records",
        help_text=_("Target Organization."),
    )
    leave_type = models.ForeignKey(
        LeaveType,
        on_delete=models.PROTECT,
        related_name="carry_forward_records",
        help_text=_("Target LeaveType."),
    )
    from_year = models.PositiveIntegerField(
        help_text=_("Source calendar/financial year."),
    )
    to_year = models.PositiveIntegerField(
        help_text=_("Destination calendar/financial year."),
    )
    eligible_balance = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        help_text=_("Unused balance eligible for carry forward prior to cap."),
    )
    carried_forward_amount = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        help_text=_("Actual amount carried forward."),
    )
    lapsed_amount = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        help_text=_("Unused amount lapsed due to cap."),
    )
    expiry_date = models.DateField(
        null=True,
        blank=True,
        help_text=_("Expiration date of carried-forward balance."),
    )

    class Meta:
        verbose_name = _("leave carry forward record")
        verbose_name_plural = _("leave carry forward records")
        ordering = ["-created_at"]

    def __str__(self):
        return f"CarryForward {self.employee.employee_id}: {self.carried_forward_amount} ({self.from_year} -> {self.to_year})"


class LeaveEvent(BaseModel):
    """Immutable audit trail for all leave domain operations and policy changes."""

    leave_balance = models.ForeignKey(
        LeaveBalance,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="audit_events",
        help_text=_("Target LeaveBalance if applicable."),
    )
    organization = models.ForeignKey(
        Organization,
        on_delete=models.CASCADE,
        related_name="leave_audit_events",
        help_text=_("Target Organization."),
    )
    event_type = models.CharField(
        max_length=100,
        db_index=True,
        help_text=_("Audit event classification (e.g. BALANCE_INITIALIZED, ACCRUED)."),
    )
    actor_user_id = models.CharField(
        max_length=100,
        blank=True,
        help_text=_("Actor user ID."),
    )
    actor_email = models.CharField(
        max_length=255,
        blank=True,
        help_text=_("Actor email address."),
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
        help_text=_("Prior JSON state snapshot."),
    )
    new_state = models.JSONField(
        default=dict,
        blank=True,
        help_text=_("New JSON state snapshot."),
    )
    reason = models.TextField(
        blank=True,
        help_text=_("Operational justification."),
    )
    timestamp = models.DateTimeField(
        auto_now_add=True,
        db_index=True,
        help_text=_("Event creation timestamp."),
    )

    class Meta:
        verbose_name = _("leave audit event")
        verbose_name_plural = _("leave audit events")
        ordering = ["-timestamp"]

    def __str__(self):
        return f"[{self.event_type}] Org {self.organization_id} at {self.timestamp}"


class LeaveRequest(BaseModel):
    """Leave Request model supporting full-day, half-day, emergency, and multi-level approval state machine."""

    employee = models.ForeignKey(
        Employee,
        on_delete=models.CASCADE,
        related_name="leave_requests",
        help_text=_("Applicant Employee."),
    )
    organization = models.ForeignKey(
        Organization,
        on_delete=models.CASCADE,
        related_name="leave_requests",
        help_text=_("Associated Organization."),
    )
    leave_type = models.ForeignKey(
        LeaveType,
        on_delete=models.PROTECT,
        related_name="leave_requests",
        help_text=_("Applied LeaveType."),
    )
    policy = models.ForeignKey(
        LeavePolicy,
        on_delete=models.PROTECT,
        related_name="leave_requests",
        help_text=_("Governing LeavePolicy."),
    )
    leave_balance = models.ForeignKey(
        LeaveBalance,
        on_delete=models.PROTECT,
        related_name="leave_requests",
        help_text=_("Associated LeaveBalance record."),
    )
    start_date = models.DateField(
        db_index=True,
        help_text=_("Leave start date."),
    )
    end_date = models.DateField(
        db_index=True,
        help_text=_("Leave end date."),
    )
    total_days = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        help_text=_("Calculated actual working leave days duration."),
    )
    is_half_day = models.BooleanField(
        default=False,
        help_text=_("Flag indicating half-day leave request."),
    )
    half_day_period = models.CharField(
        max_length=20,
        choices=HalfDayPeriod.choices,
        null=True,
        blank=True,
        help_text=_("Half day session (FIRST_HALF or SECOND_HALF)."),
    )
    reason = models.TextField(
        help_text=_("Reason for leave request."),
    )
    attachment_url = models.URLField(
        max_length=500,
        blank=True,
        help_text=_("URL or path to supporting medical/official document."),
    )
    status = models.CharField(
        max_length=50,
        choices=LeaveRequestStatus.choices,
        default=LeaveRequestStatus.DRAFT,
        db_index=True,
        help_text=_("Current workflow status."),
    )
    current_approval_level = models.CharField(
        max_length=50,
        choices=ApprovalLevel.choices,
        default=ApprovalLevel.LEVEL_1_MANAGER,
        help_text=_("Current pending approval level."),
    )
    max_approval_levels = models.PositiveIntegerField(
        default=1,
        help_text=_("Configured approval levels required (1 to 3)."),
    )
    approver = models.ForeignKey(
        Employee,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="pending_leave_approvals",
        help_text=_("Currently assigned decision-making approver."),
    )
    rejection_reason = models.TextField(
        blank=True,
        help_text=_("Reason for rejection if rejected."),
    )
    cancellation_reason = models.TextField(
        blank=True,
        help_text=_("Reason for cancellation if cancelled."),
    )
    is_emergency = models.BooleanField(
        default=False,
        help_text=_("Emergency leave request flag bypassing standard notice period."),
    )
    is_past_leave = models.BooleanField(
        default=False,
        help_text=_("Past date retroactive leave request flag."),
    )

    class Meta:
        verbose_name = _("leave request")
        verbose_name_plural = _("leave requests")
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["employee", "status"], name="idx_leavereq_emp_status"),
            models.Index(fields=["organization", "start_date", "end_date"], name="idx_leavereq_org_dates"),
            models.Index(fields=["approver", "status"], name="idx_leavereq_appr_status"),
        ]

    def __str__(self):
        return f"LeaveRequest {self.id}: {self.employee.employee_id} ({self.start_date} to {self.end_date}) -> {self.status}"


class LeaveApprovalStep(BaseModel):
    """Approval decision record for each level in a multi-level approval chain."""

    leave_request = models.ForeignKey(
        LeaveRequest,
        on_delete=models.CASCADE,
        related_name="approval_steps",
        help_text=_("Parent LeaveRequest."),
    )
    level = models.CharField(
        max_length=50,
        choices=ApprovalLevel.choices,
        help_text=_("Approval level classification."),
    )
    approver = models.ForeignKey(
        Employee,
        on_delete=models.PROTECT,
        related_name="approval_decisions",
        help_text=_("Approver performing decision."),
    )
    status = models.CharField(
        max_length=50,
        choices=LeaveRequestStatus.choices,
        default=LeaveRequestStatus.PENDING,
        help_text=_("Decision status for this step."),
    )
    comments = models.TextField(
        blank=True,
        help_text=_("Approver comments or rationale."),
    )
    decision_timestamp = models.DateTimeField(
        null=True,
        blank=True,
        help_text=_("Timestamp of decision."),
    )

    class Meta:
        verbose_name = _("leave approval step")
        verbose_name_plural = _("leave approval steps")
        ordering = ["created_at"]
        constraints = [
            models.UniqueConstraint(
                fields=["leave_request", "level"],
                name="unique_leaveapprstep_req_level",
            )
        ]

    def __str__(self):
        return f"ApprovalStep {self.leave_request_id} [{self.level}]: {self.status}"


class LeaveRequestHistory(BaseModel):
    """Revision history recording state transitions and modifications for a LeaveRequest."""

    leave_request = models.ForeignKey(
        LeaveRequest,
        on_delete=models.CASCADE,
        related_name="history",
        help_text=_("Parent LeaveRequest."),
    )
    action = models.CharField(
        max_length=50,
        help_text=_("Action performed (e.g. SUBMITTED, APPROVED, MODIFIED, CANCELLED)."),
    )
    modification_type = models.CharField(
        max_length=50,
        choices=ModificationType.choices,
        null=True,
        blank=True,
        help_text=_("Modification category if action is MODIFIED."),
    )
    previous_state = models.JSONField(
        default=dict,
        blank=True,
        help_text=_("JSON snapshot of request prior to action."),
    )
    new_state = models.JSONField(
        default=dict,
        blank=True,
        help_text=_("JSON snapshot of request after action."),
    )
    comments = models.TextField(
        blank=True,
        help_text=_("User or system action notes."),
    )
    actor_user_id = models.CharField(
        max_length=100,
        blank=True,
        help_text=_("User ID of actor."),
    )
    actor_email = models.CharField(
        max_length=255,
        blank=True,
        help_text=_("Email address of actor."),
    )

    class Meta:
        verbose_name = _("leave request history")
        verbose_name_plural = _("leave request histories")
        ordering = ["-created_at"]

    def __str__(self):
        return f"RequestHistory {self.leave_request_id}: {self.action}"


class ApprovalDelegation(BaseModel):
    """Approval delegation rule assigning a backup/temporary approver during manager absence."""

    organization = models.ForeignKey(
        Organization,
        on_delete=models.CASCADE,
        related_name="approval_delegations",
        help_text=_("Associated Organization."),
    )
    delegator = models.ForeignKey(
        Employee,
        on_delete=models.CASCADE,
        related_name="outgoing_delegations",
        help_text=_("Manager delegating approval authority."),
    )
    delegatee = models.ForeignKey(
        Employee,
        on_delete=models.CASCADE,
        related_name="incoming_delegations",
        help_text=_("Temporary backup approver receiving authority."),
    )
    start_date = models.DateField(
        db_index=True,
        help_text=_("Delegation effective start date."),
    )
    end_date = models.DateField(
        db_index=True,
        help_text=_("Delegation effective end date."),
    )
    is_active = models.BooleanField(
        default=True,
        db_index=True,
        help_text=_("Active flag for delegation rule."),
    )
    reason = models.TextField(
        blank=True,
        help_text=_("Rationale for delegation."),
    )

    class Meta:
        verbose_name = _("approval delegation")
        verbose_name_plural = _("approval delegations")
        ordering = ["-start_date"]

    def __str__(self):
        return f"Delegation: {self.delegator.employee_id} -> {self.delegatee.employee_id} ({self.start_date} to {self.end_date})"

