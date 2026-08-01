"""Domain state mutation service functions for the Employee Lifecycle Engine."""

import logging
import uuid
from datetime import date, timedelta
from typing import Any, Dict

from django.db import transaction

from apps.organizations.models import Branch, Department, Designation, Organization, Shift, Team
from apps.organizations.services import check_organization_limit

from .constants import EMPLOYEE_LIFECYCLE_TRANSITIONS, MAX_HIERARCHY_DEPTH
from .events import (
    EmployeeAssignedToTeam,
    EmployeeConfirmedEvent,
    EmployeeExitedEvent,
    EmployeeJoinedEvent,
    EmployeePromotedEvent,
    EmployeeResignedEvent,
    EmployeeSuspendedEvent,
    EmployeeTransferredBranch,
    EmployeeTransferredDepartment,
    EmployeeTransferredEvent,
    HierarchyUpdated,
    ManagerAssigned,
    ManagerChanged,
    ShiftAssigned,
    WorkLocationChanged,
    publish_employee_event,
)
from .exceptions import (
    CircularReportingError,
    EmployeeHierarchyError,
    EmployeeResignationError,
    InvalidEmployeeLifecycleTransitionError,
    MaxHierarchyDepthExceededError,
    WorkforceAssignmentError,
)
from .models import (
    AssignmentType,
    Certification,
    Education,
    EmergencyContact,
    Employee,
    EmployeeAuditEvent,
    EmployeeIdentifier,
    EmployeeProfile,
    EmployeeResignation,
    EmploymentHistory,
    EmploymentStatus,
    Experience,
    ManagerAssignment,
    ManagerType,
    Skill,
    WorkLocationType,
    WorkforceAssignment,
)

logger = logging.getLogger("nexora.employees")


# ── Audit Logger Service ───────────────────────────────────────────────────


def record_employee_audit_event(
    *,
    employee: Employee,
    event_type: str,
    user_id: str = "",
    user_email: str = "",
    ip_address: str | None = None,
    request_id: str = "",
    previous_state: Dict[str, Any] | None = None,
    new_state: Dict[str, Any] | None = None,
    metadata: Dict[str, Any] | None = None,
) -> EmployeeAuditEvent:
    """Record a structured audit trail entry for an employee lifecycle mutation."""
    return EmployeeAuditEvent.objects.create(
        employee=employee,
        event_type=event_type,
        user_id=user_id,
        user_email=user_email,
        ip_address=ip_address,
        request_id=request_id,
        previous_state=previous_state or {},
        new_state=new_state or {},
        metadata=metadata or {},
    )


# ── Reporting Hierarchy Guards ─────────────────────────────────────────────


def get_reporting_chain_depth(*, employee: Employee) -> int:
    """Calculate reporting manager chain depth from root organizational executive."""
    depth = 1
    current = employee.reporting_manager
    visited = {employee.id}
    while current:
        if current.id in visited:
            raise CircularReportingError("Circular reporting manager hierarchy loop detected.")
        visited.add(current.id)
        depth += 1
        current = current.reporting_manager
        if depth > MAX_HIERARCHY_DEPTH:
            raise MaxHierarchyDepthExceededError(
                f"Reporting manager hierarchy depth exceeds maximum threshold ({MAX_HIERARCHY_DEPTH})."
            )
    return depth


def validate_reporting_hierarchy(*, employee: Employee | None, reporting_manager: Employee | None) -> None:
    """Validate reporting manager hierarchy to prevent self-reporting or circular reporting chains."""
    if not reporting_manager:
        return
    if employee and employee.id == reporting_manager.id:
        raise CircularReportingError("An employee cannot be their own reporting manager.")

    current = reporting_manager.reporting_manager
    visited = {reporting_manager.id}
    if employee:
        visited.add(employee.id)

    chain_depth = 1
    while current:
        if current.id in visited:
            raise CircularReportingError("Circular reporting manager hierarchy loop detected.")
        visited.add(current.id)
        chain_depth += 1
        if chain_depth > MAX_HIERARCHY_DEPTH:
            raise MaxHierarchyDepthExceededError(
                f"Reporting manager hierarchy depth exceeds maximum limit ({MAX_HIERARCHY_DEPTH})."
            )
        current = current.reporting_manager


def validate_organization_hierarchy(
    *,
    organization: Organization,
    branch: Branch,
    department: Department,
    team: Team | None = None,
) -> None:
    """Validate that Branch, Department, and Team belong to the specified Organization."""
    if branch.organization_id != organization.id:
        raise EmployeeHierarchyError(
            f"Branch '{branch.name}' does not belong to organization '{organization.name}'."
        )
    if department.organization_id != organization.id or department.branch_id != branch.id:
        raise EmployeeHierarchyError(
            f"Department '{department.name}' does not belong to branch '{branch.name}'."
        )
    if team and (team.organization_id != organization.id or team.department_id != department.id):
        raise EmployeeHierarchyError(
            f"Team '{team.name}' does not belong to department '{department.name}'."
        )


# ── FSM Lifecycle State Machine Engine ──────────────────────────────────────


@transaction.atomic
def transition_employee_lifecycle_status(
    *,
    employee: Employee,
    target_status: str,
    reason: str = "",
    user_id: str = "",
    user_email: str = "",
    ip_address: str | None = None,
    request_id: str = "",
) -> Employee:
    """Transition Employee status adhering to strict 14-state FSM lifecycle rules."""
    current_status = employee.employment_status
    if current_status == target_status:
        return employee

    allowed = EMPLOYEE_LIFECYCLE_TRANSITIONS.get(current_status, set())
    if target_status not in allowed:
        raise InvalidEmployeeLifecycleTransitionError(
            f"Illegal lifecycle state transition for Employee {employee.employee_id}: "
            f"Cannot transition from '{current_status}' to '{target_status}'. "
            f"Allowed target statuses: {sorted(list(allowed))}."
        )

    previous_state = {"employment_status": current_status}
    employee.employment_status = target_status
    employee.save(update_fields=["employment_status", "updated_at"])
    new_state = {"employment_status": target_status, "reason": reason}

    record_employee_audit_event(
        employee=employee,
        event_type=f"EMPLOYEE_LIFECYCLE_TRANSITION_{target_status}",
        user_id=user_id,
        user_email=user_email,
        ip_address=ip_address,
        request_id=request_id,
        previous_state=previous_state,
        new_state=new_state,
    )

    # Publish Domain Events based on state
    if target_status == EmploymentStatus.CONFIRMED:
        publish_employee_event(
            EmployeeConfirmedEvent(
                event_id=str(uuid.uuid4()),
                event_type="EMPLOYEE_CONFIRMED",
                employee_id=str(employee.id),
                organization_id=str(employee.organization_id),
                confirmation_date=date.today().isoformat(),
            )
        )
    elif target_status == EmploymentStatus.SUSPENDED:
        publish_employee_event(
            EmployeeSuspendedEvent(
                event_id=str(uuid.uuid4()),
                event_type="EMPLOYEE_SUSPENDED",
                employee_id=str(employee.id),
                organization_id=str(employee.organization_id),
                reason=reason,
            )
        )

    logger.info("Employee %s lifecycle transitioned: %s -> %s", employee.employee_id, current_status, target_status)
    return employee


# ── Onboarding Engine ────────────────────────────────────────────────────────


@transaction.atomic
def create_employee(
    *,
    organization: Organization,
    branch: Branch,
    department: Department,
    designation: Designation,
    first_name: str,
    last_name: str,
    official_email: str,
    date_of_joining: date,
    team: Team | None = None,
    reporting_manager: Employee | None = None,
    user=None,
    shift: Shift | None = None,
    official_phone: str = "",
    employment_type: str = "FULL_TIME",
    employment_status: str = "PROBATION",
    probation_period_months: int = 3,
    work_location: str = "",
    gender: str = "",
    date_of_birth: date | None = None,
    blood_group: str = "",
    nationality: str = "",
    marital_status: str = "",
    personal_email: str = "",
    personal_phone: str = "",
    current_address: str = "",
    permanent_address: str = "",
    city: str = "",
    state: str = "",
    country: str = "",
    postal_code: str = "",
    pan_number: str = "",
    aadhaar_number: str = "",
    passport_number: str = "",
    user_id: str = "",
    user_email: str = "",
    ip_address: str | None = None,
    request_id: str = "",
) -> Employee:
    """Execute atomic Employee creation and Profile initialization workflow."""
    check_organization_limit(organization=organization, limit_type="max_employees")
    validate_organization_hierarchy(
        organization=organization, branch=branch, department=department, team=team
    )
    validate_reporting_hierarchy(employee=None, reporting_manager=reporting_manager)

    # Assign default shift if not explicitly provided
    if not shift:
        setting = getattr(organization, "setting", None)
        shift = getattr(setting, "default_shift", None)

    employee = Employee.objects.create(
        organization=organization,
        branch=branch,
        department=department,
        designation=designation,
        team=team,
        reporting_manager=reporting_manager,
        user=user,
        shift=shift,
        first_name=first_name,
        last_name=last_name,
        official_email=official_email.lower().strip(),
        official_phone=official_phone,
        employment_type=employment_type,
        employment_status=employment_status,
        date_of_joining=date_of_joining,
        probation_period_months=probation_period_months,
        work_location=work_location,
        gender=gender,
        date_of_birth=date_of_birth,
        blood_group=blood_group,
        nationality=nationality,
        marital_status=marital_status,
    )

    EmployeeProfile.objects.create(
        employee=employee,
        personal_email=personal_email,
        personal_phone=personal_phone,
        current_address=current_address,
        permanent_address=permanent_address,
        city=city,
        state=state,
        country=country,
        postal_code=postal_code,
        pan_number=pan_number,
        aadhaar_number=aadhaar_number,
        passport_number=passport_number,
    )

    # Initial Employment History Record
    EmploymentHistory.objects.create(
        employee=employee,
        change_type="JOINING",
        effective_date=date_of_joining,
        previous_data={},
        new_data={
            "branch": branch.name,
            "department": department.name,
            "designation": designation.name,
            "employment_status": employment_status,
        },
        remarks=f"Onboarded employee {employee.employee_id}",
    )

    # Audit Trail Entry
    record_employee_audit_event(
        employee=employee,
        event_type="EMPLOYEE_ONBOARDED",
        user_id=user_id,
        user_email=user_email,
        ip_address=ip_address,
        request_id=request_id,
        new_state={"employee_id": employee.employee_id, "official_email": employee.official_email},
    )

    # Publish Domain Event
    publish_employee_event(
        EmployeeJoinedEvent(
            event_id=str(uuid.uuid4()),
            event_type="EMPLOYEE_JOINED",
            employee_id=str(employee.id),
            organization_id=str(organization.id),
            employee_code=employee.employee_id,
            email=employee.official_email,
        )
    )

    logger.info("Employee created: %s (%s)", employee.display_name, employee.employee_id)
    return employee


# ── Probation & Confirmation Engine ───────────────────────────────────────────


@transaction.atomic
def confirm_employee_probation(
    *,
    employee: Employee,
    confirmation_date: date | None = None,
    remarks: str = "",
    user_id: str = "",
    user_email: str = "",
) -> Employee:
    """Confirm employee probation and update employment status to CONFIRMED."""
    if employee.employment_status in [EmploymentStatus.RESIGNED, EmploymentStatus.EXITED, EmploymentStatus.TERMINATED]:
        raise InvalidEmployeeLifecycleTransitionError(
            f"Cannot confirm probation for employee in state '{employee.employment_status}'."
        )

    conf_date = confirmation_date or date.today()
    previous_status = employee.employment_status
    employee.employment_status = EmploymentStatus.CONFIRMED
    employee.confirmation_date = conf_date
    employee.save(update_fields=["employment_status", "confirmation_date", "updated_at"])

    EmploymentHistory.objects.create(
        employee=employee,
        change_type="PROBATION_CONFIRMATION",
        effective_date=conf_date,
        previous_data={"employment_status": previous_status},
        new_data={"employment_status": EmploymentStatus.CONFIRMED, "confirmation_date": conf_date.isoformat()},
        remarks=remarks or "Probation confirmed successfully.",
    )

    record_employee_audit_event(
        employee=employee,
        event_type="EMPLOYEE_PROBATION_CONFIRMED",
        user_id=user_id,
        user_email=user_email,
        previous_state={"status": previous_status},
        new_state={"status": EmploymentStatus.CONFIRMED, "confirmation_date": conf_date.isoformat()},
    )

    publish_employee_event(
        EmployeeConfirmedEvent(
            event_id=str(uuid.uuid4()),
            event_type="EMPLOYEE_CONFIRMED",
            employee_id=str(employee.id),
            organization_id=str(employee.organization_id),
            confirmation_date=conf_date.isoformat(),
        )
    )

    logger.info("Employee %s probation confirmed on %s", employee.employee_id, conf_date)
    return employee


# ── Resignation & Exit Engine ─────────────────────────────────────────────────


@transaction.atomic
def submit_resignation(
    *,
    employee: Employee,
    resignation_date: date,
    notice_period_days: int = 30,
    requested_exit_date: date | None = None,
    reason: str = "",
    user_id: str = "",
    user_email: str = "",
) -> EmployeeResignation:
    """Submit a formal resignation request for an employee."""
    if employee.employment_status in [EmploymentStatus.EXITED, EmploymentStatus.TERMINATED, EmploymentStatus.ARCHIVED]:
        raise InvalidEmployeeLifecycleTransitionError(
            f"Cannot submit resignation for employee in state '{employee.employment_status}'."
        )

    # Check active pending resignation
    active_resignation = EmployeeResignation.objects.filter(
        employee=employee,
        status__in=[EmployeeResignation.ResignationStatus.PENDING, EmployeeResignation.ResignationStatus.APPROVED],
    ).exists()

    if active_resignation:
        raise EmployeeResignationError("An active resignation request already exists for this employee.")

    exit_date = requested_exit_date or (resignation_date + timedelta(days=notice_period_days))

    resignation = EmployeeResignation.objects.create(
        employee=employee,
        resignation_date=resignation_date,
        notice_period_days=notice_period_days,
        requested_exit_date=exit_date,
        status=EmployeeResignation.ResignationStatus.PENDING,
        reason=reason,
    )

    transition_employee_lifecycle_status(
        employee=employee,
        target_status=EmploymentStatus.RESIGNED,
        reason="Resignation submitted.",
        user_id=user_id,
        user_email=user_email,
    )

    publish_employee_event(
        EmployeeResignedEvent(
            event_id=str(uuid.uuid4()),
            event_type="EMPLOYEE_RESIGNED",
            employee_id=str(employee.id),
            organization_id=str(employee.organization_id),
            requested_exit_date=exit_date.isoformat(),
        )
    )

    logger.info("Resignation submitted for Employee: %s", employee.employee_id)
    return resignation


@transaction.atomic
def approve_resignation(
    *,
    resignation: EmployeeResignation,
    approved_exit_date: date | None = None,
    comments: str = "",
    processed_by_id: str = "",
) -> EmployeeResignation:
    """Approve a pending resignation request and set notice period status."""
    if resignation.status != EmployeeResignation.ResignationStatus.PENDING:
        raise EmployeeResignationError("Only pending resignation requests can be approved.")

    final_exit_date = approved_exit_date or resignation.requested_exit_date
    resignation.status = EmployeeResignation.ResignationStatus.APPROVED
    resignation.approved_exit_date = final_exit_date
    resignation.comments = comments
    resignation.processed_by_id = processed_by_id
    resignation.save()

    transition_employee_lifecycle_status(
        employee=resignation.employee,
        target_status=EmploymentStatus.NOTICE_PERIOD,
        reason=f"Resignation approved. Exit date: {final_exit_date}",
        user_id=processed_by_id,
    )

    logger.info("Resignation approved for Employee: %s", resignation.employee.employee_id)
    return resignation


@transaction.atomic
def withdraw_resignation(*, resignation: EmployeeResignation, remarks: str = "") -> EmployeeResignation:
    """Withdraw an active resignation request and restore employee status to ACTIVE."""
    if resignation.status not in [EmployeeResignation.ResignationStatus.PENDING, EmployeeResignation.ResignationStatus.APPROVED]:
        raise EmployeeResignationError("Only pending or approved resignations can be withdrawn.")

    resignation.status = EmployeeResignation.ResignationStatus.WITHDRAWN
    resignation.comments = f"Withdrawn: {remarks}" if remarks else "Resignation withdrawn by employee/HR."
    resignation.save()

    transition_employee_lifecycle_status(
        employee=resignation.employee,
        target_status=EmploymentStatus.ACTIVE,
        reason="Resignation withdrawn.",
    )

    logger.info("Resignation withdrawn for Employee: %s", resignation.employee.employee_id)
    return resignation


@transaction.atomic
def process_employee_exit(*, employee: Employee, exit_date: date, remarks: str = "") -> Employee:
    """Finalize employee exit processing and update status to EXITED."""
    previous_status = employee.employment_status
    employee.employment_status = EmploymentStatus.EXITED
    employee.save(update_fields=["employment_status", "updated_at"])

    EmploymentHistory.objects.create(
        employee=employee,
        change_type="EXIT",
        effective_date=exit_date,
        previous_data={"employment_status": previous_status},
        new_data={"employment_status": EmploymentStatus.EXITED, "exit_date": exit_date.isoformat()},
        remarks=remarks or "Employee exit processing finalized.",
    )

    publish_employee_event(
        EmployeeExitedEvent(
            event_id=str(uuid.uuid4()),
            event_type="EMPLOYEE_EXITED",
            employee_id=str(employee.id),
            organization_id=str(employee.organization_id),
            exit_date=exit_date.isoformat(),
        )
    )

    logger.info("Employee %s exit processing finalized on %s", employee.employee_id, exit_date)
    return employee


# ── Domain CRUD & Transfer Services ──────────────────────────────────────────


@transaction.atomic
def update_employee(*, employee: Employee, **fields) -> Employee:
    """Update editable fields on an Employee instance."""
    if "reporting_manager" in fields:
        validate_reporting_hierarchy(
            employee=employee, reporting_manager=fields["reporting_manager"]
        )

    allowed_fields = {
        "first_name",
        "last_name",
        "display_name",
        "official_phone",
        "employment_type",
        "employment_status",
        "probation_period_months",
        "confirmation_date",
        "work_location",
        "photo",
        "gender",
        "date_of_birth",
        "blood_group",
        "nationality",
        "marital_status",
        "shift",
        "team",
        "reporting_manager",
        "status",
    }

    for field, value in fields.items():
        if field in allowed_fields:
            setattr(employee, field, value)

    employee.save()
    logger.info("Employee updated: %s (%s)", employee.display_name, employee.employee_id)
    return employee


@transaction.atomic
def transfer_employee(
    *,
    employee: Employee,
    new_branch: Branch,
    new_department: Department,
    effective_date: date,
    remarks: str = "",
) -> Employee:
    """Transfer employee to a new Branch & Department and record EmploymentHistory audit entry."""
    validate_organization_hierarchy(
        organization=employee.organization, branch=new_branch, department=new_department
    )

    previous_data = {
        "branch_id": str(employee.branch_id),
        "branch_name": employee.branch.name,
        "department_id": str(employee.department_id),
        "department_name": employee.department.name,
    }

    employee.branch = new_branch
    employee.department = new_department
    employee.save(update_fields=["branch", "department", "updated_at"])

    new_data = {
        "branch_id": str(new_branch.id),
        "branch_name": new_branch.name,
        "department_id": str(new_department.id),
        "department_name": new_department.name,
    }

    EmploymentHistory.objects.create(
        employee=employee,
        change_type="TRANSFER",
        effective_date=effective_date,
        previous_data=previous_data,
        new_data=new_data,
        remarks=remarks or f"Transferred to {new_branch.name} - {new_department.name}",
    )

    publish_employee_event(
        EmployeeTransferredEvent(
            event_id=str(uuid.uuid4()),
            event_type="EMPLOYEE_TRANSFERRED",
            employee_id=str(employee.id),
            organization_id=str(employee.organization_id),
            new_branch_id=str(new_branch.id),
            new_department_id=str(new_department.id),
        )
    )

    logger.info("Employee transferred: %s to %s", employee.employee_id, new_branch.name)
    return employee


@transaction.atomic
def promote_employee(
    *,
    employee: Employee,
    new_designation: Designation,
    effective_date: date,
    remarks: str = "",
) -> Employee:
    """Promote employee to a new Designation and record EmploymentHistory audit entry."""
    previous_data = {
        "designation_id": str(employee.designation_id),
        "designation_name": employee.designation.name,
    }

    employee.designation = new_designation
    employee.save(update_fields=["designation", "updated_at"])

    new_data = {
        "designation_id": str(new_designation.id),
        "designation_name": new_designation.name,
    }

    EmploymentHistory.objects.create(
        employee=employee,
        change_type="PROMOTION",
        effective_date=effective_date,
        previous_data=previous_data,
        new_data=new_data,
        remarks=remarks or f"Promoted to {new_designation.name}",
    )

    publish_employee_event(
        EmployeePromotedEvent(
            event_id=str(uuid.uuid4()),
            event_type="EMPLOYEE_PROMOTED",
            employee_id=str(employee.id),
            organization_id=str(employee.organization_id),
            new_designation_id=str(new_designation.id),
        )
    )

    logger.info("Employee promoted: %s to %s", employee.employee_id, new_designation.name)
    return employee


@transaction.atomic
def soft_delete_employee(*, employee: Employee) -> Employee:
    """Soft delete an Employee record."""
    employee.delete(soft=True)
    logger.info("Employee soft deleted: %s (%s)", employee.display_name, employee.employee_id)
    return employee


@transaction.atomic
def restore_employee(*, employee: Employee) -> Employee:
    """Restore a soft-deleted Employee record."""
    employee.restore()
    logger.info("Employee restored: %s (%s)", employee.display_name, employee.employee_id)
    return employee


# ── Manager Assignment Engine ─────────────────────────────────────────────────


@transaction.atomic
def assign_manager(
    *,
    employee: Employee,
    manager: Employee,
    manager_type: str = "PRIMARY",
    effective_date: date | None = None,
    reason: str = "",
    actor_user_id: str = "",
) -> ManagerAssignment:
    """Assign reporting manager supporting multi-type assignments and hierarchy loop guards."""
    if employee.organization_id != manager.organization_id:
        raise EmployeeHierarchyError("Manager and employee must belong to the same organization.")

    validate_reporting_hierarchy(employee=employee, reporting_manager=manager)

    eff_date = effective_date or date.today()
    previous_manager = employee.reporting_manager

    # Deactivate existing active assignment for this manager_type if PRIMARY
    if manager_type == ManagerType.PRIMARY:
        ManagerAssignment.objects.filter(
            employee=employee, manager_type=manager_type, is_active=True
        ).update(is_active=False, end_date=eff_date)

        employee.reporting_manager = manager
        employee.save(update_fields=["reporting_manager", "updated_at"])

    assignment = ManagerAssignment.objects.create(
        employee=employee,
        manager=manager,
        manager_type=manager_type,
        is_active=True,
        effective_date=eff_date,
    )

    prev_data = {"manager_id": str(previous_manager.id), "manager_name": previous_manager.display_name} if previous_manager else {}
    new_data = {"manager_id": str(manager.id), "manager_name": manager.display_name, "manager_type": manager_type}

    WorkforceAssignment.objects.create(
        employee=employee,
        assignment_type=AssignmentType.MANAGER,
        effective_date=eff_date,
        previous_value=prev_data,
        new_value=new_data,
        reason=reason or f"Assigned {manager_type} manager {manager.display_name}",
        actor_user_id=actor_user_id,
    )

    publish_employee_event(
        ManagerAssigned(
            event_id=str(uuid.uuid4()),
            event_type="MANAGER_ASSIGNED",
            employee_id=str(employee.id),
            organization_id=str(employee.organization_id),
            manager_id=str(manager.id),
            manager_type=manager_type,
        )
    )

    logger.info("Manager assigned: %s -> %s (%s)", manager.display_name, employee.display_name, manager_type)
    return assignment


@transaction.atomic
def bulk_assign_manager(
    *,
    employee_ids: list[str | uuid.UUID],
    manager: Employee,
    manager_type: str = "PRIMARY",
    effective_date: date | None = None,
    actor_user_id: str = "",
) -> int:
    """Bulk assign a reporting manager to multiple employees in a single transaction."""
    eff_date = effective_date or date.today()
    employees = Employee.objects.filter(id__in=employee_ids)
    count = 0
    for emp in employees:
        assign_manager(
            employee=emp,
            manager=manager,
            manager_type=manager_type,
            effective_date=eff_date,
            reason="Bulk manager assignment",
            actor_user_id=actor_user_id,
        )
        count += 1
    logger.info("Bulk manager assignment executed for %d employees.", count)
    return count


# ── Shift Assignment Engine ───────────────────────────────────────────────────


@transaction.atomic
def assign_shift(
    *,
    employee: Employee,
    shift: Shift,
    effective_date: date | None = None,
    end_date: date | None = None,
    is_temporary: bool = False,
    reason: str = "",
    actor_user_id: str = "",
) -> WorkforceAssignment:
    """Assign reusable Shift template to an employee with assignment history tracking."""
    if shift.organization_id != employee.organization_id:
        raise EmployeeHierarchyError("Shift template must belong to the employee's organization.")

    eff_date = effective_date or date.today()
    previous_shift = employee.shift

    # Close previous active shift assignment in history
    WorkforceAssignment.objects.filter(
        employee=employee, assignment_type=AssignmentType.SHIFT, end_date__isnull=True
    ).update(end_date=eff_date)

    employee.shift = shift
    employee.save(update_fields=["shift", "updated_at"])

    prev_data = {"shift_id": str(previous_shift.id), "shift_name": previous_shift.name} if previous_shift else {}
    new_data = {"shift_id": str(shift.id), "shift_name": shift.name, "shift_code": shift.code}

    assignment = WorkforceAssignment.objects.create(
        employee=employee,
        assignment_type=AssignmentType.SHIFT,
        effective_date=eff_date,
        end_date=end_date,
        is_temporary=is_temporary,
        previous_value=prev_data,
        new_value=new_data,
        reason=reason or f"Assigned shift {shift.name}",
        actor_user_id=actor_user_id,
    )

    publish_employee_event(
        ShiftAssigned(
            event_id=str(uuid.uuid4()),
            event_type="SHIFT_ASSIGNED",
            employee_id=str(employee.id),
            organization_id=str(employee.organization_id),
            shift_id=str(shift.id),
        )
    )

    logger.info("Shift assigned: %s to %s", shift.name, employee.employee_id)
    return assignment


# ── Work Location Engine ─────────────────────────────────────────────────────


@transaction.atomic
def assign_work_location(
    *,
    employee: Employee,
    work_location: str,
    location_type: str = "OFFICE",
    effective_date: date | None = None,
    reason: str = "",
    actor_user_id: str = "",
) -> WorkforceAssignment:
    """Assign physical office, remote, hybrid, or site work location to an employee."""
    eff_date = effective_date or date.today()
    previous_location = employee.work_location

    WorkforceAssignment.objects.filter(
        employee=employee, assignment_type=AssignmentType.WORK_LOCATION, end_date__isnull=True
    ).update(end_date=eff_date)

    employee.work_location = work_location
    employee.save(update_fields=["work_location", "updated_at"])

    prev_data = {"work_location": previous_location}
    new_data = {"work_location": work_location, "location_type": location_type}

    assignment = WorkforceAssignment.objects.create(
        employee=employee,
        assignment_type=AssignmentType.WORK_LOCATION,
        effective_date=eff_date,
        previous_value=prev_data,
        new_value=new_data,
        reason=reason or f"Work location updated to {work_location}",
        actor_user_id=actor_user_id,
    )

    publish_employee_event(
        WorkLocationChanged(
            event_id=str(uuid.uuid4()),
            event_type="WORK_LOCATION_CHANGED",
            employee_id=str(employee.id),
            organization_id=str(employee.organization_id),
            new_location=work_location,
            location_type=location_type,
        )
    )

    logger.info("Work location assigned: %s to %s", work_location, employee.employee_id)
    return assignment


# ── Team Assignment Engine ───────────────────────────────────────────────────


@transaction.atomic
def assign_team(
    *,
    employee: Employee,
    team: Team,
    effective_date: date | None = None,
    reason: str = "",
    actor_user_id: str = "",
) -> WorkforceAssignment:
    """Assign employee to an organizational team unit."""
    if team.organization_id != employee.organization_id or team.department_id != employee.department_id:
        raise EmployeeHierarchyError("Team must belong to the employee's organization and department.")

    eff_date = effective_date or date.today()
    previous_team = employee.team

    WorkforceAssignment.objects.filter(
        employee=employee, assignment_type=AssignmentType.TEAM, end_date__isnull=True
    ).update(end_date=eff_date)

    employee.team = team
    employee.save(update_fields=["team", "updated_at"])

    prev_data = {"team_id": str(previous_team.id), "team_name": previous_team.name} if previous_team else {}
    new_data = {"team_id": str(team.id), "team_name": team.name, "team_code": team.code}

    assignment = WorkforceAssignment.objects.create(
        employee=employee,
        assignment_type=AssignmentType.TEAM,
        effective_date=eff_date,
        previous_value=prev_data,
        new_value=new_data,
        reason=reason or f"Assigned to team {team.name}",
        actor_user_id=actor_user_id,
    )

    publish_employee_event(
        EmployeeAssignedToTeam(
            event_id=str(uuid.uuid4()),
            event_type="EMPLOYEE_ASSIGNED_TO_TEAM",
            employee_id=str(employee.id),
            organization_id=str(employee.organization_id),
            team_id=str(team.id),
        )
    )

    logger.info("Team assigned: %s to %s", team.name, employee.employee_id)
    return assignment

