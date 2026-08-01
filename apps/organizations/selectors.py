"""Read-only query selectors for the organizations domain."""

import uuid
from typing import Optional
from django.db import models
from django.db.models import QuerySet

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
    RosterStatus,
    Shift,
    ShiftRoster,
    ShiftRosterAssignment,
    ShiftRotation,
    ShiftSwapRequest,
    Team,
)


def get_organization(*, organization_id: str | uuid.UUID) -> Optional[Organization]:
    """Retrieve a single Organization by ID with pre-fetched settings and branches."""
    try:
        return (
            Organization.objects.select_related("setting")
            .prefetch_related("branches")
            .get(pk=organization_id)
        )
    except (Organization.DoesNotExist, ValueError):
        return None


def get_organization_by_code(*, code: str) -> Optional[Organization]:
    """Retrieve an Organization by its unique immutable code."""
    if not code:
        return None
    try:
        return Organization.objects.select_related("setting").get(
            code__iexact=code.strip()
        )
    except Organization.DoesNotExist:
        return None


def list_organizations() -> QuerySet[Organization]:
    """Return all active non-deleted organizations ordered by creation date descending."""
    return (
        Organization.objects.select_related("setting")
        .all()
        .order_by("-created_at")
    )


def get_branch(*, branch_id: str | uuid.UUID) -> Optional[Branch]:
    """Retrieve a single Branch by ID with pre-fetched organization."""
    try:
        return Branch.objects.select_related("organization").get(pk=branch_id)
    except (Branch.DoesNotExist, ValueError):
        return None


def list_branches(*, organization_id: str | uuid.UUID) -> QuerySet[Branch]:
    """Return all branches for a given organization."""
    return (
        Branch.objects.select_related("organization")
        .filter(organization_id=organization_id)
        .order_by("name")
    )


def get_department(*, department_id: str | uuid.UUID) -> Optional[Department]:
    """Retrieve a Department by ID with pre-fetched organization, branch, and parent department."""
    try:
        return Department.objects.select_related(
            "organization", "branch", "parent_department"
        ).get(pk=department_id)
    except (Department.DoesNotExist, ValueError):
        return None


def list_departments(*, organization_id: str | uuid.UUID, branch_id: str | uuid.UUID | None = None) -> QuerySet[Department]:
    """Return departments for an organization, optionally filtered by branch."""
    qs = Department.objects.select_related(
        "organization", "branch", "parent_department"
    ).filter(organization_id=organization_id)
    if branch_id:
        qs = qs.filter(branch_id=branch_id)
    return qs.order_by("ordering", "name")


def get_designation(*, designation_id: str | uuid.UUID) -> Optional[Designation]:
    """Retrieve a Designation by ID with pre-fetched organization and department."""
    try:
        return Designation.objects.select_related("organization", "department").get(
            pk=designation_id
        )
    except (Designation.DoesNotExist, ValueError):
        return None


def list_designations(*, organization_id: str | uuid.UUID) -> QuerySet[Designation]:
    """Return all designations for an organization ordered by rank level."""
    return (
        Designation.objects.select_related("organization", "department")
        .filter(organization_id=organization_id)
        .order_by("level", "name")
    )


def get_team(*, team_id: str | uuid.UUID) -> Optional[Team]:
    """Retrieve a Team by ID with pre-fetched relations."""
    try:
        return Team.objects.select_related("organization", "branch", "department").get(
            pk=team_id
        )
    except (Team.DoesNotExist, ValueError):
        return None


def list_teams(*, organization_id: str | uuid.UUID, branch_id: str | uuid.UUID | None = None) -> QuerySet[Team]:
    """Return teams for an organization, optionally filtered by branch."""
    qs = Team.objects.select_related("organization", "branch", "department").filter(
        organization_id=organization_id
    )
    if branch_id:
        qs = qs.filter(branch_id=branch_id)
    return qs.order_by("name")


def get_shift(*, shift_id: str | uuid.UUID) -> Optional[Shift]:
    """Retrieve a Shift by ID."""
    try:
        return Shift.objects.select_related("organization").get(pk=shift_id)
    except (Shift.DoesNotExist, ValueError):
        return None


def list_shifts(*, organization_id: str | uuid.UUID) -> QuerySet[Shift]:
    """Return all shift templates for an organization."""
    return Shift.objects.select_related("organization").filter(
        organization_id=organization_id
    ).order_by("name")


def get_holiday(*, holiday_id: str | uuid.UUID) -> Optional[HolidayCalendar]:
    """Retrieve a HolidayCalendar entry by ID."""
    try:
        return HolidayCalendar.objects.select_related("organization", "branch").get(
            pk=holiday_id
        )
    except (HolidayCalendar.DoesNotExist, ValueError):
        return None


def list_holidays(*, organization_id: str | uuid.UUID, branch_id: str | uuid.UUID | None = None) -> QuerySet[HolidayCalendar]:
    """Return holidays for an organization (includes org-wide and branch-specific holidays)."""
    qs = HolidayCalendar.objects.select_related("organization", "branch").filter(
        organization_id=organization_id
    )
    if branch_id:
        qs = qs.filter(models.Q(branch_id=branch_id) | models.Q(branch__isnull=True))
    return qs.order_by("holiday_date")


def get_organization_setting(*, organization_id: str | uuid.UUID) -> Optional[OrganizationSetting]:
    """Retrieve OrganizationSetting for a given organization."""
    try:
        return OrganizationSetting.objects.select_related(
            "organization", "default_shift"
        ).get(organization_id=organization_id)
    except OrganizationSetting.DoesNotExist:
        return None


def get_organization_limit(*, organization_id: str | uuid.UUID) -> Optional[OrganizationLimit]:
    """Retrieve OrganizationLimit quota configuration for an organization."""
    try:
        return OrganizationLimit.objects.select_related("organization").get(
            organization_id=organization_id
        )
    except OrganizationLimit.DoesNotExist:
        return None


def get_organization_feature_flag(*, organization_id: str | uuid.UUID) -> Optional[OrganizationFeatureFlag]:
    """Retrieve OrganizationFeatureFlag configuration for an organization."""
    try:
        return OrganizationFeatureFlag.objects.select_related("organization").get(
            organization_id=organization_id
        )
    except OrganizationFeatureFlag.DoesNotExist:
        return None


def list_organization_audit_events(
    *, organization_id: str | uuid.UUID, limit: int = 50
) -> QuerySet[OrganizationAuditEvent]:
    """Return recent audit log trail events for an organization."""
    return OrganizationAuditEvent.objects.filter(
        organization_id=organization_id
    ).order_by("-timestamp")[:limit]


def has_active_departments_in_branch(*, branch_id: str | uuid.UUID) -> bool:
    """Check if a branch contains active non-deleted departments."""
    return Department.objects.filter(branch_id=branch_id).exists()


def has_active_teams_in_department(*, department_id: str | uuid.UUID) -> bool:
    """Check if a department contains active non-deleted teams."""
    return Team.objects.filter(department_id=department_id).exists()


def get_shift_roster(*, roster_id: str | uuid.UUID) -> Optional[ShiftRoster]:
    """Retrieve a ShiftRoster by UUID primary key."""
    try:
        return ShiftRoster.objects.select_related("organization").get(id=roster_id)
    except ShiftRoster.DoesNotExist:
        return None


def get_active_roster(*, organization_id: str | uuid.UUID, date) -> Optional[ShiftRoster]:
    """Retrieve active published ShiftRoster covering specified date for an organization."""
    return ShiftRoster.objects.filter(
        organization_id=organization_id,
        status=RosterStatus.PUBLISHED,
        start_date__lte=date,
        end_date__gte=date,
    ).order_by("-version").first()


def list_shift_rosters(*, organization_id: str | uuid.UUID, status: str | None = None) -> QuerySet[ShiftRoster]:
    """Retrieve list of ShiftRosters for an organization."""
    qs = ShiftRoster.objects.filter(organization_id=organization_id)
    if status:
        qs = qs.filter(status=status)
    return qs.order_by("-start_date")


def get_employee_roster_calendar(*, employee_id: str | uuid.UUID, start_date, end_date) -> list[dict]:
    """Build calendar shift schedule matrix for a specific employee across date range."""
    assignments = ShiftRosterAssignment.objects.filter(
        employee_id=employee_id,
        date__gte=start_date,
        date__lte=end_date,
        roster__status=RosterStatus.PUBLISHED,
    ).select_related("shift", "roster")

    calendar = []
    for a in assignments:
        calendar.append({
            "id": str(a.id),
            "date": a.date.isoformat(),
            "shift_id": str(a.shift.id),
            "shift_name": a.shift.name,
            "shift_code": a.shift.code,
            "start_time": a.shift.start_time.isoformat(),
            "end_time": a.shift.end_time.isoformat(),
            "is_override": a.is_override,
            "override_reason": a.override_reason,
        })
    return calendar


def get_team_roster_calendar(*, team_id: str | uuid.UUID, start_date, end_date) -> list[dict]:
    """Build team shift schedule matrix across date range."""
    assignments = ShiftRosterAssignment.objects.filter(
        employee__team_id=team_id,
        date__gte=start_date,
        date__lte=end_date,
        roster__status=RosterStatus.PUBLISHED,
    ).select_related("employee", "shift")

    calendar = []
    for a in assignments:
        calendar.append({
            "id": str(a.id),
            "employee_id": str(a.employee.id),
            "employee_name": a.employee.display_name,
            "date": a.date.isoformat(),
            "shift_code": a.shift.code,
            "shift_name": a.shift.name,
            "start_time": a.shift.start_time.isoformat(),
            "end_time": a.shift.end_time.isoformat(),
        })
    return calendar


