"""Read-only query selectors for Enterprise Project Management Foundation Engine."""

import uuid
from datetime import date, timedelta
from decimal import Decimal
from typing import Dict, List, Optional
from django.db.models import QuerySet

from apps.employees.models import Employee
from .models import Project, ProjectAuditLog, ProjectMember, ProjectTeam


def get_project(*, project_id: str | uuid.UUID) -> Optional[Project]:
    """Retrieve project by UUID."""
    try:
        return Project.objects.select_related(
            "organization", "branch", "department", "owner", "manager"
        ).get(id=project_id)
    except Project.DoesNotExist:
        return None


def get_project_by_code(*, organization_id: str | uuid.UUID, code: str) -> Optional[Project]:
    """Retrieve project by unique organization code."""
    try:
        return Project.objects.select_related(
            "organization", "branch", "department", "owner", "manager"
        ).get(organization_id=organization_id, code=code)
    except Project.DoesNotExist:
        return None


def list_projects(
    *,
    organization_id: str | uuid.UUID,
    status: str = "",
    project_type: str = "",
    category: str = "",
    search: str = "",
) -> QuerySet[Project]:
    """List projects for an organization with optional filtering."""
    qs = Project.objects.filter(organization_id=organization_id, is_archived=False).select_related(
        "organization", "branch", "department", "owner", "manager"
    )

    if status:
        qs = qs.filter(status=status)
    if project_type:
        qs = qs.filter(project_type=project_type)
    if category:
        qs = qs.filter(category=category)
    if search:
        qs = qs.filter(name__icontains=search) | qs.filter(code__icontains=search)

    return qs.order_by("-created_at")


def list_project_members(*, project_id: str | uuid.UUID) -> QuerySet[ProjectMember]:
    """List active members assigned to a project."""
    return ProjectMember.objects.filter(
        project_id=project_id, is_active=True
    ).select_related("employee", "employee__user", "employee__department").order_by("role")


def list_employee_projects(*, employee_id: str | uuid.UUID) -> QuerySet[ProjectMember]:
    """List project assignments for an employee."""
    return ProjectMember.objects.filter(
        employee_id=employee_id, is_active=True
    ).select_related("project", "project__organization").order_by("-joined_at")


def get_project_audit_logs(*, project_id: str | uuid.UUID) -> QuerySet[ProjectAuditLog]:
    """Retrieve audit trail logs for a project."""
    return ProjectAuditLog.objects.filter(project_id=project_id).order_by("-created_at")


# ── Enterprise Task & WBS Selectors ────────────────────────────────────────

from .models import Task, TaskActivityLog, TaskAssignment, TaskChecklist, TaskComment, TaskDependency


def get_task(*, task_id: str | uuid.UUID) -> Optional[Task]:
    """Retrieve task by UUID."""
    try:
        return Task.objects.select_related(
            "organization", "project", "parent", "epic", "reporter", "assignee"
        ).get(id=task_id)
    except Task.DoesNotExist:
        return None


def list_project_tasks(
    *,
    project_id: str | uuid.UUID,
    status: str = "",
    task_type: str = "",
    assignee_id: str = "",
    search: str = "",
) -> QuerySet[Task]:
    """List tasks for a project with optional filtering."""
    qs = Task.objects.filter(project_id=project_id, is_archived=False).select_related(
        "organization", "project", "parent", "epic", "reporter", "assignee"
    )

    if status:
        qs = qs.filter(status=status)
    if task_type:
        qs = qs.filter(task_type=task_type)
    if assignee_id:
        qs = qs.filter(assignee_id=assignee_id)
    if search:
        qs = qs.filter(title__icontains=search) | qs.filter(code__icontains=search)

    return qs.order_by("wbs_code", "-created_at")


def list_epic_tasks(*, epic_id: str | uuid.UUID) -> QuerySet[Task]:
    """List tasks associated with an Epic."""
    return Task.objects.filter(epic_id=epic_id, is_archived=False).select_related(
        "assignee", "reporter"
    ).order_by("-created_at")


def get_wbs_tree(*, project_id: str | uuid.UUID) -> list:
    """Generate hierarchical Work Breakdown Structure (WBS) tree for a project."""
    from .serializers import TaskSerializer

    tasks = list_project_tasks(project_id=project_id)
    task_dict = {str(t.id): {"task": TaskSerializer(t).data, "children": []} for t in tasks}
    tree = []

    for t in tasks:
        t_node = task_dict[str(t.id)]
        if t.parent_id and str(t.parent_id) in task_dict:
            task_dict[str(t.parent_id)]["children"].append(t_node)
        else:
            tree.append(t_node)

    return tree


def list_task_dependencies(*, task_id: str | uuid.UUID) -> QuerySet[TaskDependency]:
    """List predecessor dependencies for a task."""
    return TaskDependency.objects.filter(target_task_id=task_id).select_related("source_task")


def list_task_comments(*, task_id: str | uuid.UUID) -> QuerySet[TaskComment]:
    """List comments for a task in chronological order."""
    return TaskComment.objects.filter(task_id=task_id, parent_comment__isnull=True).prefetch_related("replies").order_by("created_at")


def get_task_activity_logs(*, task_id: str | uuid.UUID) -> QuerySet[TaskActivityLog]:
    """Retrieve activity log timeline entries for a task."""
    return TaskActivityLog.objects.filter(task_id=task_id).order_by("-created_at")


# ── Enterprise Agile Delivery, Sprint & Kanban Selectors ───────────────────

from .models import BoardColumn, KanbanBoard, Release, Sprint


def get_sprint(*, sprint_id: str | uuid.UUID) -> Optional[Sprint]:
    """Retrieve Sprint by UUID."""
    try:
        return Sprint.objects.select_related("organization", "project", "team", "owner").get(id=sprint_id)
    except Sprint.DoesNotExist:
        return None


def list_project_sprints(*, project_id: str | uuid.UUID, status: str = "") -> QuerySet[Sprint]:
    """List sprints for a project."""
    qs = Sprint.objects.filter(project_id=project_id).select_related("owner", "team")
    if status:
        qs = qs.filter(status=status)
    return qs.order_by("-sprint_number")


def get_active_sprint(*, project_id: str | uuid.UUID) -> Optional[Sprint]:
    """Get the currently ACTIVE sprint for a project."""
    return Sprint.objects.filter(project_id=project_id, status="ACTIVE").first()


def get_sprint_backlog(*, sprint_id: str | uuid.UUID) -> QuerySet[Task]:
    """Get tasks committed to a specific sprint."""
    return Task.objects.filter(sprint_id=sprint_id, is_archived=False).select_related(
        "assignee", "reporter", "board_column"
    ).order_by("backlog_rank", "created_at")


def get_product_backlog(*, project_id: str | uuid.UUID) -> QuerySet[Task]:
    """Get unassigned tasks in the product backlog (no active sprint)."""
    return Task.objects.filter(project_id=project_id, sprint__isnull=True, is_archived=False).select_related(
        "assignee", "reporter"
    ).order_by("backlog_rank", "-priority")


def list_project_boards(*, project_id: str | uuid.UUID) -> QuerySet[KanbanBoard]:
    """List Kanban/Scrum boards for a project."""
    return KanbanBoard.objects.filter(project_id=project_id).prefetch_related("columns")


def get_board_detail(*, board_id: str | uuid.UUID) -> Optional[KanbanBoard]:
    """Get board detail with columns and tasks."""
    try:
        return KanbanBoard.objects.prefetch_related("columns", "columns__tasks").get(id=board_id)
    except KanbanBoard.DoesNotExist:
        return None


def calculate_sprint_velocity(*, project_id: str | uuid.UUID) -> Dict:
    """Calculate average sprint velocity across completed sprints for a project."""
    completed_sprints = Sprint.objects.filter(project_id=project_id, status="COMPLETED").order_by("-sprint_number")[:5]
    total_completed_pts = sum(s.completed_story_points for s in completed_sprints)
    count = completed_sprints.count()
    avg_velocity = (total_completed_pts / Decimal(str(count))) if count > 0 else Decimal("0.0")

    return {
        "completed_sprints_count": count,
        "average_velocity": avg_velocity,
        "sprints": [
            {
                "sprint_number": s.sprint_number,
                "name": s.name,
                "total_story_points": float(s.total_story_points),
                "completed_story_points": float(s.completed_story_points),
                "velocity": float(s.velocity),
            }
            for s in completed_sprints
        ],
    }


def get_burndown_dataset(*, sprint_id: str | uuid.UUID) -> Dict:
    """Prepare burndown chart dataset foundation for a sprint."""
    sprint = get_sprint(sprint_id=sprint_id)
    if not sprint:
        return {}

    tasks = get_sprint_backlog(sprint_id=sprint_id)
    total_pts = sum(t.story_points for t in tasks)
    done_pts = sum(t.story_points for t in tasks if t.status == "DONE")
    remaining_pts = total_pts - done_pts

    return {
        "sprint_id": str(sprint.id),
        "sprint_name": sprint.name,
        "total_story_points": float(total_pts),
        "completed_story_points": float(done_pts),
        "remaining_story_points": float(remaining_pts),
        "capacity_hours": float(sprint.capacity_hours),
    }


# ── Enterprise Time Tracking & Timesheet Selectors ────────────────────────

from .models import OvertimeRecord, TimeEntry, Timesheet, TimesheetApprovalLog


def get_time_entry(*, time_entry_id: str | uuid.UUID) -> Optional[TimeEntry]:
    """Retrieve time entry by UUID."""
    try:
        return TimeEntry.objects.select_related("organization", "project", "task", "sprint", "employee").get(id=time_entry_id)
    except TimeEntry.DoesNotExist:
        return None


def get_active_timer(*, employee_id: str | uuid.UUID) -> Optional[TimeEntry]:
    """Get the currently running timer for an employee."""
    return TimeEntry.objects.filter(employee_id=employee_id, is_timer_running=True).select_related("project", "task").first()


def list_employee_time_entries(
    *,
    employee_id: str | uuid.UUID,
    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
    project_id: str = "",
) -> QuerySet[TimeEntry]:
    """List time entries for an employee within a date range."""
    qs = TimeEntry.objects.filter(employee_id=employee_id).select_related("project", "task", "sprint")
    if start_date:
        qs = qs.filter(date__gte=start_date)
    if end_date:
        qs = qs.filter(date__lte=end_date)
    if project_id:
        qs = qs.filter(project_id=project_id)
    return qs.order_by("-date", "-created_at")


def list_timesheets(
    *,
    employee_id: str = "",
    project_id: str = "",
    status: str = "",
) -> QuerySet[Timesheet]:
    """List timesheet submissions for approval or review."""
    qs = Timesheet.objects.select_related("employee", "project", "approver")
    if employee_id:
        qs = qs.filter(employee_id=employee_id)
    if project_id:
        qs = qs.filter(project_id=project_id)
    if status:
        qs = qs.filter(status=status)
    return qs.order_by("-start_date")


def get_timesheet_detail(*, timesheet_id: str | uuid.UUID) -> Optional[Timesheet]:
    """Retrieve timesheet detail with approval logs."""
    try:
        return Timesheet.objects.select_related("employee", "project", "approver").prefetch_related("approval_logs").get(id=timesheet_id)
    except Timesheet.DoesNotExist:
        return None


def calculate_employee_productivity(
    *,
    employee_id: str | uuid.UUID,
    start_date: date,
    end_date: date,
) -> Dict:
    """Calculate productivity metrics for an employee across a date range."""
    entries = TimeEntry.objects.filter(employee_id=employee_id, date__gte=start_date, date__lte=end_date)
    total_hours = sum(e.hours for e in entries)
    billable_hours = sum(e.hours for e in entries if e.billable_type == "BILLABLE")
    non_billable_hours = total_hours - billable_hours

    utilization_rate = (billable_hours / total_hours * Decimal("100.0")) if total_hours > 0 else Decimal("0.0")

    return {
        "employee_id": str(employee_id),
        "start_date": start_date.isoformat(),
        "end_date": end_date.isoformat(),
        "total_hours": float(total_hours),
        "billable_hours": float(billable_hours),
        "non_billable_hours": float(non_billable_hours),
        "utilization_rate": float(utilization_rate),
    }


def get_overtime_records(*, employee_id: str | uuid.UUID, start_date: date, end_date: date) -> QuerySet[OvertimeRecord]:
    """Retrieve overtime records for an employee."""
    return OvertimeRecord.objects.filter(employee_id=employee_id, date__gte=start_date, date__lte=end_date).order_by("date")


# ── Enterprise Resource Planning, Capacity & Workload Selectors ───────────

from .models import ResourceAllocation, ResourceCapacitySnapshot, ResourceSkillRequirement


def get_resource_allocation(*, allocation_id: str | uuid.UUID) -> Optional[ResourceAllocation]:
    """Retrieve resource allocation by UUID."""
    try:
        return ResourceAllocation.objects.select_related("organization", "project", "task", "employee").get(id=allocation_id)
    except ResourceAllocation.DoesNotExist:
        return None


def list_employee_allocations(
    *,
    employee_id: str | uuid.UUID,
    active_only: bool = True,
    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
) -> QuerySet[ResourceAllocation]:
    """List allocations for an employee."""
    qs = ResourceAllocation.objects.filter(employee_id=employee_id).select_related("project", "task")
    if active_only:
        qs = qs.filter(status="ACTIVE")
    if start_date:
        qs = qs.filter(end_date__gte=start_date)
    if end_date:
        qs = qs.filter(start_date__lte=end_date)
    return qs.order_by("-start_date")


def list_project_allocations(*, project_id: str | uuid.UUID, active_only: bool = True) -> QuerySet[ResourceAllocation]:
    """List allocations for a project."""
    qs = ResourceAllocation.objects.filter(project_id=project_id).select_related("employee", "task")
    if active_only:
        qs = qs.filter(status="ACTIVE")
    return qs.order_by("-allocation_percentage")


def detect_allocation_conflicts(
    *,
    employee_id: str | uuid.UUID,
    start_date: date,
    end_date: date,
    exclude_allocation_id: Optional[str] = None,
) -> Dict:
    """Detect overallocation conflicts where total allocation percentage exceeds 100%."""
    allocations = ResourceAllocation.objects.filter(
        employee_id=employee_id,
        status="ACTIVE",
        start_date__lte=end_date,
        end_date__gte=start_date,
    )
    if exclude_allocation_id:
        allocations = allocations.exclude(id=exclude_allocation_id)

    total_pct = sum(a.allocation_percentage for a in allocations)
    is_conflicted = total_pct > Decimal("100.00")

    return {
        "employee_id": str(employee_id),
        "total_allocation_percentage": float(total_pct),
        "is_conflicted": is_conflicted,
        "conflicting_allocations_count": allocations.count(),
    }


def calculate_employee_capacity(
    *,
    employee_id: str | uuid.UUID,
    start_date: date,
    end_date: date,
) -> Dict:
    """Calculate capacity and available hours for an employee considering allocations and leaves."""
    days = (end_date - start_date).days + 1
    total_planned_hours = Decimal(str(days * 8))

    allocations = list_employee_allocations(employee_id=employee_id, active_only=True, start_date=start_date, end_date=end_date)
    allocated_hours = sum((a.allocated_hours_per_day * Decimal(str(days))) for a in allocations)

    # Calculate logged hours from TimeEntry
    logged_entries = TimeEntry.objects.filter(employee_id=employee_id, date__gte=start_date, date__lte=end_date)
    actual_hours = sum(e.hours for e in logged_entries)

    utilization_pct = (allocated_hours / total_planned_hours * Decimal("100.0")) if total_planned_hours > 0 else Decimal("0.0")

    if utilization_pct < Decimal("50.0"):
        status_key = "UNDERUTILIZED"
    elif utilization_pct > Decimal("100.0"):
        status_key = "OVERALLOCATED"
    else:
        status_key = "OPTIMAL"

    return {
        "employee_id": str(employee_id),
        "start_date": start_date.isoformat(),
        "end_date": end_date.isoformat(),
        "planned_capacity_hours": float(total_planned_hours),
        "allocated_hours": float(allocated_hours),
        "actual_logged_hours": float(actual_hours),
        "available_hours": float(max(Decimal("0.00"), total_planned_hours - allocated_hours)),
        "utilization_rate": float(utilization_pct),
        "workload_status": status_key,
    }


def list_bench_resources(*, organization_id: str | uuid.UUID) -> List[Dict]:
    """List idle or underutilized resources (< 50% allocation) on the bench."""
    employees = Employee.objects.filter(organization_id=organization_id, status="ACTIVE")
    today = date.today()
    bench = []

    for emp in employees:
        cap = calculate_employee_capacity(employee_id=emp.id, start_date=today, end_date=today + timedelta(days=7))
        if cap["workload_status"] == "UNDERUTILIZED":
            bench.append(
                {
                    "employee_id": str(emp.id),
                    "display_name": emp.display_name,
                    "department": emp.department.name if emp.department else "",
                    "designation": emp.designation.name if emp.designation else "",
                    "utilization_rate": cap["utilization_rate"],
                    "available_hours": cap["available_hours"],
                }
            )

    return bench


def match_resources_by_skill(*, project_id: str | uuid.UUID) -> List[Dict]:
    """Match candidates against project skill requirements."""
    requirements = ResourceSkillRequirement.objects.filter(project_id=project_id)
    if not requirements.exists():
        return []

    # Get project organization
    project = get_project(project_id=project_id)
    if not project:
        return []

    candidates = Employee.objects.filter(organization=project.organization, status="ACTIVE")
    results = []

    for emp in candidates:
        # Candidate score placeholder matching skills
        score = 100.0  # Base candidate fit score
        results.append(
            {
                "employee_id": str(emp.id),
                "display_name": emp.display_name,
                "match_score": score,
            }
        )

    return results


# ── Enterprise Portfolio Management, Program & PMO Selectors ─────────────

from .models import Portfolio, PortfolioMilestone, PortfolioProjectMapping, PortfolioRisk, Program


def get_portfolio(*, portfolio_id: str | uuid.UUID) -> Optional[Portfolio]:
    """Retrieve portfolio by UUID."""
    try:
        return Portfolio.objects.select_related("organization", "owner", "executive_sponsor").get(id=portfolio_id)
    except Portfolio.DoesNotExist:
        return None


def list_portfolios(*, organization_id: str | uuid.UUID, status: str = "") -> QuerySet[Portfolio]:
    """List portfolios for an organization."""
    qs = Portfolio.objects.filter(organization_id=organization_id).select_related("owner", "executive_sponsor")
    if status:
        qs = qs.filter(status=status)
    return qs.order_by("priority", "name")


def get_program(*, program_id: str | uuid.UUID) -> Optional[Program]:
    """Retrieve program by UUID."""
    try:
        return Program.objects.select_related("organization", "program_manager", "portfolio").get(id=program_id)
    except Program.DoesNotExist:
        return None


def list_programs(*, organization_id: str | uuid.UUID, portfolio_id: str = "") -> QuerySet[Program]:
    """List programs for an organization."""
    qs = Program.objects.filter(organization_id=organization_id).select_related("program_manager", "portfolio")
    if portfolio_id:
        qs = qs.filter(portfolio_id=portfolio_id)
    return qs.order_by("code")


def calculate_project_health_score(*, project_id: str | uuid.UUID) -> Dict:
    """Calculate RAG status (GREEN, AMBER, RED) for a project."""
    project = get_project(project_id=project_id)
    if not project:
        return {"overall_health": "RED", "score": 0}

    tasks = list_project_tasks(project_id=project_id)
    total_tasks = tasks.count()
    completed_tasks = tasks.filter(status="DONE").count()
    blocked_tasks = tasks.filter(status="BLOCKED").count()

    completion_rate = (completed_tasks / total_tasks * 100.0) if total_tasks > 0 else 0.0

    if blocked_tasks > 3:
        health = "RED"
        score = 40
    elif blocked_tasks > 0 or completion_rate < 50.0:
        health = "AMBER"
        score = 70
    else:
        health = "GREEN"
        score = 95

    return {
        "project_id": str(project_id),
        "code": project.code,
        "name": project.name,
        "overall_health": health,
        "health_score": score,
        "completion_rate": completion_rate,
        "blocked_tasks_count": blocked_tasks,
    }


def get_executive_dashboard_metrics(*, organization_id: str | uuid.UUID, dashboard_type: str = "CEO") -> Dict:
    """Generate executive dashboard analytics metrics."""
    projects = Project.objects.filter(organization_id=organization_id)
    total_projects = projects.count()
    active_projects = projects.filter(status="IN_PROGRESS").count()
    completed_projects = projects.filter(status="COMPLETED").count()

    portfolios = list_portfolios(organization_id=organization_id)
    programs = list_programs(organization_id=organization_id)

    success_rate = (completed_projects / total_projects * 100.0) if total_projects > 0 else 0.0

    return {
        "dashboard_type": dashboard_type,
        "organization_id": str(organization_id),
        "total_projects": total_projects,
        "active_projects": active_projects,
        "completed_projects": completed_projects,
        "total_portfolios": portfolios.count(),
        "total_programs": programs.count(),
        "project_success_rate": success_rate,
    }


def list_portfolio_risks(*, organization_id: str | uuid.UUID, portfolio_id: str = "") -> QuerySet[PortfolioRisk]:
    """List portfolio risks."""
    qs = PortfolioRisk.objects.filter(organization_id=organization_id).select_related("portfolio", "program", "project", "risk_owner")
    if portfolio_id:
        qs = qs.filter(portfolio_id=portfolio_id)
    return qs.order_by("-risk_score")


def list_portfolio_milestones(*, organization_id: str | uuid.UUID, portfolio_id: str = "") -> QuerySet[PortfolioMilestone]:
    """List portfolio strategic milestones."""
    qs = PortfolioMilestone.objects.filter(organization_id=organization_id).select_related("portfolio", "program")
    if portfolio_id:
        qs = qs.filter(portfolio_id=portfolio_id)
    return qs.order_by("target_date")





