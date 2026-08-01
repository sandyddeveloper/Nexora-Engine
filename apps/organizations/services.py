"""Domain service methods for the Organization Business Rules Engine."""

import datetime
import logging
import uuid
from typing import Any, Dict

from django.db import transaction
from django.utils import timezone

from .constants import (
    DEFAULT_DEPARTMENTS,
    DEFAULT_FEATURE_FLAGS,
    DEFAULT_HOLIDAY_CONFIG,
    DEFAULT_ORGANIZATION_LIMITS,
    DEFAULT_SHIFT_CONFIG,
    LIFECYCLE_TRANSITIONS,
)
from .events import (
    OrganizationActivatedEvent,
    OrganizationArchivedEvent,
    OrganizationCreatedEvent,
    OrganizationSuspendedEvent,
    RosterArchivedEvent,
    RosterPublishedEvent,
    ShiftOverrideAppliedEvent,
    ShiftRosterAssignedEvent,
    ShiftSwapRequestedEvent,
    publish_domain_event,
)
from .exceptions import (
    BusinessRuleValidationError,
    CircularDependencyError,
    FeatureFlagDisabledError,
    InvalidLifecycleTransitionError,
    OrganizationLimitExceededError,
    ShiftRosterError,
    ShiftSwapError,
)
from .models import (
    Branch,
    Department,
    Designation,
    HolidayCalendar,
    Organization,
    OrganizationAuditEvent,
    OrganizationFeatureFlag,
    OrganizationLimit,
    OrganizationSetting,
    OrganizationStatus,
    RosterPeriodType,
    RosterStatus,
    Shift,
    ShiftRoster,
    ShiftRosterAssignment,
    ShiftRotation,
    ShiftSwapRequest,
    SwapStatus,
    Team,
)

logger = logging.getLogger("nexora.organizations")


# ── Audit & Event Helpers ───────────────────────────────────────────────────


def record_organization_audit_event(
    *,
    organization: Organization,
    event_type: str,
    user_id: str = "",
    user_email: str = "",
    ip_address: str | None = None,
    request_id: str = "",
    previous_state: Dict[str, Any] | None = None,
    new_state: Dict[str, Any] | None = None,
    metadata: Dict[str, Any] | None = None,
) -> OrganizationAuditEvent:
    """Record an audit trail event for an Organization Business Engine mutation."""
    return OrganizationAuditEvent.objects.create(
        organization=organization,
        event_type=event_type,
        user_id=user_id,
        user_email=user_email,
        ip_address=ip_address,
        request_id=request_id,
        previous_state=previous_state or {},
        new_state=new_state or {},
        metadata=metadata or {},
    )


# ── Limit & Feature Flag Engine Services ────────────────────────────────────


def check_organization_limit(*, organization: Organization, limit_type: str) -> None:
    """Validate resource creation count against OrganizationLimit subscription quota."""
    limit = getattr(organization, "limit", None)
    if not limit:
        return

    counts = {
        "max_branches": lambda: Branch.objects.filter(organization=organization).count(),
        "max_departments": lambda: Department.objects.filter(organization=organization).count(),
        "max_teams": lambda: Team.objects.filter(organization=organization).count(),
        "max_shifts": lambda: Shift.objects.filter(organization=organization).count(),
    }

    if limit_type in counts:
        max_allowed = getattr(limit, limit_type, 0)
        current_count = counts[limit_type]()
        if current_count >= max_allowed:
            raise OrganizationLimitExceededError(
                f"Organization quota limit exceeded for {limit_type}. "
                f"Allowed: {max_allowed}, Current: {current_count}."
            )


def check_feature_flag(*, organization: Organization, flag_name: str) -> None:
    """Validate if a specific feature flag is enabled for an Organization."""
    flag = getattr(organization, "feature_flag", None)
    if not flag:
        return

    if hasattr(flag, flag_name) and not getattr(flag, flag_name):
        raise FeatureFlagDisabledError(
            f"The requested module/feature '{flag_name}' is disabled for organization {organization.code}."
        )


# ── Onboarding Engine ────────────────────────────────────────────────────────


@transaction.atomic
def onboard_organization(
    *,
    name: str,
    legal_name: str = "",
    registration_number: str = "",
    tax_number: str = "",
    gst_number: str = "",
    email: str = "",
    phone: str = "",
    website: str = "",
    industry: str = "",
    country: str = "",
    state: str = "",
    city: str = "",
    address: str = "",
    postal_code: str = "",
    user_id: str = "",
    user_email: str = "",
    ip_address: str | None = None,
    request_id: str = "",
) -> Organization:
    """Execute complete single-transaction Organization Onboarding Workflow.

    Automates:
    1. Organization creation (Status = ACTIVE)
    2. Dedicated OrganizationSetting initialization
    3. Head Office Branch creation (HQ-01)
    4. 6 Default Departments creation (ENG, HR, FIN, OPS, SALES, SUP)
    5. Default Shift Template creation (SHIFT-STD)
    6. Default Holiday Calendar creation (New Year)
    7. Subscription Quota Limits initialization
    8. Feature Flags initialization
    9. Audit Event trail entry
    10. Domain Event publishing

    Rolls back entire transaction if any step fails.
    """
    # 1. Create Organization
    org = Organization.objects.create(
        name=name,
        legal_name=legal_name or name,
        registration_number=registration_number,
        tax_number=tax_number,
        gst_number=gst_number,
        email=email,
        phone=phone,
        website=website,
        industry=industry,
        country=country,
        state=state,
        city=city,
        address=address,
        postal_code=postal_code,
        status=OrganizationStatus.ACTIVE,
    )

    # 2. Organization Settings
    setting = OrganizationSetting.objects.create(
        organization=org,
        default_language=org.language,
        default_currency=org.currency,
        default_timezone=org.timezone,
    )

    # 3. Head Office Branch
    hq_branch = Branch.objects.create(
        organization=org,
        code="HQ-01",
        name=f"{name} Head Office",
        email=email,
        phone=phone,
        city=city,
        state=state,
        country=country,
        postal_code=postal_code,
        address=address,
        timezone=org.timezone,
        is_headquarters=True,
        status=OrganizationStatus.ACTIVE,
    )

    # 4. Default Departments
    dept_map = {}
    for d_data in DEFAULT_DEPARTMENTS:
        dept = Department.objects.create(
            organization=org,
            branch=hq_branch,
            code=d_data["code"],
            name=d_data["name"],
            description=d_data["description"],
            ordering=d_data["ordering"],
            status=OrganizationStatus.ACTIVE,
        )
        dept_map[d_data["code"]] = dept

    # 5. Default Shift Template
    shift = Shift.objects.create(
        organization=org,
        code=DEFAULT_SHIFT_CONFIG["code"],
        name=DEFAULT_SHIFT_CONFIG["name"],
        shift_type=DEFAULT_SHIFT_CONFIG["shift_type"],
        start_time=datetime.time.fromisoformat(DEFAULT_SHIFT_CONFIG["start_time"]),
        end_time=datetime.time.fromisoformat(DEFAULT_SHIFT_CONFIG["end_time"]),
        grace_time_minutes=DEFAULT_SHIFT_CONFIG["grace_time_minutes"],
        flexible_hours=DEFAULT_SHIFT_CONFIG["flexible_hours"],
        is_night_shift=DEFAULT_SHIFT_CONFIG["is_night_shift"],
        break_duration_minutes=DEFAULT_SHIFT_CONFIG["break_duration_minutes"],
        working_hours=DEFAULT_SHIFT_CONFIG["working_hours"],
        status=OrganizationStatus.ACTIVE,
    )
    setting.default_shift = shift
    setting.save(update_fields=["default_shift", "updated_at"])

    # 6. Default Holiday Calendar
    HolidayCalendar.objects.create(
        organization=org,
        branch=None,  # Organization-wide
        name="New Year's Day",
        holiday_date=datetime.date(datetime.date.today().year + 1, 1, 1),
        holiday_type="PUBLIC",
        description="Global New Year holiday",
        is_recurring=True,
        status=OrganizationStatus.ACTIVE,
    )

    # 7. Organization Limits
    OrganizationLimit.objects.create(organization=org, **DEFAULT_ORGANIZATION_LIMITS)

    # 8. Organization Feature Flags
    OrganizationFeatureFlag.objects.create(organization=org, **DEFAULT_FEATURE_FLAGS)

    # 9. Audit Event Entry
    record_organization_audit_event(
        organization=org,
        event_type="ORGANIZATION_ONBOARDED",
        user_id=user_id,
        user_email=user_email,
        ip_address=ip_address,
        request_id=request_id,
        new_state={"status": OrganizationStatus.ACTIVE, "code": org.code, "name": org.name},
        metadata={"headquarters_branch": hq_branch.code, "departments_created": len(dept_map)},
    )

    # 10. Publish Domain Event
    event = OrganizationCreatedEvent(
        event_id=str(uuid.uuid4()),
        event_type="ORGANIZATION_CREATED",
        organization_id=str(org.id),
        code=org.code,
        name=org.name,
    )
    publish_domain_event(event)

    logger.info("Complete Onboarding Engine workflow executed for Org: %s (%s)", org.name, org.code)
    return org


# ── Lifecycle FSM State Engine ───────────────────────────────────────────────


@transaction.atomic
def transition_organization_status(
    *,
    organization: Organization,
    target_status: str,
    reason: str = "",
    user_id: str = "",
    user_email: str = "",
    ip_address: str | None = None,
    request_id: str = "",
) -> Organization:
    """Transition Organization status adhering to strict FSM lifecycle rules."""
    current_status = organization.status
    if current_status == target_status:
        return organization

    allowed = LIFECYCLE_TRANSITIONS.get(current_status, set())
    if target_status not in allowed:
        raise InvalidLifecycleTransitionError(
            f"Illegal state transition for Organization {organization.code}: "
            f"Cannot transition from '{current_status}' to '{target_status}'. "
            f"Allowed target statuses: {sorted(list(allowed))}."
        )

    previous_state = {"status": current_status}
    organization.status = target_status
    organization.save(update_fields=["status", "updated_at"])
    new_state = {"status": target_status, "reason": reason}

    record_organization_audit_event(
        organization=organization,
        event_type=f"ORGANIZATION_STATUS_TRANSITION_{target_status}",
        user_id=user_id,
        user_email=user_email,
        ip_address=ip_address,
        request_id=request_id,
        previous_state=previous_state,
        new_state=new_state,
    )

    # Publish Domain Events
    if target_status == OrganizationStatus.ACTIVE:
        publish_domain_event(
            OrganizationActivatedEvent(
                event_id=str(uuid.uuid4()),
                event_type="ORGANIZATION_ACTIVATED",
                organization_id=str(organization.id),
                previous_status=current_status,
            )
        )
    elif target_status == OrganizationStatus.SUSPENDED:
        publish_domain_event(
            OrganizationSuspendedEvent(
                event_id=str(uuid.uuid4()),
                event_type="ORGANIZATION_SUSPENDED",
                organization_id=str(organization.id),
                reason=reason,
            )
        )
    elif target_status == OrganizationStatus.ARCHIVED:
        publish_domain_event(
            OrganizationArchivedEvent(
                event_id=str(uuid.uuid4()),
                event_type="ORGANIZATION_ARCHIVED",
                organization_id=str(organization.id),
            )
        )

    logger.info("Organization %s transitioned: %s -> %s", organization.code, current_status, target_status)
    return organization


# ── Business Rule Validation & Hierarchy Guards ─────────────────────────────


def validate_department_parent(
    *, department: Department, parent_department: Department | None
) -> None:
    """Validate department parent hierarchy to prevent circular dependency loops."""
    if not parent_department:
        return
    if department.id == parent_department.id:
        raise CircularDependencyError("A department cannot be its own parent department.")

    current = parent_department
    visited = {department.id}
    while current:
        if current.id in visited:
            raise CircularDependencyError(
                f"Circular parent department loop detected for department '{department.name}'."
            )
        visited.add(current.id)
        current = current.parent_department


# ── Domain CRUD Services ─────────────────────────────────────────────────────


@transaction.atomic
def create_organization(
    *,
    name: str,
    legal_name: str = "",
    registration_number: str = "",
    tax_number: str = "",
    gst_number: str = "",
    email: str = "",
    phone: str = "",
    website: str = "",
    logo: str = "",
    industry: str = "",
    organization_type: str = "COMPANY",
    currency: str = "USD",
    language: str = "en",
    timezone: str = "UTC",
    date_format: str = "YYYY-MM-DD",
    time_format: str = "24H",
    fiscal_year_start: str = "01-01",
    country: str = "",
    state: str = "",
    city: str = "",
    address: str = "",
    postal_code: str = "",
    status: str = "ACTIVE",
) -> Organization:
    """Create a new Organization and initialize default OrganizationSetting, Limit, and FeatureFlag."""
    org = Organization.objects.create(
        name=name,
        legal_name=legal_name,
        registration_number=registration_number,
        tax_number=tax_number,
        gst_number=gst_number,
        email=email,
        phone=phone,
        website=website,
        logo=logo,
        industry=industry,
        organization_type=organization_type,
        currency=currency,
        language=language,
        timezone=timezone,
        date_format=date_format,
        time_format=time_format,
        fiscal_year_start=fiscal_year_start,
        country=country,
        state=state,
        city=city,
        address=address,
        postal_code=postal_code,
        status=status,
    )
    OrganizationSetting.objects.create(
        organization=org,
        default_language=language,
        default_currency=currency,
        default_timezone=timezone,
    )
    OrganizationLimit.objects.create(organization=org, **DEFAULT_ORGANIZATION_LIMITS)
    OrganizationFeatureFlag.objects.create(organization=org, **DEFAULT_FEATURE_FLAGS)
    logger.info("Organization created: %s (%s)", org.name, org.code)
    return org


@transaction.atomic
def update_organization(*, organization: Organization, **fields) -> Organization:
    """Update editable fields on an Organization instance."""
    allowed_fields = {
        "name",
        "legal_name",
        "registration_number",
        "tax_number",
        "gst_number",
        "email",
        "phone",
        "website",
        "logo",
        "industry",
        "organization_type",
        "currency",
        "language",
        "timezone",
        "date_format",
        "time_format",
        "fiscal_year_start",
        "country",
        "state",
        "city",
        "address",
        "postal_code",
        "status",
    }
    for field, value in fields.items():
        if field in allowed_fields:
            setattr(organization, field, value)
    organization.save()
    logger.info("Organization updated: %s (%s)", organization.name, organization.code)
    return organization


@transaction.atomic
def soft_delete_organization(*, organization: Organization) -> Organization:
    """Soft delete an Organization after verifying it is not currently ACTIVE."""
    if organization.status == OrganizationStatus.ACTIVE:
        raise BusinessRuleValidationError(
            "Active organizations cannot be soft deleted. Suspend or deactivate the organization first."
        )
    organization.delete(soft=True)
    logger.info("Organization soft deleted: %s (%s)", organization.name, organization.code)
    return organization


@transaction.atomic
def restore_organization(*, organization: Organization) -> Organization:
    """Restore a soft-deleted Organization."""
    organization.restore()
    organization.status = OrganizationStatus.ACTIVE
    organization.save(update_fields=["status", "updated_at"])
    logger.info("Organization restored: %s (%s)", organization.name, organization.code)
    return organization


# ── Branch Services ──────────────────────────────────────────────────────────


@transaction.atomic
def create_branch(
    *,
    organization: Organization,
    code: str,
    name: str,
    email: str = "",
    phone: str = "",
    address: str = "",
    city: str = "",
    state: str = "",
    country: str = "",
    postal_code: str = "",
    latitude=None,
    longitude=None,
    timezone: str = "UTC",
    is_headquarters: bool = False,
    status: str = "ACTIVE",
) -> Branch:
    """Create a new operational Branch enforcing quota limits and single HQ policy."""
    check_organization_limit(organization=organization, limit_type="max_branches")

    if is_headquarters:
        Branch.objects.filter(organization=organization, is_headquarters=True).update(
            is_headquarters=False
        )

    branch = Branch.objects.create(
        organization=organization,
        code=code.upper().strip(),
        name=name,
        email=email,
        phone=phone,
        address=address,
        city=city,
        state=state,
        country=country,
        postal_code=postal_code,
        latitude=latitude,
        longitude=longitude,
        timezone=timezone,
        is_headquarters=is_headquarters,
        status=status,
    )
    logger.info("Branch created: %s (%s) for Org %s", branch.name, branch.code, organization.code)
    return branch


@transaction.atomic
def update_branch(*, branch: Branch, **fields) -> Branch:
    """Update editable fields on a Branch instance."""
    allowed_fields = {
        "name",
        "email",
        "phone",
        "address",
        "city",
        "state",
        "country",
        "postal_code",
        "latitude",
        "longitude",
        "timezone",
        "is_headquarters",
        "status",
    }
    if fields.get("is_headquarters"):
        Branch.objects.filter(
            organization=branch.organization, is_headquarters=True
        ).exclude(pk=branch.pk).update(is_headquarters=False)

    for field, value in fields.items():
        if field in allowed_fields:
            setattr(branch, field, value)
    branch.save()
    logger.info("Branch updated: %s (%s)", branch.name, branch.code)
    return branch


@transaction.atomic
def soft_delete_branch(*, branch: Branch) -> Branch:
    """Soft delete a Branch instance after verifying it contains no active departments."""
    if Department.objects.filter(branch=branch).exists():
        raise BusinessRuleValidationError(
            f"Cannot delete Branch '{branch.name}' because it contains active departments."
        )
    branch.delete(soft=True)
    logger.info("Branch soft deleted: %s (%s)", branch.name, branch.code)
    return branch


# ── Department Services ──────────────────────────────────────────────────────


@transaction.atomic
def create_department(
    *,
    organization: Organization,
    branch: Branch,
    name: str,
    code: str,
    parent_department: Department | None = None,
    description: str = "",
    ordering: int = 0,
    status: str = "ACTIVE",
) -> Department:
    """Create a new Department enforcing quota limits and hierarchy loop validation."""
    check_organization_limit(organization=organization, limit_type="max_departments")

    department = Department(
        organization=organization,
        branch=branch,
        parent_department=parent_department,
        name=name,
        code=code.upper().strip(),
        description=description,
        ordering=ordering,
        status=status,
    )
    validate_department_parent(department=department, parent_department=parent_department)
    department.save()
    logger.info("Department created: %s (%s)", department.name, department.code)
    return department


@transaction.atomic
def update_department(*, department: Department, **fields) -> Department:
    """Update editable fields on a Department instance."""
    allowed_fields = {"name", "description", "parent_department", "ordering", "status"}
    if "parent_department" in fields:
        validate_department_parent(
            department=department, parent_department=fields["parent_department"]
        )

    for field, value in fields.items():
        if field in allowed_fields:
            setattr(department, field, value)
    department.save()
    logger.info("Department updated: %s (%s)", department.name, department.code)
    return department


@transaction.atomic
def soft_delete_department(*, department: Department) -> Department:
    """Soft delete a Department instance after verifying it contains no active teams."""
    if Team.objects.filter(department=department).exists():
        raise BusinessRuleValidationError(
            f"Cannot delete Department '{department.name}' because it contains active teams."
        )
    department.delete(soft=True)
    logger.info("Department soft deleted: %s (%s)", department.name, department.code)
    return department


# ── Designation Services ─────────────────────────────────────────────────────


@transaction.atomic
def create_designation(
    *,
    organization: Organization,
    name: str,
    code: str,
    department: Department | None = None,
    grade: str = "",
    level: int = 1,
    description: str = "",
    status: str = "ACTIVE",
) -> Designation:
    """Create a new Designation under an Organization."""
    designation = Designation.objects.create(
        organization=organization,
        department=department,
        name=name,
        code=code.upper().strip(),
        grade=grade,
        level=level,
        description=description,
        status=status,
    )
    logger.info("Designation created: %s (%s)", designation.name, designation.code)
    return designation


@transaction.atomic
def update_designation(*, designation: Designation, **fields) -> Designation:
    """Update editable fields on a Designation instance."""
    allowed_fields = {"name", "department", "grade", "level", "description", "status"}
    for field, value in fields.items():
        if field in allowed_fields:
            setattr(designation, field, value)
    designation.save()
    logger.info("Designation updated: %s (%s)", designation.name, designation.code)
    return designation


@transaction.atomic
def soft_delete_designation(*, designation: Designation) -> Designation:
    """Soft delete a Designation instance."""
    designation.delete(soft=True)
    logger.info("Designation soft deleted: %s (%s)", designation.name, designation.code)
    return designation


# ── Team Services ────────────────────────────────────────────────────────────


@transaction.atomic
def create_team(
    *,
    organization: Organization,
    branch: Branch,
    department: Department,
    name: str,
    code: str,
    description: str = "",
    status: str = "ACTIVE",
) -> Team:
    """Create a new Team belonging to a Department, Branch, and Organization."""
    check_organization_limit(organization=organization, limit_type="max_teams")

    team = Team.objects.create(
        organization=organization,
        branch=branch,
        department=department,
        name=name,
        code=code.upper().strip(),
        description=description,
        status=status,
    )
    logger.info("Team created: %s (%s)", team.name, team.code)
    return team


@transaction.atomic
def update_team(*, team: Team, **fields) -> Team:
    """Update editable fields on a Team instance."""
    allowed_fields = {"name", "description", "status"}
    for field, value in fields.items():
        if field in allowed_fields:
            setattr(team, field, value)
    team.save()
    logger.info("Team updated: %s (%s)", team.name, team.code)
    return team


@transaction.atomic
def soft_delete_team(*, team: Team) -> Team:
    """Soft delete a Team instance."""
    team.delete(soft=True)
    logger.info("Team soft deleted: %s (%s)", team.name, team.code)
    return team


# ── Shift Services ───────────────────────────────────────────────────────────


@transaction.atomic
def create_shift(
    *,
    organization: Organization,
    name: str,
    code: str,
    start_time,
    end_time,
    shift_type: str = "REGULAR",
    grace_time_minutes: int = 15,
    flexible_hours: bool = False,
    is_night_shift: bool = False,
    break_duration_minutes: int = 60,
    working_hours: float = 8.00,
    status: str = "ACTIVE",
) -> Shift:
    """Create a reusable Shift template under an Organization."""
    check_organization_limit(organization=organization, limit_type="max_shifts")

    shift = Shift.objects.create(
        organization=organization,
        name=name,
        code=code.upper().strip(),
        shift_type=shift_type,
        start_time=start_time,
        end_time=end_time,
        grace_time_minutes=grace_time_minutes,
        flexible_hours=flexible_hours,
        is_night_shift=is_night_shift,
        break_duration_minutes=break_duration_minutes,
        working_hours=working_hours,
        status=status,
    )
    logger.info("Shift template created: %s (%s)", shift.name, shift.code)
    return shift


@transaction.atomic
def update_shift(*, shift: Shift, **fields) -> Shift:
    """Update editable fields on a Shift template."""
    allowed_fields = {
        "name",
        "shift_type",
        "start_time",
        "end_time",
        "grace_time_minutes",
        "flexible_hours",
        "is_night_shift",
        "break_duration_minutes",
        "working_hours",
        "status",
    }
    for field, value in fields.items():
        if field in allowed_fields:
            setattr(shift, field, value)
    shift.save()
    logger.info("Shift template updated: %s (%s)", shift.name, shift.code)
    return shift


@transaction.atomic
def soft_delete_shift(*, shift: Shift) -> Shift:
    """Soft delete a Shift template after verifying it is not default shift."""
    setting = getattr(shift.organization, "setting", None)
    if setting and setting.default_shift_id == shift.id:
        raise BusinessRuleValidationError(
            f"Cannot delete Shift template '{shift.name}' because it is configured as default shift."
        )
    shift.delete(soft=True)
    logger.info("Shift template soft deleted: %s (%s)", shift.name, shift.code)
    return shift


# ── Holiday Calendar Services ────────────────────────────────────────────────


@transaction.atomic
def create_holiday(
    *,
    organization: Organization,
    name: str,
    holiday_date,
    branch: Branch | None = None,
    holiday_type: str = "PUBLIC",
    description: str = "",
    is_recurring: bool = False,
    status: str = "ACTIVE",
) -> HolidayCalendar:
    """Create a HolidayCalendar entry."""
    holiday = HolidayCalendar.objects.create(
        organization=organization,
        branch=branch,
        name=name,
        holiday_date=holiday_date,
        holiday_type=holiday_type,
        description=description,
        is_recurring=is_recurring,
        status=status,
    )
    logger.info("Holiday created: %s (%s)", holiday.name, holiday.holiday_date)
    return holiday


@transaction.atomic
def update_holiday(*, holiday: HolidayCalendar, **fields) -> HolidayCalendar:
    """Update editable fields on a HolidayCalendar entry."""
    allowed_fields = {
        "name",
        "holiday_date",
        "branch",
        "holiday_type",
        "description",
        "is_recurring",
        "status",
    }
    for field, value in fields.items():
        if field in allowed_fields:
            setattr(holiday, field, value)
    holiday.save()
    logger.info("Holiday updated: %s (%s)", holiday.name, holiday.holiday_date)
    return holiday


@transaction.atomic
def soft_delete_holiday(*, holiday: HolidayCalendar) -> HolidayCalendar:
    """Soft delete a HolidayCalendar entry."""
    holiday.delete(soft=True)
    logger.info("Holiday soft deleted: %s", holiday.name)
    return holiday


# ── Organization Setting, Limit & Feature Flag Services ──────────────────────


@transaction.atomic
def update_organization_setting(
    *, setting: OrganizationSetting, **fields
) -> OrganizationSetting:
    """Update editable configuration parameters on OrganizationSetting instance."""
    allowed_fields = {
        "attendance_mode",
        "leave_approval_levels",
        "working_days_mask",
        "weekend_days_mask",
        "default_shift",
        "default_language",
        "default_currency",
        "default_timezone",
        "notification_config",
        "security_config",
    }
    for field, value in fields.items():
        if field in allowed_fields:
            setattr(setting, field, value)
    setting.save()
    logger.info("Organization settings updated for Org: %s", setting.organization.code)
    return setting


@transaction.atomic
def update_organization_limit(
    *, limit: OrganizationLimit, **fields
) -> OrganizationLimit:
    """Update subscription quota limits on OrganizationLimit instance."""
    allowed_fields = {
        "max_branches",
        "max_departments",
        "max_teams",
        "max_employees",
        "max_storage_gb",
        "max_api_calls_per_day",
        "max_projects",
    }
    for field, value in fields.items():
        if field in allowed_fields:
            setattr(limit, field, value)
    limit.save()
    logger.info("Organization limits updated for Org: %s", limit.organization.code)
    return limit


@transaction.atomic
def update_organization_feature_flag(
    *, feature_flag: OrganizationFeatureFlag, **fields
) -> OrganizationFeatureFlag:
    """Update feature flags on OrganizationFeatureFlag instance."""
    allowed_fields = {
        "attendance_enabled",
        "payroll_enabled",
        "crm_enabled",
        "projects_enabled",
        "documents_enabled",
        "ai_assistant_enabled",
        "automation_enabled",
        "api_access_enabled",
    }
    for field, value in fields.items():
        if field in allowed_fields:
            setattr(feature_flag, field, value)
    feature_flag.save()
    logger.info("Organization feature flags updated for Org: %s", feature_flag.organization.code)
    return feature_flag


# ── Shift Rostering & Scheduling Engine ───────────────────────────────────────


@transaction.atomic
def create_shift_roster(
    *,
    organization: Organization,
    name: str,
    code: str,
    period_type: str = RosterPeriodType.WEEKLY,
    start_date: datetime.date,
    end_date: datetime.date,
) -> ShiftRoster:
    """Create a new ShiftRoster in DRAFT state."""
    if start_date > end_date:
        raise ShiftRosterError("Start date cannot be later than end date.")

    roster = ShiftRoster.objects.create(
        organization=organization,
        name=name,
        code=code.upper(),
        period_type=period_type,
        start_date=start_date,
        end_date=end_date,
        status=RosterStatus.DRAFT,
    )

    logger.info("Shift roster created: %s (%s) for Org %s", roster.name, roster.code, organization.code)
    return roster


@transaction.atomic
def publish_shift_roster(*, roster: ShiftRoster) -> ShiftRoster:
    """Publish a draft shift roster making assignments active."""
    if roster.status == RosterStatus.PUBLISHED:
        raise ShiftRosterError("Shift roster is already published.")

    roster.status = RosterStatus.PUBLISHED
    roster.version += 1
    roster.save()

    publish_domain_event(
        RosterPublishedEvent(
            event_id=str(uuid.uuid4()),
            event_type="ROSTER_PUBLISHED",
            organization_id=str(roster.organization_id),
            roster_id=str(roster.id),
            period_type=roster.period_type,
        )
    )

    logger.info("Shift roster published: %s (%s) v%d", roster.name, roster.code, roster.version)
    return roster


@transaction.atomic
def archive_shift_roster(*, roster: ShiftRoster) -> ShiftRoster:
    """Archive a published shift roster."""
    roster.status = RosterStatus.ARCHIVED
    roster.save()

    publish_domain_event(
        RosterArchivedEvent(
            event_id=str(uuid.uuid4()),
            event_type="ROSTER_ARCHIVED",
            organization_id=str(roster.organization_id),
            roster_id=str(roster.id),
        )
    )

    logger.info("Shift roster archived: %s", roster.code)
    return roster


@transaction.atomic
def assign_employee_roster_shift(
    *,
    roster: ShiftRoster,
    employee,
    shift: Shift,
    date: datetime.date,
    is_override: bool = False,
    override_reason: str = "",
) -> ShiftRosterAssignment:
    """Assign an employee to a shift for a single calendar date in a roster."""
    if date < roster.start_date or date > roster.end_date:
        raise ShiftRosterError("Assignment date falls outside roster period boundaries.")

    assignment, created = ShiftRosterAssignment.objects.update_or_create(
        roster=roster,
        employee=employee,
        date=date,
        defaults={
            "shift": shift,
            "is_override": is_override,
            "override_reason": override_reason,
        },
    )

    logger.info("Roster assignment saved: %s -> %s on %s", employee.employee_id, shift.code, date)
    return assignment


@transaction.atomic
def bulk_assign_team_roster_shift(
    *,
    roster: ShiftRoster,
    team_id: str | uuid.UUID,
    shift: Shift,
    start_date: datetime.date,
    end_date: datetime.date,
) -> int:
    """Bulk assign all employees in a team to a shift template across date range."""
    from apps.employees.models import Employee

    team_members = Employee.objects.filter(team_id=team_id, is_active=True)
    count = 0

    curr_date = start_date
    while curr_date <= end_date:
        for emp in team_members:
            assign_employee_roster_shift(
                roster=roster,
                employee=emp,
                shift=shift,
                date=curr_date,
            )
            count += 1
        curr_date += datetime.timedelta(days=1)

    logger.info("Bulk team shift roster assignment executed: %d assignments created.", count)
    return count


@transaction.atomic
def override_employee_shift(
    *,
    roster: ShiftRoster,
    employee,
    shift: Shift,
    date: datetime.date,
    reason: str,
) -> ShiftRosterAssignment:
    """Apply manual emergency shift override for an employee."""
    assignment = assign_employee_roster_shift(
        roster=roster,
        employee=employee,
        shift=shift,
        date=date,
        is_override=True,
        override_reason=reason,
    )

    publish_domain_event(
        ShiftOverrideAppliedEvent(
            event_id=str(uuid.uuid4()),
            event_type="SHIFT_OVERRIDE_APPLIED",
            organization_id=str(roster.organization_id),
            employee_id=str(employee.id),
            date=date.isoformat(),
        )
    )

    logger.info("Shift override applied for Employee %s on %s", employee.employee_id, date)
    return assignment


@transaction.atomic
def submit_shift_swap_request(
    *,
    requester,
    target_employee,
    requester_date: datetime.date,
    target_date: datetime.date,
    reason: str = "",
) -> ShiftSwapRequest:
    """Submit peer-to-peer shift swap request foundation."""
    if requester.organization_id != target_employee.organization_id:
        raise ShiftSwapError("Requester and target employee must belong to the same organization.")

    swap_req = ShiftSwapRequest.objects.create(
        requester=requester,
        target_employee=target_employee,
        requester_date=requester_date,
        target_date=target_date,
        reason=reason,
        status=SwapStatus.PENDING,
    )

    publish_domain_event(
        ShiftSwapRequestedEvent(
            event_id=str(uuid.uuid4()),
            event_type="SHIFT_SWAP_REQUESTED",
            organization_id=str(requester.organization_id),
            swap_request_id=str(swap_req.id),
            requester_id=str(requester.id),
            target_id=str(target_employee.id),
        )
    )

    logger.info("Shift swap requested: %s <-> %s", requester.employee_id, target_employee.employee_id)
    return swap_req

