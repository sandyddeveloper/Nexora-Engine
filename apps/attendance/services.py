"""Domain state mutation service functions for the Attendance Foundation Engine."""

import logging
import uuid
from datetime import date, datetime, timezone
from decimal import Decimal

from django.db import transaction

from apps.employees.models import Employee, EmploymentStatus
from apps.organizations.models import Organization

from .events import (
    AttendanceCalculated,
    AttendanceConfigurationChanged,
    AttendanceCorrectionProcessed,
    AttendanceCorrectionSubmitted,
    AttendanceLocked,
    AttendancePolicyAssigned,
    AttendanceRecordCreated,
    AttendanceUnlocked,
    BreakEnded,
    BreakStarted,
    EmployeeCheckedIn,
    EmployeeCheckedOut,
    publish_attendance_event,
)
from .exceptions import (
    AttendanceBreakError,
    AttendanceCheckInError,
    AttendanceCheckOutError,
    AttendanceCorrectionError,
    AttendanceDuplicateError,
    AttendanceLockedError,
    AttendancePolicyValidationError,
)
from .models import (
    ApprovalStatus,
    AttendanceBreak,
    AttendanceConfiguration,
    AttendanceCorrectionRequest,
    AttendanceEvent,
    AttendancePolicy,
    AttendanceRecord,
    AttendanceSession,
    AttendanceStatus,
    BreakType,
    CorrectionStatus,
)
from .selectors import get_active_break, get_active_session, get_effective_attendance_configuration

logger = logging.getLogger("nexora.attendance.services")


@transaction.atomic
def create_attendance_policy(
    *,
    organization: Organization,
    name: str,
    code: str,
    grace_time_minutes: int = 15,
    late_threshold_minutes: int = 30,
    early_exit_threshold_minutes: int = 30,
    minimum_working_hours: Decimal = Decimal("4.00"),
    full_day_working_hours: Decimal = Decimal("8.00"),
    maximum_working_hours: Decimal = Decimal("12.00"),
    overtime_allowed: bool = True,
    half_day_allowed: bool = True,
    auto_checkout_enabled: bool = False,
    approval_required: bool = True,
    is_default: bool = False,
) -> AttendancePolicy:
    """Create a new AttendancePolicy for an organization."""
    if is_default:
        AttendancePolicy.objects.filter(organization=organization, is_default=True).update(is_default=False)

    policy = AttendancePolicy.objects.create(
        organization=organization,
        name=name,
        code=code.upper(),
        grace_time_minutes=grace_time_minutes,
        late_threshold_minutes=late_threshold_minutes,
        early_exit_threshold_minutes=early_exit_threshold_minutes,
        minimum_working_hours=minimum_working_hours,
        full_day_working_hours=full_day_working_hours,
        maximum_working_hours=maximum_working_hours,
        overtime_allowed=overtime_allowed,
        half_day_allowed=half_day_allowed,
        auto_checkout_enabled=auto_checkout_enabled,
        approval_required=approval_required,
        is_default=is_default,
    )

    logger.info("Attendance Policy created: %s (%s) for Org %s", policy.name, policy.code, organization.code)
    return policy


@transaction.atomic
def set_attendance_configuration(
    *,
    organization: Organization,
    default_policy: AttendancePolicy,
    branch=None,
    department=None,
    team=None,
    allow_future_attendance: bool = False,
    allow_manual_entry: bool = True,
    allow_wfh_request: bool = True,
    lock_attendance_days: int = 30,
) -> AttendanceConfiguration:
    """Create or update AttendanceConfiguration settings at Organization, Branch, Dept, or Team level."""
    if default_policy.organization_id != organization.id:
        raise AttendancePolicyValidationError("Default policy must belong to target organization.")

    cfg, created = AttendanceConfiguration.objects.update_or_create(
        organization=organization,
        branch=branch,
        department=department,
        team=team,
        defaults={
            "default_policy": default_policy,
            "allow_future_attendance": allow_future_attendance,
            "allow_manual_entry": allow_manual_entry,
            "allow_wfh_request": allow_wfh_request,
            "lock_attendance_days": lock_attendance_days,
        },
    )

    publish_attendance_event(
        AttendanceConfigurationChanged(
            event_id=str(uuid.uuid4()),
            event_type="ATTENDANCE_CONFIGURATION_CHANGED",
            attendance_record_id="",
            employee_id="",
            organization_id=str(organization.id),
            configuration_id=str(cfg.id),
        )
    )

    logger.info("Attendance Configuration updated for Org %s", organization.code)
    return cfg


@transaction.atomic
def create_attendance_record(
    *,
    employee: Employee,
    attendance_date: date,
    status: str = AttendanceStatus.PRESENT,
    source: str = "WEB",
    work_location: str = "",
    working_hours: Decimal = Decimal("0.00"),
    break_hours: Decimal = Decimal("0.00"),
    overtime_hours: Decimal = Decimal("0.00"),
    remarks: str = "",
    actor_user_id: str = "",
    actor_email: str = "",
) -> AttendanceRecord:
    """Create an AttendanceRecord enforcing duplicate checks, organizational state, and policy resolution."""
    if not employee.organization.is_active:
        raise AttendancePolicyValidationError("Cannot log attendance for inactive organization.")

    if employee.employment_status in [EmploymentStatus.ARCHIVED, EmploymentStatus.EXITED]:
        raise AttendancePolicyValidationError("Cannot log attendance for exited or archived employees.")

    if AttendanceRecord.objects.filter(employee=employee, attendance_date=attendance_date).exists():
        raise AttendanceDuplicateError(f"Attendance record already exists for {employee.display_name} on {attendance_date}.")

    cfg = get_effective_attendance_configuration(
        organization_id=employee.organization_id,
        branch_id=employee.branch_id,
        department_id=employee.department_id,
        team_id=employee.team_id,
    )

    policy = cfg.default_policy if cfg else None
    if not policy:
        from .selectors import get_default_attendance_policy
        policy = get_default_attendance_policy(organization_id=employee.organization_id)
        if not policy:
            raise AttendancePolicyValidationError("No active AttendancePolicy configured for organization.")

    if cfg and not cfg.allow_future_attendance and attendance_date > date.today():
        raise AttendancePolicyValidationError("Future attendance logging is disabled by configuration policy.")

    record = AttendanceRecord.objects.create(
        employee=employee,
        organization=employee.organization,
        branch=employee.branch,
        department=employee.department,
        designation=employee.designation,
        team=employee.team,
        shift=employee.shift,
        policy=policy,
        attendance_date=attendance_date,
        status=status,
        source=source,
        work_location=work_location or employee.work_location,
        approval_status=ApprovalStatus.APPROVED if not policy.approval_required else ApprovalStatus.PENDING,
        working_hours=working_hours,
        break_hours=break_hours,
        overtime_hours=overtime_hours,
        remarks=remarks,
    )

    AttendanceEvent.objects.create(
        attendance_record=record,
        event_type="CREATED",
        actor_user_id=actor_user_id,
        actor_email=actor_email,
        new_state={"status": status, "attendance_date": attendance_date.isoformat()},
        reason="Initial attendance record created.",
    )

    publish_attendance_event(
        AttendanceRecordCreated(
            event_id=str(uuid.uuid4()),
            event_type="ATTENDANCE_RECORD_CREATED",
            attendance_record_id=str(record.id),
            employee_id=str(employee.id),
            organization_id=str(employee.organization_id),
            attendance_date=attendance_date.isoformat(),
            status=status,
        )
    )

    logger.info("Attendance record created: %s (%s) on %s", employee.employee_id, status, attendance_date)
    return record


@transaction.atomic
def update_attendance_record(
    *,
    record: AttendanceRecord,
    status: str | None = None,
    working_hours: Decimal | None = None,
    remarks: str = "",
    actor_user_id: str = "",
    actor_email: str = "",
) -> AttendanceRecord:
    """Update an existing AttendanceRecord enforcing lock validation and recording audit event trail."""
    if record.is_locked:
        raise AttendanceLockedError("Cannot modify locked attendance record.")

    prev_status = record.status
    if status:
        record.status = status
    if working_hours is not None:
        record.working_hours = working_hours
    if remarks:
        record.remarks = remarks

    record.save()

    AttendanceEvent.objects.create(
        attendance_record=record,
        event_type="CORRECTED",
        actor_user_id=actor_user_id,
        actor_email=actor_email,
        previous_state={"status": prev_status},
        new_state={"status": record.status, "working_hours": str(record.working_hours)},
        reason=remarks or "Attendance record updated.",
    )

    logger.info("Attendance record updated: Record %s -> Status: %s", record.id, record.status)
    return record


@transaction.atomic
def lock_attendance_records(
    *,
    organization_id: str | uuid.UUID,
    lock_up_to_date: date,
    actor_user_id: str = "",
) -> int:
    """Lock all attendance records for an organization up to specified calendar date."""
    updated_count = AttendanceRecord.objects.filter(
        organization_id=organization_id,
        attendance_date__lte=lock_up_to_date,
        is_locked=False,
    ).update(is_locked=True)

    publish_attendance_event(
        AttendanceLocked(
            event_id=str(uuid.uuid4()),
            event_type="ATTENDANCE_LOCKED",
            attendance_record_id="",
            employee_id="",
            organization_id=str(organization_id),
            lock_date=lock_up_to_date.isoformat(),
        )
    )

    logger.info("Locked %d attendance records for Org %s up to %s", updated_count, organization_id, lock_up_to_date)
    return updated_count


@transaction.atomic
def unlock_attendance_records(
    *,
    organization_id: str | uuid.UUID,
    unlock_up_to_date: date,
    actor_user_id: str = "",
) -> int:
    """Unlock attendance records for an organization up to specified date for corrections."""
    updated_count = AttendanceRecord.objects.filter(
        organization_id=organization_id,
        attendance_date__lte=unlock_up_to_date,
        is_locked=True,
    ).update(is_locked=False)

    publish_attendance_event(
        AttendanceUnlocked(
            event_id=str(uuid.uuid4()),
            event_type="ATTENDANCE_UNLOCKED",
            attendance_record_id="",
            employee_id="",
            organization_id=str(organization_id),
            unlock_date=unlock_up_to_date.isoformat(),
        )
    )

    logger.info("Unlocked %d attendance records for Org %s up to %s", updated_count, organization_id, unlock_up_to_date)
    return updated_count


# ── Check-In Engine ───────────────────────────────────────────────────────────


@transaction.atomic
def check_in_employee(
    *,
    employee: Employee,
    check_in_time: datetime | None = None,
    source: str = "WEB",
    work_location: str = "",
    remarks: str = "",
    actor_user_id: str = "",
    actor_email: str = "",
) -> AttendanceSession:
    """Execute Check-In workflow creating/updating daily AttendanceRecord and opening an active session."""
    now_dt = check_in_time or datetime.now(timezone.utc)
    att_date = now_dt.date()

    if get_active_session(employee_id=employee.id):
        raise AttendanceCheckInError(f"Employee {employee.display_name} already has an active check-in session.")

    try:
        record = AttendanceRecord.objects.get(employee=employee, attendance_date=att_date)
        if record.is_locked:
            raise AttendanceLockedError("Cannot check-in for locked attendance date.")
    except AttendanceRecord.DoesNotExist:
        record = create_attendance_record(
            employee=employee,
            attendance_date=att_date,
            status=AttendanceStatus.PRESENT,
            source=source,
            work_location=work_location,
            remarks=remarks,
            actor_user_id=actor_user_id,
            actor_email=actor_email,
        )

    session = AttendanceSession.objects.create(
        attendance_record=record,
        check_in=now_dt,
    )

    publish_attendance_event(
        EmployeeCheckedIn(
            event_id=str(uuid.uuid4()),
            event_type="EMPLOYEE_CHECKED_IN",
            attendance_record_id=str(record.id),
            employee_id=str(employee.id),
            organization_id=str(employee.organization_id),
            check_in_time=now_dt.isoformat(),
            source=source,
        )
    )

    logger.info("Employee checked in: %s at %s", employee.employee_id, now_dt.isoformat())
    return session


# ── Check-Out Engine ──────────────────────────────────────────────────────────


@transaction.atomic
def check_out_employee(
    *,
    employee: Employee,
    check_out_time: datetime | None = None,
    force: bool = False,
    remarks: str = "",
    actor_user_id: str = "",
    actor_email: str = "",
) -> AttendanceSession:
    """Execute Check-Out workflow closing active session and triggering daily metrics calculation."""
    session = get_active_session(employee_id=employee.id)
    if not session:
        raise AttendanceCheckOutError(f"No active check-in session found for employee {employee.display_name}.")

    # Auto-close any open break intervals
    active_brk = get_active_break(session_id=session.id)
    if active_brk:
        end_break(employee=employee, end_time=check_out_time)

    now_dt = check_out_time or datetime.now(timezone.utc)
    if now_dt < session.check_in:
        raise AttendanceCheckOutError("Check-out time cannot be earlier than check-in time.")

    session.check_out = now_dt
    duration_mins = int((now_dt - session.check_in).total_seconds() // 60)
    session.session_duration_minutes = duration_mins
    session.is_auto_checked_out = force
    session.save()

    record = session.attendance_record
    calculate_daily_attendance(record=record)

    publish_attendance_event(
        EmployeeCheckedOut(
            event_id=str(uuid.uuid4()),
            event_type="EMPLOYEE_CHECKED_OUT",
            attendance_record_id=str(record.id),
            employee_id=str(employee.id),
            organization_id=str(employee.organization_id),
            check_out_time=now_dt.isoformat(),
            working_duration_minutes=duration_mins,
        )
    )

    logger.info("Employee checked out: %s at %s (%d mins)", employee.employee_id, now_dt.isoformat(), duration_mins)
    return session


# ── Break Management Engine ───────────────────────────────────────────────────


@transaction.atomic
def start_break(
    *,
    employee: Employee,
    break_type: str = BreakType.LUNCH,
    start_time: datetime | None = None,
    is_paid: bool = False,
) -> AttendanceBreak:
    """Start a break interval associated with employee's active session."""
    session = get_active_session(employee_id=employee.id)
    if not session:
        raise AttendanceBreakError("Cannot start break without an active check-in session.")

    if get_active_break(session_id=session.id):
        raise AttendanceBreakError("An active break session is already in progress.")

    now_dt = start_time or datetime.now(timezone.utc)
    brk = AttendanceBreak.objects.create(
        session=session,
        break_type=break_type,
        start_time=now_dt,
        is_paid=is_paid,
    )

    publish_attendance_event(
        BreakStarted(
            event_id=str(uuid.uuid4()),
            event_type="BREAK_STARTED",
            attendance_record_id=str(session.attendance_record_id),
            employee_id=str(employee.id),
            organization_id=str(employee.organization_id),
            break_type=break_type,
            start_time=now_dt.isoformat(),
        )
    )

    logger.info("Break started: %s (%s) at %s", employee.employee_id, break_type, now_dt.isoformat())
    return brk


@transaction.atomic
def end_break(
    *,
    employee: Employee,
    end_time: datetime | None = None,
) -> AttendanceBreak:
    """End current active break interval."""
    session = get_active_session(employee_id=employee.id)
    if not session:
        raise AttendanceBreakError("No active check-in session found for employee.")

    brk = get_active_break(session_id=session.id)
    if not brk:
        raise AttendanceBreakError("No active break in progress to resume work.")

    now_dt = end_time or datetime.now(timezone.utc)
    if now_dt < brk.start_time:
        raise AttendanceBreakError("Break end time cannot be earlier than break start time.")

    brk.end_time = now_dt
    duration_mins = int((now_dt - brk.start_time).total_seconds() // 60)
    brk.duration_minutes = duration_mins
    brk.save()

    publish_attendance_event(
        BreakEnded(
            event_id=str(uuid.uuid4()),
            event_type="BREAK_ENDED",
            attendance_record_id=str(session.attendance_record_id),
            employee_id=str(employee.id),
            organization_id=str(employee.organization_id),
            break_type=brk.break_type,
            end_time=now_dt.isoformat(),
            duration_minutes=duration_mins,
        )
    )

    logger.info("Break ended: %s (%s) duration: %d mins", employee.employee_id, brk.break_type, duration_mins)
    return brk


# ── Attendance Calculation Engine ─────────────────────────────────────────────


@transaction.atomic
def calculate_daily_attendance(*, record: AttendanceRecord) -> AttendanceRecord:
    """Calculate total working hours, break hours, overtime, and status rules for an AttendanceRecord."""
    sessions = record.sessions.all()

    total_session_minutes = 0
    total_unpaid_break_minutes = 0
    total_break_minutes = 0

    for s in sessions:
        if s.check_out:
            session_mins = int((s.check_out - s.check_in).total_seconds() // 60)
            total_session_minutes += session_mins

        for b in s.breaks.all():
            if b.end_time:
                b_mins = int((b.end_time - b.start_time).total_seconds() // 60)
                total_break_minutes += b_mins
                if not b.is_paid:
                    total_unpaid_break_minutes += b_mins

    net_working_minutes = max(0, total_session_minutes - total_unpaid_break_minutes)

    net_working_hours = Decimal(str(round(net_working_minutes / 60.0, 2)))
    break_hours = Decimal(str(round(total_break_minutes / 60.0, 2)))

    record.working_hours = net_working_hours
    record.break_hours = break_hours

    policy = record.policy
    if policy:
        if net_working_hours >= policy.full_day_working_hours:
            record.status = AttendanceStatus.PRESENT
        elif policy.half_day_allowed and net_working_hours >= policy.minimum_working_hours:
            record.status = AttendanceStatus.HALF_DAY
        else:
            record.status = AttendanceStatus.ABSENT

        if policy.overtime_allowed and net_working_hours > policy.full_day_working_hours:
            record.overtime_hours = net_working_hours - policy.full_day_working_hours

    record.save()

    publish_attendance_event(
        AttendanceCalculated(
            event_id=str(uuid.uuid4()),
            event_type="ATTENDANCE_CALCULATED",
            attendance_record_id=str(record.id),
            employee_id=str(record.employee_id),
            organization_id=str(record.organization_id),
            working_hours=str(net_working_hours),
            calculated_status=record.status,
        )
    )

    logger.info("Attendance calculated for Record %s: %s hrs -> Status: %s", record.id, net_working_hours, record.status)
    return record


# ── Attendance Correction Engine ──────────────────────────────────────────────


@transaction.atomic
def submit_attendance_correction(
    *,
    record: AttendanceRecord,
    requested_by: Employee,
    requested_check_in: datetime | None = None,
    requested_check_out: datetime | None = None,
    requested_status: str = AttendanceStatus.PRESENT,
    reason: str,
) -> AttendanceCorrectionRequest:
    """Submit a formal attendance correction request."""
    if record.is_locked:
        raise AttendanceCorrectionError("Cannot submit correction request for locked attendance record.")

    if AttendanceCorrectionRequest.objects.filter(attendance_record=record, status=CorrectionStatus.PENDING).exists():
        raise AttendanceCorrectionError("A pending correction request already exists for this attendance record.")

    request_obj = AttendanceCorrectionRequest.objects.create(
        attendance_record=record,
        requested_by=requested_by,
        requested_check_in=requested_check_in,
        requested_check_out=requested_check_out,
        requested_status=requested_status,
        reason=reason,
        status=CorrectionStatus.PENDING,
    )

    publish_attendance_event(
        AttendanceCorrectionSubmitted(
            event_id=str(uuid.uuid4()),
            event_type="ATTENDANCE_CORRECTION_SUBMITTED",
            attendance_record_id=str(record.id),
            employee_id=str(record.employee_id),
            organization_id=str(record.organization_id),
            correction_request_id=str(request_obj.id),
        )
    )

    logger.info("Attendance correction submitted for Record %s by %s", record.id, requested_by.employee_id)
    return request_obj


@transaction.atomic
def process_attendance_correction(
    *,
    correction_request: AttendanceCorrectionRequest,
    approve: bool = True,
    processed_by_id: str = "",
) -> AttendanceCorrectionRequest:
    """Approve or reject a pending attendance correction request."""
    if correction_request.status != CorrectionStatus.PENDING:
        raise AttendanceCorrectionError("Correction request is no longer pending.")

    record = correction_request.attendance_record
    if record.is_locked:
        raise AttendanceLockedError("Cannot process correction for locked attendance record.")

    if approve:
        correction_request.status = CorrectionStatus.APPROVED
        record.status = correction_request.requested_status
        record.save()
    else:
        correction_request.status = CorrectionStatus.REJECTED

    correction_request.processed_by_id = processed_by_id
    correction_request.processed_at = datetime.now(timezone.utc)
    correction_request.save()

    publish_attendance_event(
        AttendanceCorrectionProcessed(
            event_id=str(uuid.uuid4()),
            event_type="ATTENDANCE_CORRECTION_PROCESSED",
            attendance_record_id=str(record.id),
            employee_id=str(record.employee_id),
            organization_id=str(record.organization_id),
            correction_request_id=str(correction_request.id),
            approval_status=correction_request.status,
        )
    )

    logger.info("Attendance correction processed: Request %s -> Status: %s", correction_request.id, correction_request.status)
    return correction_request


# ── Bulk Attendance Engine ────────────────────────────────────────────────────


@transaction.atomic
def bulk_import_attendance(
    *,
    organization: Organization,
    records_data: list[dict],
    actor_user_id: str = "",
) -> dict:
    """Bulk import attendance records with atomic transaction rollback safety."""
    created_count = 0
    errors = []

    for idx, data in enumerate(records_data):
        emp_id = data.get("employee_id")
        att_date = data.get("attendance_date")
        status = data.get("status", AttendanceStatus.PRESENT)

        from apps.employees.selectors import get_employee
        employee = get_employee(employee_id=emp_id)
        if not employee:
            errors.append(f"Row {idx+1}: Employee {emp_id} not found.")
            continue

        try:
            create_attendance_record(
                employee=employee,
                attendance_date=att_date,
                status=status,
                source="IMPORT",
                working_hours=data.get("working_hours", Decimal("8.00")),
                remarks=data.get("remarks", "Bulk imported"),
                actor_user_id=actor_user_id,
            )
            created_count += 1
        except Exception as e:
            errors.append(f"Row {idx+1}: {str(e)}")

    logger.info("Bulk attendance import completed for Org %s: %d created, %d errors", organization.code, created_count, len(errors))
    return {"created_count": created_count, "errors": errors}


# ── Attendance Analytics & Report Services ────────────────────────────────────


def generate_attendance_analytics_report(
    *,
    organization: Organization,
    level: str,
    target_id: str,
    start_date: date,
    end_date: date,
) -> dict:
    """Generate an attendance analytics report at the specified organizational hierarchy level."""
    from .selectors import (
        get_branch_attendance_analytics,
        get_department_attendance_analytics,
        get_employee_attendance_analytics,
        get_organization_attendance_analytics,
        get_team_attendance_analytics,
    )
    from .events import AttendanceAnalyticsGenerated, publish_attendance_event

    level_upper = level.upper()

    if level_upper == "EMPLOYEE":
        analytics = get_employee_attendance_analytics(employee_id=target_id, start_date=start_date, end_date=end_date)
    elif level_upper == "TEAM":
        analytics = get_team_attendance_analytics(team_id=target_id, start_date=start_date, end_date=end_date)
    elif level_upper == "DEPARTMENT":
        analytics = get_department_attendance_analytics(department_id=target_id, start_date=start_date, end_date=end_date)
    elif level_upper == "BRANCH":
        analytics = get_branch_attendance_analytics(branch_id=target_id, start_date=start_date, end_date=end_date)
    elif level_upper == "ORGANIZATION":
        analytics = get_organization_attendance_analytics(organization_id=target_id, start_date=start_date, end_date=end_date)
    else:
        from .exceptions import AttendanceAnalyticsError
        raise AttendanceAnalyticsError(f"Invalid analytics level: {level}. Expected EMPLOYEE|TEAM|DEPARTMENT|BRANCH|ORGANIZATION.")

    publish_attendance_event(
        AttendanceAnalyticsGenerated(
            event_id=str(uuid.uuid4()),
            event_type="ATTENDANCE_ANALYTICS_GENERATED",
            attendance_record_id="",
            employee_id="",
            organization_id=str(organization.id),
            level=level_upper,
            target_id=target_id,
        )
    )

    logger.info("Attendance analytics report generated: Level=%s, Target=%s, Org=%s", level_upper, target_id, organization.code)
    return analytics


def export_attendance_report_csv(
    *,
    organization_id: str | uuid.UUID,
    start_date: date,
    end_date: date,
) -> list[dict]:
    """Export attendance records as a list of flat dictionaries suitable for CSV serialization."""
    import csv
    import io

    from .events import AttendanceExportGenerated, publish_attendance_event

    records = AttendanceRecord.objects.filter(
        organization_id=organization_id,
        attendance_date__gte=start_date,
        attendance_date__lte=end_date,
    ).select_related("employee", "branch", "department", "designation", "shift", "policy").order_by("attendance_date", "employee__first_name")

    rows = []
    for r in records:
        rows.append({
            "employee_id": r.employee.employee_id,
            "employee_name": r.employee.display_name,
            "branch": r.branch.name if r.branch else "",
            "department": r.department.name if r.department else "",
            "designation": r.designation.name if r.designation else "",
            "shift": r.shift.name if r.shift else "",
            "attendance_date": r.attendance_date.isoformat(),
            "status": r.status,
            "source": r.source,
            "working_hours": str(r.working_hours),
            "break_hours": str(r.break_hours),
            "overtime_hours": str(r.overtime_hours),
            "is_locked": r.is_locked,
            "remarks": r.remarks,
        })

    publish_attendance_event(
        AttendanceExportGenerated(
            event_id=str(uuid.uuid4()),
            event_type="ATTENDANCE_EXPORT_GENERATED",
            attendance_record_id="",
            employee_id="",
            organization_id=str(organization_id),
            format="CSV",
        )
    )

    logger.info("Attendance CSV export generated: %d records for Org %s (%s to %s)", len(rows), organization_id, start_date, end_date)
    return rows


