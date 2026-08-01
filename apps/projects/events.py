"""Domain events for Enterprise Project Management Foundation Engine."""

import logging
from dataclasses import dataclass
from typing import Any, Dict

logger = logging.getLogger("nexora.projects.events")


@dataclass
class BaseProjectEvent:
    """Base project domain event schema."""

    event_id: str = ""
    event_type: str = ""
    organization_id: str = ""
    project_id: str = ""
    timestamp: str = ""
    actor_id: str = ""
    metadata: Dict[str, Any] = None


@dataclass
class ProjectCreated(BaseProjectEvent):
    """Published when a project is created."""

    code: str = ""
    name: str = ""
    project_type: str = ""


@dataclass
class ProjectActivated(BaseProjectEvent):
    """Published when a project state moves to IN_PROGRESS."""

    previous_status: str = ""


@dataclass
class ProjectPaused(BaseProjectEvent):
    """Published when a project state moves to ON_HOLD."""

    reason: str = ""


@dataclass
class ProjectCompleted(BaseProjectEvent):
    """Published when a project is completed."""

    completion_date: str = ""


@dataclass
class ProjectArchived(BaseProjectEvent):
    """Published when a project is archived."""

    archived_by_user_id: str = ""


@dataclass
class ProjectMemberAdded(BaseProjectEvent):
    """Published when a member is assigned to a project."""

    employee_id: str = ""
    role: str = ""


@dataclass
class ProjectMemberRemoved(BaseProjectEvent):
    """Published when a member is removed from a project."""

    employee_id: str = ""


@dataclass
class ProjectSettingsUpdated(BaseProjectEvent):
    """Published when project settings are updated."""

    updated_fields: str = ""


@dataclass
class TaskCreated(BaseProjectEvent):
    """Published when a task is created."""

    task_id: str = ""
    task_code: str = ""
    title: str = ""
    task_type: str = ""


@dataclass
class TaskUpdated(BaseProjectEvent):
    """Published when a task is updated."""

    task_id: str = ""
    task_code: str = ""


@dataclass
class TaskAssigned(BaseProjectEvent):
    """Published when a task is assigned to an employee."""

    task_id: str = ""
    assignee_id: str = ""
    role: str = ""


@dataclass
class TaskCompleted(BaseProjectEvent):
    """Published when a task status moves to DONE."""

    task_id: str = ""
    completion_date: str = ""


@dataclass
class TaskBlocked(BaseProjectEvent):
    """Published when a task status moves to BLOCKED."""

    task_id: str = ""
    block_reason: str = ""


@dataclass
class TaskReopened(BaseProjectEvent):
    """Published when a completed task is reopened."""

    task_id: str = ""


@dataclass
class TaskArchived(BaseProjectEvent):
    """Published when a task is archived."""

    task_id: str = ""


@dataclass
class TaskCommentAdded(BaseProjectEvent):
    """Published when a comment is posted on a task."""

    task_id: str = ""
    comment_id: str = ""


@dataclass
class TaskChecklistCompleted(BaseProjectEvent):
    """Published when all items in a task checklist are marked complete."""

    task_id: str = ""


@dataclass
class SprintCreated(BaseProjectEvent):
    """Published when a sprint is created."""

    sprint_id: str = ""
    sprint_number: int = 0
    name: str = ""


@dataclass
class SprintStarted(BaseProjectEvent):
    """Published when a sprint moves to ACTIVE status."""

    sprint_id: str = ""
    start_date: str = ""
    end_date: str = ""


@dataclass
class SprintCompleted(BaseProjectEvent):
    """Published when a sprint is completed."""

    sprint_id: str = ""
    completed_points: str = "0.0"
    velocity: str = "0.0"


@dataclass
class TaskMoved(BaseProjectEvent):
    """Published when a task is moved between board columns or sprints."""

    task_id: str = ""
    from_column_id: str = ""
    to_column_id: str = ""


@dataclass
class BacklogUpdated(BaseProjectEvent):
    """Published when backlog order or ranking is updated."""

    project_id: str = ""


@dataclass
class VelocityCalculated(BaseProjectEvent):
    """Published when sprint velocity metrics are recalculated."""

    sprint_id: str = ""
    velocity: str = "0.0"


@dataclass
class BoardUpdated(BaseProjectEvent):
    """Published when a kanban board layout or WIP limit is updated."""

    board_id: str = ""


@dataclass
class TimeStarted(BaseProjectEvent):
    """Published when a timer is started."""

    time_entry_id: str = ""
    employee_id: str = ""
    task_id: str = ""


@dataclass
class TimeStopped(BaseProjectEvent):
    """Published when a timer is stopped."""

    time_entry_id: str = ""
    employee_id: str = ""
    hours: str = "0.00"


@dataclass
class WorklogCreated(BaseProjectEvent):
    """Published when a worklog entry is created."""

    time_entry_id: str = ""
    employee_id: str = ""
    hours: str = "0.00"


@dataclass
class WorklogUpdated(BaseProjectEvent):
    """Published when a worklog entry is updated."""

    time_entry_id: str = ""


@dataclass
class TimesheetSubmitted(BaseProjectEvent):
    """Published when a timesheet is submitted for approval."""

    timesheet_id: str = ""
    employee_id: str = ""
    total_hours: str = "0.00"


@dataclass
class TimesheetApproved(BaseProjectEvent):
    """Published when a timesheet is approved."""

    timesheet_id: str = ""
    approver_id: str = ""


@dataclass
class TimesheetRejected(BaseProjectEvent):
    """Published when a timesheet is rejected."""

    timesheet_id: str = ""
    approver_id: str = ""
    rejection_reason: str = ""


@dataclass
class TimeEntryValidated(BaseProjectEvent):
    """Published when a time entry passes validation checks."""

    time_entry_id: str = ""


@dataclass
class ResourceAllocated(BaseProjectEvent):
    """Published when a resource is allocated to a project or task."""

    allocation_id: str = ""
    employee_id: str = ""
    allocation_percentage: str = "100.0"


@dataclass
class AllocationUpdated(BaseProjectEvent):
    """Published when resource allocation parameters are updated."""

    allocation_id: str = ""


@dataclass
class AllocationRemoved(BaseProjectEvent):
    """Published when resource allocation is removed."""

    allocation_id: str = ""


@dataclass
class CapacityCalculated(BaseProjectEvent):
    """Published when resource capacity is calculated for an employee or team."""

    employee_id: str = ""
    available_hours: str = "0.00"


@dataclass
class ConflictDetected(BaseProjectEvent):
    """Published when resource double-booking or overallocation is detected."""

    employee_id: str = ""
    total_allocation_pct: str = "0.0"


@dataclass
class BenchAssigned(BaseProjectEvent):
    """Published when an employee is moved to bench status."""

    employee_id: str = ""


@dataclass
class ForecastPrepared(BaseProjectEvent):
    """Published when workforce capacity forecast dataset is generated."""

    organization_id: str = ""


@dataclass
class PortfolioCreated(BaseProjectEvent):
    """Published when a portfolio is created."""

    portfolio_id: str = ""
    code: str = ""
    name: str = ""


@dataclass
class PortfolioUpdated(BaseProjectEvent):
    """Published when portfolio properties are updated."""

    portfolio_id: str = ""


@dataclass
class ProgramCreated(BaseProjectEvent):
    """Published when a program is created."""

    program_id: str = ""
    code: str = ""
    name: str = ""


@dataclass
class MilestoneCompleted(BaseProjectEvent):
    """Published when a strategic milestone is completed."""

    milestone_id: str = ""


@dataclass
class PortfolioHealthCalculated(BaseProjectEvent):
    """Published when portfolio health metrics are recalculated."""

    portfolio_id: str = ""
    health_status: str = "GREEN"


@dataclass
class DashboardGenerated(BaseProjectEvent):
    """Published when an executive dashboard metrics dataset is generated."""

    dashboard_type: str = "CEO"


@dataclass
class RiskEscalated(BaseProjectEvent):
    """Published when a portfolio or program risk is escalated."""

    risk_id: str = ""
    risk_score: int = 0







def publish_project_event(event: BaseProjectEvent) -> None:
    """Publish internal project domain event."""
    logger.info(
        "Project Event Published [%s] for Org %s: Event ID %s (Project: %s)",
        event.event_type,
        event.organization_id,
        event.event_id,
        event.project_id,
    )
