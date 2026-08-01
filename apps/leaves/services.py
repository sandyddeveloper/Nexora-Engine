"""Domain state mutation service functions for the Leave Management Foundation Engine."""

import logging
import uuid
from datetime import date, datetime, timezone
from decimal import Decimal

from django.db import transaction

from apps.employees.models import Employee, EmploymentStatus
from apps.organizations.models import Organization

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
from .events import (
    AnalyticsCacheInvalidated,
    LeaveAccrued,
    LeaveAnalyticsGenerated,
    LeaveApproved,
    LeaveBalanceAdjusted,
    LeaveBalanceInitialized,
    LeaveCancelled,
    LeaveCarryForwardCompleted,
    LeaveComplianceCalculated,
    LeaveConfigurationChanged,
    LeaveDashboardRefreshed,
    LeaveExpired,
    LeaveExportGenerated,
    LeaveModified,
    LeavePolicyCreated,
    LeaveRejected,
    LeaveReportGenerated,
    LeaveRequested,
    LeaveSubmitted,
    LeaveWithdrawn,
    publish_leave_event,
)
from .exceptions import (
    LeaveAccrualError,
    LeaveBalanceError,
    LeaveCarryForwardError,
    LeaveEligibilityError,
    LeavePolicyValidationError,
)
from .models import (
    ApprovalDelegation,
    LeaveAccrualLog,
    LeaveAccrualRule,
    LeaveApprovalStep,
    LeaveBalance,
    LeaveBalanceHistory,
    LeaveCarryForwardRecord,
    LeaveConfiguration,
    LeaveEvent,
    LeavePolicy,
    LeaveRequest,
    LeaveRequestHistory,
    LeaveType,
)
from .selectors import (
    calculate_working_days_between,
    check_leave_eligibility,
    check_leave_overlap,
    get_active_delegated_approver,
    get_effective_leave_configuration,
    get_employee_leave_balance,
)

logger = logging.getLogger("nexora.leaves.services")


@transaction.atomic
def create_leave_type(
    *,
    organization: Organization,
    name: str,
    code: str,
    category: str = LeaveCategory.CASUAL,
    description: str = "",
    is_paid: bool = True,
    is_encashable: bool = False,
    is_wfh_placeholder: bool = False,
    is_compensatory_off: bool = False,
    requires_attachment: bool = False,
    gender_suitability: str = "ALL",
) -> LeaveType:
    """Create a new LeaveType definition for an organization."""
    if LeaveType.objects.filter(organization=organization, code=code.upper()).exists():
        raise LeavePolicyValidationError(f"LeaveType code '{code}' already exists in organization.")

    leave_type = LeaveType.objects.create(
        organization=organization,
        name=name,
        code=code.upper(),
        category=category,
        description=description,
        is_paid=is_paid,
        is_encashable=is_encashable,
        is_wfh_placeholder=is_wfh_placeholder,
        is_compensatory_off=is_compensatory_off,
        requires_attachment=requires_attachment,
        gender_suitability=gender_suitability,
    )

    logger.info("LeaveType created: %s (%s) for Org %s", leave_type.name, leave_type.code, organization.code)
    return leave_type


@transaction.atomic
def create_leave_policy(
    *,
    organization: Organization,
    leave_type: LeaveType,
    name: str,
    code: str,
    max_leave_per_year: Decimal = Decimal("12.00"),
    min_leave_per_request: Decimal = Decimal("0.50"),
    max_leave_per_request: Decimal = Decimal("15.00"),
    half_day_allowed: bool = True,
    hourly_leave_allowed: bool = False,
    negative_balance_allowed: bool = False,
    max_negative_balance: Decimal = Decimal("0.00"),
    carry_forward_allowed: bool = False,
    max_carry_forward_days: Decimal = Decimal("10.00"),
    carry_forward_percentage: Decimal = Decimal("100.00"),
    carry_forward_expiry_days: int = 90,
    notice_period_days: int = 3,
    max_consecutive_days: int = 15,
    min_gap_between_leaves_days: int = 0,
    attachment_required_threshold_days: int = 3,
    reset_period: str = ResetPeriod.CALENDAR_YEAR,
    is_default: bool = False,
) -> LeavePolicy:
    """Create a new LeavePolicy for a LeaveType in an organization."""
    if leave_type.organization_id != organization.id:
        raise LeavePolicyValidationError("LeaveType must belong to specified organization.")

    if LeavePolicy.objects.filter(organization=organization, code=code.upper()).exists():
        raise LeavePolicyValidationError(f"LeavePolicy code '{code}' already exists in organization.")

    if is_default:
        LeavePolicy.objects.filter(organization=organization, leave_type=leave_type, is_default=True).update(is_default=False)

    policy = LeavePolicy.objects.create(
        organization=organization,
        leave_type=leave_type,
        name=name,
        code=code.upper(),
        max_leave_per_year=max_leave_per_year,
        min_leave_per_request=min_leave_per_request,
        max_leave_per_request=max_leave_per_request,
        half_day_allowed=half_day_allowed,
        hourly_leave_allowed=hourly_leave_allowed,
        negative_balance_allowed=negative_balance_allowed,
        max_negative_balance=max_negative_balance,
        carry_forward_allowed=carry_forward_allowed,
        max_carry_forward_days=max_carry_forward_days,
        carry_forward_percentage=carry_forward_percentage,
        carry_forward_expiry_days=carry_forward_expiry_days,
        notice_period_days=notice_period_days,
        max_consecutive_days=max_consecutive_days,
        min_gap_between_leaves_days=min_gap_between_leaves_days,
        attachment_required_threshold_days=attachment_required_threshold_days,
        reset_period=reset_period,
        is_default=is_default,
    )

    publish_leave_event(
        LeavePolicyCreated(
            event_id=str(uuid.uuid4()),
            event_type="LEAVE_POLICY_CREATED",
            organization_id=str(organization.id),
            leave_type_id=str(leave_type.id),
            policy_name=policy.name,
            policy_code=policy.code,
        )
    )

    logger.info("LeavePolicy created: %s (%s) for LeaveType %s", policy.name, policy.code, leave_type.code)
    return policy


@transaction.atomic
def set_leave_configuration(
    *,
    organization: Organization,
    default_policy: LeavePolicy,
    branch=None,
    department=None,
    designation=None,
) -> LeaveConfiguration:
    """Create or update hierarchical LeaveConfiguration settings."""
    if default_policy.organization_id != organization.id:
        raise LeavePolicyValidationError("Default policy must belong to specified organization.")

    cfg, created = LeaveConfiguration.objects.update_or_create(
        organization=organization,
        branch=branch,
        department=department,
        designation=designation,
        defaults={"default_policy": default_policy},
    )

    publish_leave_event(
        LeaveConfigurationChanged(
            event_id=str(uuid.uuid4()),
            event_type="LEAVE_CONFIGURATION_CHANGED",
            organization_id=str(organization.id),
            configuration_id=str(cfg.id),
        )
    )

    logger.info("LeaveConfiguration updated for Org %s", organization.code)
    return cfg


@transaction.atomic
def initialize_employee_leave_balance(
    *,
    employee: Employee,
    leave_type: LeaveType,
    policy: LeavePolicy | None = None,
    opening_balance: Decimal = Decimal("0.00"),
    actor_user_id: str = "",
    actor_email: str = "",
) -> LeaveBalance:
    """Initialize LeaveBalance for an employee enforcing single active balance rule."""
    if LeaveBalance.objects.filter(employee=employee, leave_type=leave_type, is_active=True).exists():
        raise LeaveBalanceError(f"Active LeaveBalance already exists for {employee.display_name} and {leave_type.code}.")

    is_eligible, reason = check_leave_eligibility(employee=employee, leave_type=leave_type)
    # If balance doesn't exist yet, check eligibility except for balance presence check
    if not is_eligible and "No active leave balance" not in reason:
        raise LeaveEligibilityError(f"Employee {employee.display_name} is ineligible: {reason}")

    effective_policy = policy or get_effective_leave_configuration(
        organization_id=employee.organization_id,
        branch_id=employee.branch_id,
        department_id=employee.department_id,
        designation_id=employee.designation_id,
    )
    effective_policy = effective_policy.default_policy if hasattr(effective_policy, "default_policy") else (policy or leave_type.policies.filter(is_default=True).first())

    if not effective_policy:
        from .selectors import get_default_leave_policy
        effective_policy = get_default_leave_policy(organization_id=employee.organization_id, leave_type_id=leave_type.id)
        if not effective_policy:
            raise LeavePolicyValidationError(f"No active LeavePolicy configured for leave type {leave_type.code}.")

    bal = LeaveBalance.objects.create(
        employee=employee,
        organization=employee.organization,
        leave_type=leave_type,
        policy=effective_policy,
        opening_balance=opening_balance,
        available_balance=opening_balance,
    )

    LeaveBalanceHistory.objects.create(
        leave_balance=bal,
        employee=employee,
        organization=employee.organization,
        leave_type=leave_type,
        adjustment_type=BalanceAdjustmentType.INITIALIZATION,
        delta=opening_balance,
        previous_available_balance=Decimal("0.00"),
        new_available_balance=opening_balance,
        reason="Initial leave balance setup.",
        actor_user_id=actor_user_id,
        actor_email=actor_email,
    )

    publish_leave_event(
        LeaveBalanceInitialized(
            event_id=str(uuid.uuid4()),
            event_type="LEAVE_BALANCE_INITIALIZED",
            organization_id=str(employee.organization_id),
            employee_id=str(employee.id),
            leave_type_id=str(leave_type.id),
            leave_category=leave_type.category,
            opening_balance=float(opening_balance),
        )
    )

    logger.info("Initialized LeaveBalance for %s (%s): %s days", employee.employee_id, leave_type.code, opening_balance)
    return bal


@transaction.atomic
def adjust_leave_balance(
    *,
    leave_balance: LeaveBalance,
    adjustment_type: str,
    delta: Decimal,
    reason: str,
    actor_user_id: str = "",
    actor_email: str = "",
) -> LeaveBalance:
    """Execute transaction-safe credit/debit adjustment to an employee's LeaveBalance."""
    if leave_balance.is_locked:
        raise LeaveBalanceError("Cannot adjust a locked leave balance record.")

    prev_available = leave_balance.available_balance

    if adjustment_type == BalanceAdjustmentType.CREDIT or adjustment_type == BalanceAdjustmentType.ACCRUAL:
        leave_balance.allocated_accrued += delta
    elif adjustment_type == BalanceAdjustmentType.DEBIT:
        leave_balance.used_balance += delta
    elif adjustment_type == BalanceAdjustmentType.EXPIRE:
        leave_balance.expired_balance += delta
    elif adjustment_type == BalanceAdjustmentType.CARRY_FORWARD:
        leave_balance.carry_forward_balance += delta
    elif adjustment_type == BalanceAdjustmentType.MANUAL_CORRECTION:
        leave_balance.opening_balance += delta
    else:
        raise LeaveBalanceError(f"Invalid balance adjustment type: {adjustment_type}")

    leave_balance.recalculate_available_balance()
    leave_balance.save()

    LeaveBalanceHistory.objects.create(
        leave_balance=leave_balance,
        employee=leave_balance.employee,
        organization=leave_balance.organization,
        leave_type=leave_balance.leave_type,
        adjustment_type=adjustment_type,
        delta=delta,
        previous_available_balance=prev_available,
        new_available_balance=leave_balance.available_balance,
        reason=reason,
        actor_user_id=actor_user_id,
        actor_email=actor_email,
    )

    publish_leave_event(
        LeaveBalanceAdjusted(
            event_id=str(uuid.uuid4()),
            event_type="LEAVE_BALANCE_ADJUSTED",
            organization_id=str(leave_balance.organization_id),
            employee_id=str(leave_balance.employee_id),
            leave_type_id=str(leave_balance.leave_type_id),
            adjustment_type=adjustment_type,
            amount=float(delta),
            new_available_balance=float(leave_balance.available_balance),
        )
    )

    logger.info("Adjusted LeaveBalance %s [%s]: %s -> %s", leave_balance.id, adjustment_type, delta, leave_balance.available_balance)
    return leave_balance


@transaction.atomic
def process_scheduled_accruals(
    *,
    organization: Organization,
    accrual_frequency: str = AccrualFrequency.MONTHLY,
    accrual_date: date | None = None,
) -> dict:
    """Periodic Leave Accrual Engine: credits scheduled leave accruals to active employee balances."""
    run_date = accrual_date or date.today()
    balances = LeaveBalance.objects.filter(
        organization=organization, is_active=True, is_locked=False
    ).select_related("employee", "leave_type", "policy")

    accrued_count = 0
    total_accrued = Decimal("0.00")

    for bal in balances:
        policy = bal.policy
        # Standard monthly accrual logic (max_leave_per_year / 12)
        if accrual_frequency == AccrualFrequency.MONTHLY:
            accrual_amount = Decimal(str(round(float(policy.max_leave_per_year) / 12.0, 2)))
        elif accrual_frequency == AccrualFrequency.QUARTERLY:
            accrual_amount = Decimal(str(round(float(policy.max_leave_per_year) / 4.0, 2)))
        elif accrual_frequency == AccrualFrequency.YEARLY:
            accrual_amount = policy.max_leave_per_year
        else:
            accrual_amount = Decimal("1.00")

        adjust_leave_balance(
            leave_balance=bal,
            adjustment_type=BalanceAdjustmentType.ACCRUAL,
            delta=accrual_amount,
            reason=f"Scheduled {accrual_frequency} accrual credit for {run_date.strftime('%B %Y')}.",
        )

        bal.last_accrual_date = run_date
        bal.save(update_fields=["last_accrual_date"])

        LeaveAccrualLog.objects.create(
            leave_balance=bal,
            employee=bal.employee,
            organization=organization,
            leave_type=bal.leave_type,
            accrual_date=run_date,
            accrued_amount=accrual_amount,
            accrual_frequency=accrual_frequency,
            status="SUCCESS",
        )

        publish_leave_event(
            LeaveAccrued(
                event_id=str(uuid.uuid4()),
                event_type="LEAVE_ACCRUED",
                organization_id=str(organization.id),
                employee_id=str(bal.employee_id),
                leave_type_id=str(bal.leave_type_id),
                accrual_frequency=accrual_frequency,
                accrued_amount=float(accrual_amount),
            )
        )

        accrued_count += 1
        total_accrued += accrual_amount

    logger.info("Processed %s accruals for Org %s: %d balances credited, total %s days", accrual_frequency, organization.code, accrued_count, total_accrued)
    return {"accrued_count": accrued_count, "total_accrued_days": float(total_accrued)}


@transaction.atomic
def process_carry_forward(
    *,
    organization: Organization,
    from_year: int,
    to_year: int,
) -> dict:
    """Carry Forward Engine: processes year-end leave balance carry forward transfers and caps."""
    balances = LeaveBalance.objects.filter(
        organization=organization, is_active=True, is_locked=False
    ).select_related("employee", "leave_type", "policy")

    processed_count = 0
    total_carried = Decimal("0.00")

    for bal in balances:
        policy = bal.policy
        if not policy.carry_forward_allowed:
            continue

        available = bal.available_balance
        if available <= Decimal("0.00"):
            continue

        pct = policy.carry_forward_percentage / Decimal("100.00")
        eligible = available * pct
        carried = min(eligible, policy.max_carry_forward_days)
        lapsed = max(Decimal("0.00"), available - carried)

        adjust_leave_balance(
            leave_balance=bal,
            adjustment_type=BalanceAdjustmentType.CARRY_FORWARD,
            delta=carried,
            reason=f"Year-end carry forward transfer from {from_year} to {to_year}.",
        )

        if lapsed > Decimal("0.00"):
            adjust_leave_balance(
                leave_balance=bal,
                adjustment_type=BalanceAdjustmentType.EXPIRE,
                delta=lapsed,
                reason=f"Lapsed balance in year-end carry forward cap from {from_year}.",
            )

        LeaveCarryForwardRecord.objects.create(
            employee=bal.employee,
            organization=organization,
            leave_type=bal.leave_type,
            from_year=from_year,
            to_year=to_year,
            eligible_balance=eligible,
            carried_forward_amount=carried,
            lapsed_amount=lapsed,
        )

        publish_leave_event(
            LeaveCarryForwardCompleted(
                event_id=str(uuid.uuid4()),
                event_type="LEAVE_CARRY_FORWARD_COMPLETED",
                organization_id=str(organization.id),
                employee_id=str(bal.employee_id),
                leave_type_id=str(bal.leave_type_id),
                carried_forward_amount=float(carried),
            )
        )

        processed_count += 1
        total_carried += carried

    logger.info("Carry forward completed for Org %s: %d processed, total %s days carried", organization.code, processed_count, total_carried)
    return {"processed_count": processed_count, "total_carried_days": float(total_carried)}


@transaction.atomic
def process_leave_expiry(
    *,
    organization: Organization,
    expiry_date: date | None = None,
) -> dict:
    """Leave Expiry Engine: lapses unutilized expired leave balances."""
    run_date = expiry_date or date.today()
    records = LeaveCarryForwardRecord.objects.filter(
        organization=organization,
        expiry_date__lte=run_date,
        carried_forward_amount__gt=Decimal("0.00"),
    ).select_related("employee", "leave_type")

    expired_count = 0
    total_expired = Decimal("0.00")

    for rec in records:
        bal = get_employee_leave_balance(employee_id=rec.employee_id, leave_type_id=rec.leave_type_id)
        if not bal or bal.carry_forward_balance <= Decimal("0.00"):
            continue

        expire_amount = min(bal.carry_forward_balance, rec.carried_forward_amount)
        bal.carry_forward_balance -= expire_amount
        bal.expired_balance += expire_amount
        bal.recalculate_available_balance()
        bal.save()

        LeaveBalanceHistory.objects.create(
            leave_balance=bal,
            employee=bal.employee,
            organization=organization,
            leave_type=bal.leave_type,
            adjustment_type=BalanceAdjustmentType.EXPIRE,
            delta=expire_amount,
            previous_available_balance=bal.available_balance + expire_amount,
            new_available_balance=bal.available_balance,
            reason=f"Carried-forward leave balance expired on {run_date.isoformat()}.",
        )

        publish_leave_event(
            LeaveExpired(
                event_id=str(uuid.uuid4()),
                event_type="LEAVE_EXPIRED",
                organization_id=str(organization.id),
                employee_id=str(bal.employee_id),
                leave_type_id=str(bal.leave_type_id),
                expired_amount=float(expire_amount),
            )
        )

        rec.carried_forward_amount = Decimal("0.00")
        rec.save(update_fields=["carried_forward_amount"])

        expired_count += 1
        total_expired += expire_amount

    logger.info("Processed leave expiry for Org %s: %d records expired, total %s days", organization.code, expired_count, total_expired)
    return {"expired_count": expired_count, "total_expired_days": float(total_expired)}


# ── Leave Request & Approval Workflow Services ───────────────────────────────


@transaction.atomic
def apply_leave_request(
    *,
    employee: Employee,
    leave_type: LeaveType,
    start_date: date,
    end_date: date,
    reason: str,
    is_half_day: bool = False,
    half_day_period: str | None = None,
    attachment_url: str = "",
    is_emergency: bool = False,
    is_draft: bool = False,
) -> LeaveRequest:
    """Apply for a new LeaveRequest with validation checks (overlaps, balance, notice period, eligibility)."""
    if start_date > end_date:
        raise LeavePolicyValidationError("Leave start date cannot be after end date.")

    # 1. Overlap Check
    if check_leave_overlap(employee_id=employee.id, start_date=start_date, end_date=end_date):
        raise LeavePolicyValidationError("Overlapping leave request already exists for the specified dates.")

    # 2. Balance & Policy Resolution
    bal = get_employee_leave_balance(employee_id=employee.id, leave_type_id=leave_type.id)
    if not bal:
        raise LeaveEligibilityError(f"No active LeaveBalance initialized for {employee.display_name} and {leave_type.code}.")

    policy = bal.policy

    # 3. Calculate Working Days
    working_info = calculate_working_days_between(
        organization_id=employee.organization_id, start_date=start_date, end_date=end_date, employee=employee
    )
    calc_days = Decimal(str(working_info["working_days"]))
    if is_half_day:
        calc_days = Decimal("0.50")

    if calc_days <= Decimal("0.00"):
        raise LeavePolicyValidationError("Selected date window contains 0 working days (Holidays/Weekly Offs only).")

    # 4. Notice Period Check (if not emergency)
    if not is_emergency:
        days_notice = (start_date - date.today()).days
        if days_notice < policy.notice_period_days:
            raise LeavePolicyValidationError(f"Leave request violates mandatory notice period ({policy.notice_period_days} days notice required).")

    # 5. Attachment Requirement Check
    if policy.attachment_required_threshold_days and calc_days >= Decimal(str(policy.attachment_required_threshold_days)):
        if not attachment_url:
            raise LeavePolicyValidationError(f"Attachment is mandatory for leave requests of {policy.attachment_required_threshold_days} days or more.")

    # 6. Eligibility Verification
    is_eligible, elig_reason = check_leave_eligibility(employee=employee, leave_type=leave_type, requested_days=float(calc_days))
    if not is_eligible:
        raise LeaveEligibilityError(elig_reason)

    # Resolve Approver (Reporting Manager or Delegated Approver)
    manager = employee.reporting_manager
    assigned_approver = None
    if manager:
        delegated = get_active_delegated_approver(manager_employee_id=manager.id, date_obj=start_date)
        assigned_approver = delegated or manager

    status = LeaveRequestStatus.DRAFT if is_draft else LeaveRequestStatus.SUBMITTED

    req = LeaveRequest.objects.create(
        employee=employee,
        organization=employee.organization,
        leave_type=leave_type,
        policy=policy,
        leave_balance=bal,
        start_date=start_date,
        end_date=end_date,
        total_days=calc_days,
        is_half_day=is_half_day,
        half_day_period=half_day_period,
        reason=reason,
        attachment_url=attachment_url,
        status=status,
        current_approval_level=ApprovalLevel.LEVEL_1_MANAGER,
        max_approval_levels=1,
        approver=assigned_approver,
        is_emergency=is_emergency,
        is_past_leave=(start_date < date.today()),
    )

    LeaveRequestHistory.objects.create(
        leave_request=req,
        action="DRAFT_CREATED" if is_draft else "APPLIED",
        previous_state={},
        new_state={"status": status, "total_days": float(calc_days)},
        comments="Leave request created.",
        actor_user_id=str(employee.user_id) if hasattr(employee, "user_id") else "",
        actor_email=employee.official_email,
    )

    publish_leave_event(
        LeaveRequested(
            event_id=str(uuid.uuid4()),
            event_type="LEAVE_REQUESTED",
            organization_id=str(employee.organization_id),
            employee_id=str(employee.id),
            leave_type_id=str(leave_type.id),
            request_id=str(req.id),
            start_date=start_date.isoformat(),
            end_date=end_date.isoformat(),
            total_days=float(calc_days),
        )
    )

    logger.info("LeaveRequest %s created for %s (%s to %s) -> Status: %s", req.id, employee.employee_id, start_date, end_date, status)
    return req


@transaction.atomic
def submit_leave_request(*, leave_request: LeaveRequest, actor_email: str = "") -> LeaveRequest:
    """Submit a draft LeaveRequest for approval processing."""
    if leave_request.status != LeaveRequestStatus.DRAFT:
        raise LeavePolicyValidationError(f"Cannot submit request with status '{leave_request.status}'. Must be DRAFT.")

    leave_request.status = LeaveRequestStatus.SUBMITTED
    leave_request.save(update_fields=["status", "updated_at"])

    LeaveRequestHistory.objects.create(
        leave_request=leave_request,
        action="SUBMITTED",
        previous_state={"status": LeaveRequestStatus.DRAFT},
        new_state={"status": LeaveRequestStatus.SUBMITTED},
        comments="Draft leave request submitted.",
        actor_email=actor_email,
    )

    publish_leave_event(
        LeaveSubmitted(
            event_id=str(uuid.uuid4()),
            event_type="LEAVE_SUBMITTED",
            organization_id=str(leave_request.organization_id),
            employee_id=str(leave_request.employee_id),
            leave_type_id=str(leave_request.leave_type_id),
            request_id=str(leave_request.id),
            approver_id=str(leave_request.approver_id) if leave_request.approver_id else "",
        )
    )

    logger.info("LeaveRequest %s submitted for approval.", leave_request.id)
    return leave_request


@transaction.atomic
def approve_leave_request(
    *,
    leave_request: LeaveRequest,
    approver: Employee,
    comments: str = "",
    actor_user_id: str = "",
    actor_email: str = "",
) -> LeaveRequest:
    """Approve a LeaveRequest: updates status, deducts LeaveBalance, syncs Attendance records, and logs history."""
    if leave_request.status not in [LeaveRequestStatus.SUBMITTED, LeaveRequestStatus.PENDING]:
        raise LeavePolicyValidationError(f"Cannot approve request with status '{leave_request.status}'.")

    prev_status = leave_request.status
    leave_request.status = LeaveRequestStatus.APPROVED
    leave_request.save(update_fields=["status", "updated_at"])

    # Create Approval Step Record
    LeaveApprovalStep.objects.create(
        leave_request=leave_request,
        level=leave_request.current_approval_level,
        approver=approver,
        status=LeaveRequestStatus.APPROVED,
        comments=comments,
        decision_timestamp=datetime.now(timezone.utc),
    )

    # Deduct Leave Balance (DEBIT)
    adjust_leave_balance(
        leave_balance=leave_request.leave_balance,
        adjustment_type=BalanceAdjustmentType.DEBIT,
        delta=leave_request.total_days,
        reason=f"Leave request {leave_request.id} approved by {approver.display_name}.",
        actor_user_id=actor_user_id,
        actor_email=actor_email,
    )

    # Sync with Attendance Domain (Create / Update AttendanceRecords for dates covered)
    from apps.attendance.models import AttendanceRecord, AttendanceStatus
    from apps.attendance.selectors import get_default_attendance_policy
    from datetime import timedelta

    att_policy = get_default_attendance_policy(organization_id=leave_request.organization_id)

    curr_date = leave_request.start_date
    while curr_date <= leave_request.end_date:
        defaults = {
            "organization": leave_request.organization,
            "branch": leave_request.employee.branch,
            "department": leave_request.employee.department,
            "designation": leave_request.employee.designation,
            "status": AttendanceStatus.LEAVE,
            "remarks": f"Approved Leave ({leave_request.leave_type.name})",
        }
        if att_policy:
            defaults["policy"] = att_policy

        rec, created = AttendanceRecord.objects.get_or_create(
            employee=leave_request.employee,
            attendance_date=curr_date,
            defaults=defaults,
        )
        if not created and rec.status != AttendanceStatus.LEAVE:
            rec.status = AttendanceStatus.LEAVE
            rec.remarks = f"Approved Leave ({leave_request.leave_type.name})"
            rec.save(update_fields=["status", "remarks", "updated_at"])
        curr_date += timedelta(days=1)

    # Record History
    LeaveRequestHistory.objects.create(
        leave_request=leave_request,
        action="APPROVED",
        previous_state={"status": prev_status},
        new_state={"status": LeaveRequestStatus.APPROVED},
        comments=comments or f"Approved by {approver.display_name}.",
        actor_user_id=actor_user_id,
        actor_email=actor_email,
    )

    publish_leave_event(
        LeaveApproved(
            event_id=str(uuid.uuid4()),
            event_type="LEAVE_APPROVED",
            organization_id=str(leave_request.organization_id),
            employee_id=str(leave_request.employee_id),
            leave_type_id=str(leave_request.leave_type_id),
            request_id=str(leave_request.id),
            approver_id=str(approver.id),
            level=leave_request.current_approval_level,
        )
    )

    logger.info("LeaveRequest %s approved by %s.", leave_request.id, approver.display_name)
    return leave_request


@transaction.atomic
def reject_leave_request(
    *,
    leave_request: LeaveRequest,
    approver: Employee,
    rejection_reason: str,
    actor_user_id: str = "",
    actor_email: str = "",
) -> LeaveRequest:
    """Reject a LeaveRequest with rationale log."""
    if leave_request.status not in [LeaveRequestStatus.SUBMITTED, LeaveRequestStatus.PENDING]:
        raise LeavePolicyValidationError(f"Cannot reject request with status '{leave_request.status}'.")

    prev_status = leave_request.status
    leave_request.status = LeaveRequestStatus.REJECTED
    leave_request.rejection_reason = rejection_reason
    leave_request.save(update_fields=["status", "rejection_reason", "updated_at"])

    LeaveApprovalStep.objects.create(
        leave_request=leave_request,
        level=leave_request.current_approval_level,
        approver=approver,
        status=LeaveRequestStatus.REJECTED,
        comments=rejection_reason,
        decision_timestamp=datetime.now(timezone.utc),
    )

    LeaveRequestHistory.objects.create(
        leave_request=leave_request,
        action="REJECTED",
        previous_state={"status": prev_status},
        new_state={"status": LeaveRequestStatus.REJECTED, "rejection_reason": rejection_reason},
        comments=rejection_reason,
        actor_user_id=actor_user_id,
        actor_email=actor_email,
    )

    publish_leave_event(
        LeaveRejected(
            event_id=str(uuid.uuid4()),
            event_type="LEAVE_REJECTED",
            organization_id=str(leave_request.organization_id),
            employee_id=str(leave_request.employee_id),
            leave_type_id=str(leave_request.leave_type_id),
            request_id=str(leave_request.id),
            rejection_reason=rejection_reason,
        )
    )

    logger.info("LeaveRequest %s rejected by %s.", leave_request.id, approver.display_name)
    return leave_request


@transaction.atomic
def cancel_leave_request(
    *,
    leave_request: LeaveRequest,
    cancellation_reason: str,
    actor_user_id: str = "",
    actor_email: str = "",
) -> LeaveRequest:
    """Cancel an approved/submitted LeaveRequest: restores LeaveBalance and reverts Attendance records."""
    prev_status = leave_request.status
    if prev_status in [LeaveRequestStatus.CANCELLED, LeaveRequestStatus.WITHDRAWN, LeaveRequestStatus.REJECTED]:
        raise LeavePolicyValidationError(f"Cannot cancel a request that is already '{prev_status}'.")

    was_approved = (prev_status == LeaveRequestStatus.APPROVED)

    leave_request.status = LeaveRequestStatus.CANCELLED
    leave_request.cancellation_reason = cancellation_reason
    leave_request.save(update_fields=["status", "cancellation_reason", "updated_at"])

    # If was approved, restore LeaveBalance (CREDIT)
    if was_approved:
        adjust_leave_balance(
            leave_balance=leave_request.leave_balance,
            adjustment_type=BalanceAdjustmentType.CREDIT,
            delta=leave_request.total_days,
            reason=f"Leave request {leave_request.id} cancelled. Restoring balance.",
            actor_user_id=actor_user_id,
            actor_email=actor_email,
        )

        # Revert Attendance Records
        from apps.attendance.models import AttendanceRecord, AttendanceStatus
        records = AttendanceRecord.objects.filter(
            employee=leave_request.employee,
            attendance_date__gte=leave_request.start_date,
            attendance_date__lte=leave_request.end_date,
        )
        for r in records:
            r.status = AttendanceStatus.ABSENT  # Revert to absent/unprocessed
            r.remarks = f"Leave Cancelled ({leave_request.id})"
            r.save(update_fields=["status", "remarks", "updated_at"])

    LeaveRequestHistory.objects.create(
        leave_request=leave_request,
        action="CANCELLED",
        previous_state={"status": prev_status},
        new_state={"status": LeaveRequestStatus.CANCELLED, "cancellation_reason": cancellation_reason},
        comments=cancellation_reason,
        actor_user_id=actor_user_id,
        actor_email=actor_email,
    )

    publish_leave_event(
        LeaveCancelled(
            event_id=str(uuid.uuid4()),
            event_type="LEAVE_CANCELLED",
            organization_id=str(leave_request.organization_id),
            employee_id=str(leave_request.employee_id),
            leave_type_id=str(leave_request.leave_type_id),
            request_id=str(leave_request.id),
            cancellation_reason=cancellation_reason,
        )
    )

    logger.info("LeaveRequest %s cancelled.", leave_request.id)
    return leave_request


@transaction.atomic
def withdraw_leave_request(
    *,
    leave_request: LeaveRequest,
    actor_user_id: str = "",
    actor_email: str = "",
) -> LeaveRequest:
    """Withdraw a LeaveRequest by employee before approval."""
    if leave_request.status not in [LeaveRequestStatus.DRAFT, LeaveRequestStatus.SUBMITTED, LeaveRequestStatus.PENDING]:
        raise LeavePolicyValidationError(f"Cannot withdraw request with status '{leave_request.status}'.")

    prev_status = leave_request.status
    leave_request.status = LeaveRequestStatus.WITHDRAWN
    leave_request.save(update_fields=["status", "updated_at"])

    LeaveRequestHistory.objects.create(
        leave_request=leave_request,
        action="WITHDRAWN",
        previous_state={"status": prev_status},
        new_state={"status": LeaveRequestStatus.WITHDRAWN},
        comments="Withdrawn by applicant employee.",
        actor_user_id=actor_user_id,
        actor_email=actor_email,
    )

    publish_leave_event(
        LeaveWithdrawn(
            event_id=str(uuid.uuid4()),
            event_type="LEAVE_WITHDRAWN",
            organization_id=str(leave_request.organization_id),
            employee_id=str(leave_request.employee_id),
            leave_type_id=str(leave_request.leave_type_id),
            request_id=str(leave_request.id),
        )
    )

    logger.info("LeaveRequest %s withdrawn by employee.", leave_request.id)
    return leave_request


@transaction.atomic
def modify_leave_request(
    *,
    leave_request: LeaveRequest,
    new_start_date: date | None = None,
    new_end_date: date | None = None,
    new_reason: str = "",
    actor_user_id: str = "",
    actor_email: str = "",
) -> LeaveRequest:
    """Modify a pending or draft LeaveRequest with revision history logging."""
    if leave_request.status not in [LeaveRequestStatus.DRAFT, LeaveRequestStatus.SUBMITTED, LeaveRequestStatus.PENDING]:
        raise LeavePolicyValidationError(f"Cannot modify request with status '{leave_request.status}'.")

    prev_state = {
        "start_date": leave_request.start_date.isoformat(),
        "end_date": leave_request.end_date.isoformat(),
        "total_days": float(leave_request.total_days),
        "reason": leave_request.reason,
    }

    start = new_start_date or leave_request.start_date
    end = new_end_date or leave_request.end_date

    if start > end:
        raise LeavePolicyValidationError("Start date cannot be after end date.")

    # Overlap check excluding current request
    if check_leave_overlap(employee_id=leave_request.employee_id, start_date=start, end_date=end, exclude_request_id=leave_request.id):
        raise LeavePolicyValidationError("Overlapping leave request exists for the modified date window.")

    working_info = calculate_working_days_between(
        organization_id=leave_request.organization_id, start_date=start, end_date=end, employee=leave_request.employee
    )
    new_days = Decimal(str(working_info["working_days"]))
    if leave_request.is_half_day:
        new_days = Decimal("0.50")

    leave_request.start_date = start
    leave_request.end_date = end
    leave_request.total_days = new_days
    if new_reason:
        leave_request.reason = new_reason
    leave_request.save()

    new_state = {
        "start_date": start.isoformat(),
        "end_date": end.isoformat(),
        "total_days": float(new_days),
        "reason": leave_request.reason,
    }

    LeaveRequestHistory.objects.create(
        leave_request=leave_request,
        action="MODIFIED",
        modification_type=ModificationType.DATE_CHANGE if (new_start_date or new_end_date) else ModificationType.REASON_CHANGE,
        previous_state=prev_state,
        new_state=new_state,
        comments="Leave request modified by applicant.",
        actor_user_id=actor_user_id,
        actor_email=actor_email,
    )

    publish_leave_event(
        LeaveModified(
            event_id=str(uuid.uuid4()),
            event_type="LEAVE_MODIFIED",
            organization_id=str(leave_request.organization_id),
            employee_id=str(leave_request.employee_id),
            leave_type_id=str(leave_request.leave_type_id),
            request_id=str(leave_request.id),
            modification_type="DATE_CHANGE" if (new_start_date or new_end_date) else "REASON_CHANGE",
        )
    )

    logger.info("LeaveRequest %s modified.", leave_request.id)
    return leave_request


@transaction.atomic
def create_approval_delegation(
    *,
    organization: Organization,
    delegator: Employee,
    delegatee: Employee,
    start_date: date,
    end_date: date,
    reason: str = "",
) -> ApprovalDelegation:
    """Create an ApprovalDelegation rule assigning temporary/backup approver."""
    if delegator.id == delegatee.id:
        raise LeavePolicyValidationError("Delegator cannot delegate approval authority to self.")

    if start_date > end_date:
        raise LeavePolicyValidationError("Delegation start date cannot be after end date.")

    delegation = ApprovalDelegation.objects.create(
        organization=organization,
        delegator=delegator,
        delegatee=delegatee,
        start_date=start_date,
        end_date=end_date,
        reason=reason,
    )

    logger.info("ApprovalDelegation created: %s -> %s (%s to %s)", delegator.employee_id, delegatee.employee_id, start_date, end_date)
    return delegation


# ── Leave Analytics & Compliance Engine Services ─────────────────────────────


def generate_leave_analytics_report(
    *,
    organization: Organization,
    scope: str,
    target_id: str = "",
    start_date: date,
    end_date: date,
) -> dict:
    """Generate leave analytics for the specified scope and publish domain event."""
    from . import selectors

    scope_upper = scope.upper()
    if scope_upper == "EMPLOYEE":
        data = selectors.get_employee_leave_analytics(employee_id=target_id)
    elif scope_upper == "ORGANIZATION":
        data = selectors.get_organization_leave_analytics(
            organization_id=organization.id, start_date=start_date, end_date=end_date,
        )
    elif scope_upper == "KPIS":
        data = selectors.calculate_leave_kpis(
            organization_id=organization.id, start_date=start_date, end_date=end_date,
        )
    else:
        data = selectors.get_organization_leave_analytics(
            organization_id=organization.id, start_date=start_date, end_date=end_date,
        )

    publish_leave_event(
        LeaveAnalyticsGenerated(
            event_id=str(uuid.uuid4()),
            event_type="LEAVE_ANALYTICS_GENERATED",
            organization_id=str(organization.id),
            scope=scope_upper,
            target_id=target_id,
        )
    )

    logger.info("Leave analytics report generated: scope=%s, org=%s", scope_upper, organization.code)
    return data


def generate_leave_export_csv(
    *,
    organization: Organization,
    report_type: str,
    start_date: date,
    end_date: date,
) -> str:
    """Generate CSV content string for leave reports and publish export event."""
    import csv
    import io
    from . import selectors

    output = io.StringIO()
    writer = csv.writer(output)

    report_upper = report_type.upper()
    if report_upper == "UTILIZATION":
        kpis = selectors.calculate_leave_kpis(
            organization_id=organization.id, start_date=start_date, end_date=end_date,
        )
        writer.writerow(["KPI Metric", "Value"])
        writer.writerow(["Utilization %", kpis["utilization_percentage"]])
        writer.writerow(["Rejection %", kpis["rejection_percentage"]])
        writer.writerow(["Cancellation %", kpis["cancellation_percentage"]])
        writer.writerow(["Org Availability %", kpis["organization_availability_percentage"]])
        writer.writerow(["Avg Approval Time (hrs)", kpis["average_approval_time_hours"]])
    elif report_upper == "COMPLIANCE":
        compliance = selectors.get_leave_compliance_audit(
            organization_id=organization.id, start_date=start_date, end_date=end_date,
        )
        writer.writerow(["Compliance Metric", "Value"])
        writer.writerow(["Compliance Score", compliance["compliance_score"]])
        writer.writerow(["Risk Level", compliance["risk_level"]])
        writer.writerow(["Negative Balance Violations", compliance["negative_balance_violations"]])
        writer.writerow(["Attachment Violations", compliance["attachment_policy_violations"]])
        writer.writerow(["Total Violations", compliance["total_policy_violations"]])
    else:
        org_stats = selectors.get_organization_leave_analytics(
            organization_id=organization.id, start_date=start_date, end_date=end_date,
        )
        writer.writerow(["Metric", "Value"])
        for key, val in org_stats.items():
            writer.writerow([key, val])

    file_name = f"leave_{report_upper.lower()}_{organization.code}_{start_date}_{end_date}.csv"

    publish_leave_event(
        LeaveExportGenerated(
            event_id=str(uuid.uuid4()),
            event_type="LEAVE_EXPORT_GENERATED",
            organization_id=str(organization.id),
            export_format="CSV",
            file_name=file_name,
        )
    )

    logger.info("Leave CSV export generated: %s for Org %s", file_name, organization.code)
    return output.getvalue()


def audit_leave_compliance(
    *,
    organization: Organization,
    start_date: date,
    end_date: date,
) -> dict:
    """Run leave compliance audit and publish compliance calculated event."""
    from . import selectors

    compliance = selectors.get_leave_compliance_audit(
        organization_id=organization.id, start_date=start_date, end_date=end_date,
    )

    publish_leave_event(
        LeaveComplianceCalculated(
            event_id=str(uuid.uuid4()),
            event_type="LEAVE_COMPLIANCE_CALCULATED",
            organization_id=str(organization.id),
            compliance_score=compliance["compliance_score"],
            total_violations=compliance["total_policy_violations"],
        )
    )

    logger.info(
        "Leave compliance audit completed: Org %s, Score %.2f, Violations %d",
        organization.code,
        compliance["compliance_score"],
        compliance["total_policy_violations"],
    )
    return compliance

