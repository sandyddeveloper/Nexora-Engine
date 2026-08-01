"""Read-only query selector functions for the employees domain."""

import uuid
from typing import Optional

from django.db import models
from django.db.models import QuerySet

from .constants import MAX_HIERARCHY_DEPTH
from .models import (
    Certification,
    Education,
    EmergencyContact,
    Employee,
    EmployeeAuditEvent,
    EmployeeIdentifier,
    EmployeeProfile,
    EmployeeResignation,
    EmploymentHistory,
    Experience,
    ManagerAssignment,
    Skill,
    WorkforceAssignment,
)


def get_employee(*, employee_id: str | uuid.UUID) -> Optional[Employee]:
    """Retrieve an Employee instance by primary key with select_related preloads."""
    try:
        return (
            Employee.objects.select_related(
                "organization",
                "branch",
                "department",
                "designation",
                "team",
                "reporting_manager",
                "user",
                "shift",
                "profile",
            )
            .get(pk=employee_id)
        )
    except (Employee.DoesNotExist, ValueError):
        return None


def get_employee_by_code(*, organization_id: str | uuid.UUID, code: str) -> Optional[Employee]:
    """Retrieve an Employee by employee_id code within an organization."""
    try:
        return (
            Employee.objects.select_related(
                "organization", "branch", "department", "designation"
            )
            .get(organization_id=organization_id, employee_id=code)
        )
    except Employee.DoesNotExist:
        return None


def list_employees(
    *,
    organization_id: str | uuid.UUID,
    branch_id: str | uuid.UUID | None = None,
    department_id: str | uuid.UUID | None = None,
    designation_id: str | uuid.UUID | None = None,
    employment_status: str | None = None,
    search: str | None = None,
) -> QuerySet[Employee]:
    """Return filtered queryset of employees for an organization with optimized preloads."""
    qs = Employee.objects.select_related(
        "organization",
        "branch",
        "department",
        "designation",
        "team",
        "reporting_manager",
    ).filter(organization_id=organization_id)

    if branch_id:
        qs = qs.filter(branch_id=branch_id)
    if department_id:
        qs = qs.filter(department_id=department_id)
    if designation_id:
        qs = qs.filter(designation_id=designation_id)
    if employment_status:
        qs = qs.filter(employment_status=employment_status)
    if search:
        qs = qs.filter(
            models.Q(first_name__icontains=search)
            | models.Q(last_name__icontains=search)
            | models.Q(official_email__icontains=search)
            | models.Q(employee_id__icontains=search)
        )

    return qs.order_by("first_name", "last_name")


def get_employee_profile(*, employee_id: str | uuid.UUID) -> Optional[EmployeeProfile]:
    """Retrieve detailed EmployeeProfile for an employee."""
    try:
        return EmployeeProfile.objects.select_related("employee").get(employee_id=employee_id)
    except EmployeeProfile.DoesNotExist:
        return None


def list_emergency_contacts(*, employee_id: str | uuid.UUID) -> QuerySet[EmergencyContact]:
    """List emergency contacts for an employee."""
    return EmergencyContact.objects.filter(employee_id=employee_id).order_by("priority", "name")


def list_education_history(*, employee_id: str | uuid.UUID) -> QuerySet[Education]:
    """List education background history for an employee."""
    return Education.objects.filter(employee_id=employee_id).order_by("-end_date")


def list_experience_history(*, employee_id: str | uuid.UUID) -> QuerySet[Experience]:
    """List prior work experience history for an employee."""
    return Experience.objects.filter(employee_id=employee_id).order_by("-start_date")


def list_skills(*, employee_id: str | uuid.UUID) -> QuerySet[Skill]:
    """List technical and functional skills for an employee."""
    return Skill.objects.filter(employee_id=employee_id).order_by("name")


def list_certifications(*, employee_id: str | uuid.UUID) -> QuerySet[Certification]:
    """List certifications for an employee."""
    return Certification.objects.filter(employee_id=employee_id).order_by("-issue_date")


def list_employment_histories(*, employee_id: str | uuid.UUID) -> QuerySet[EmploymentHistory]:
    """List promotion, transfer, and manager mutation history for an employee."""
    return EmploymentHistory.objects.filter(employee_id=employee_id).order_by("-effective_date")


def list_employee_audit_events(
    *, employee_id: str | uuid.UUID, limit: int = 50
) -> QuerySet[EmployeeAuditEvent]:
    """Return audit log trail for an employee."""
    return EmployeeAuditEvent.objects.filter(employee_id=employee_id).order_by("-timestamp")[:limit]


def get_active_resignation(*, employee_id: str | uuid.UUID) -> Optional[EmployeeResignation]:
    """Retrieve active pending/approved resignation request for an employee."""
    return EmployeeResignation.objects.filter(
        employee_id=employee_id,
        status__in=[EmployeeResignation.ResignationStatus.PENDING, EmployeeResignation.ResignationStatus.APPROVED],
    ).first()


def get_org_chart_hierarchy(*, employee_id: str | uuid.UUID, max_depth: int = MAX_HIERARCHY_DEPTH) -> dict:
    """Build a recursive organizational reporting hierarchy tree for an employee."""

    def build_tree(emp: Employee, current_depth: int) -> dict:
        node = {
            "id": str(emp.id),
            "employee_id": emp.employee_id,
            "display_name": emp.display_name,
            "official_email": emp.official_email,
            "designation_name": emp.designation.name if emp.designation else "",
            "department_name": emp.department.name if emp.department else "",
            "branch_name": emp.branch.name if emp.branch else "",
            "employment_status": emp.employment_status,
            "direct_reports": [],
        }

        if current_depth < max_depth:
            direct_reports = Employee.objects.select_related(
                "designation", "department", "branch"
            ).filter(reporting_manager=emp)
            node["direct_reports"] = [
                build_tree(report, current_depth + 1) for report in direct_reports
            ]

        return node

    root_emp = get_employee(employee_id=employee_id)
    if not root_emp:
        return {}
    return build_tree(root_emp, current_depth=1)


def get_manager_assignment(*, employee_id: str | uuid.UUID, manager_type: str = "PRIMARY") -> Optional[ManagerAssignment]:
    """Retrieve active ManagerAssignment record for an employee."""
    try:
        return ManagerAssignment.objects.select_related("employee", "manager").get(
            employee_id=employee_id, manager_type=manager_type, is_active=True
        )
    except ManagerAssignment.DoesNotExist:
        return None


def list_workforce_assignments(*, employee_id: str | uuid.UUID) -> QuerySet[WorkforceAssignment]:
    """Return workforce assignment history trail for an employee."""
    return WorkforceAssignment.objects.filter(employee_id=employee_id).order_by("-effective_date")


def get_organization_tree(*, organization_id: str | uuid.UUID) -> dict:
    """Build full organization workforce tree grouped by Branches and Departments."""
    from apps.organizations import selectors as org_selectors

    org = org_selectors.get_organization(organization_id=organization_id)
    if not org:
        return {}

    branches = org_selectors.list_branches(organization_id=organization_id)
    branch_nodes = []
    for b in branches:
        departments = org_selectors.list_departments(organization_id=organization_id, branch_id=b.id)
        dept_nodes = []
        for d in departments:
            emp_count = Employee.objects.filter(department_id=d.id, employment_status="ACTIVE").count()
            dept_nodes.append({
                "id": str(d.id),
                "code": d.code,
                "name": d.name,
                "active_employee_count": emp_count,
            })
        branch_nodes.append({
            "id": str(b.id),
            "code": b.code,
            "name": b.name,
            "departments": dept_nodes,
        })

    return {
        "id": str(org.id),
        "code": org.code,
        "name": org.name,
        "branches": branch_nodes,
    }


def get_department_tree(*, organization_id: str | uuid.UUID) -> list[dict]:
    """Build recursive department hierarchy tree for an organization."""
    from apps.organizations import selectors as org_selectors

    departments = org_selectors.list_departments(organization_id=organization_id)
    dept_map = {d.id: d for d in departments}

    nodes = []
    for d in departments:
        emp_count = Employee.objects.filter(department_id=d.id).count()
        nodes.append({
            "id": str(d.id),
            "code": d.code,
            "name": d.name,
            "parent_id": str(d.parent_department_id) if d.parent_department_id else None,
            "employee_count": emp_count,
        })
    return nodes


def get_team_tree(*, organization_id: str | uuid.UUID) -> list[dict]:
    """Build team structure tree for an organization with active member counts."""
    from apps.organizations import selectors as org_selectors

    teams = org_selectors.list_teams(organization_id=organization_id)
    team_nodes = []
    for t in teams:
        members = Employee.objects.filter(team_id=t.id).values("id", "employee_id", "first_name", "last_name", "official_email")
        team_nodes.append({
            "id": str(t.id),
            "code": t.code,
            "name": t.name,
            "department_name": t.department.name,
            "member_count": len(members),
            "members": list(members),
        })
    return team_nodes


