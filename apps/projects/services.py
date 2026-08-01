"""Domain state mutation service functions for Enterprise Project Management Foundation Engine."""

import logging
import uuid
from datetime import date
from decimal import Decimal
from typing import Dict, List, Optional
from django.db import models, transaction
from django.utils import timezone

from apps.employees.models import Employee
from apps.organizations.models import Branch, Department, Organization

from .enums import ProjectMemberRole, ProjectStatus, ProjectType
from .events import (
    ProjectActivated,
    ProjectArchived,
    ProjectCompleted,
    ProjectCreated,
    ProjectMemberAdded,
    ProjectMemberRemoved,
    ProjectPaused,
    ProjectSettingsUpdated,
    publish_project_event,
)
from .exceptions import ProjectLifecycleError, ProjectValidationError
from .models import Project, ProjectAuditLog, ProjectMember

logger = logging.getLogger("nexora.projects.services")


def _record_audit_log(
    *,
    project: Project,
    action: str,
    description: str,
    user_id: str = "",
    changes: Optional[Dict] = None,
) -> ProjectAuditLog:
    """Record an audit log entry for a project."""
    return ProjectAuditLog.objects.create(
        project=project,
        actor_user_id=user_id,
        action=action,
        description=description,
        changes_json=changes or {},
    )


@transaction.atomic
def create_project(
    *,
    organization: Organization,
    owner: Employee,
    manager: Employee,
    code: str,
    name: str,
    description: str = "",
    project_type: str = ProjectType.INTERNAL,
    category: str = "SOFTWARE",
    priority: str = "MEDIUM",
    risk_level: str = "LOW",
    visibility: str = "ORGANIZATION",
    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
    estimated_budget: Decimal = Decimal("0.00"),
    estimated_hours: Decimal = Decimal("0.00"),
    branch: Optional[Branch] = None,
    department: Optional[Department] = None,
    settings: Optional[Dict] = None,
    user_id: str = "",
) -> Project:
    """Create a new enterprise project and record audit entry."""
    code = code.strip().upper()
    if Project.objects.filter(organization=organization, code=code).exists():
        raise ProjectValidationError(f"Project with code '{code}' already exists in organization.")

    default_settings = {
        "working_days": ["MON", "TUE", "WED", "THU", "FRI"],
        "timezone": "UTC",
        "task_prefix": code,
    }
    if settings:
        default_settings.update(settings)

    project = Project.objects.create(
        organization=organization,
        branch=branch,
        department=department,
        owner=owner,
        manager=manager,
        code=code,
        name=name,
        description=description,
        project_type=project_type,
        category=category,
        status=ProjectStatus.DRAFT,
        priority=priority,
        risk_level=risk_level,
        visibility=visibility,
        start_date=start_date,
        end_date=end_date,
        estimated_budget=estimated_budget,
        estimated_hours=estimated_hours,
        settings_json=default_settings,
    )

    # Automatically add Owner and Manager as members
    ProjectMember.objects.create(
        project=project,
        employee=owner,
        role=ProjectMemberRole.OWNER,
        allocated_hours_per_week=Decimal("40.00"),
    )
    if manager.id != owner.id:
        ProjectMember.objects.create(
            project=project,
            employee=manager,
            role=ProjectMemberRole.MANAGER,
            allocated_hours_per_week=Decimal("40.00"),
        )

    _record_audit_log(
        project=project,
        action="PROJECT_CREATED",
        description=f"Project '{name}' [{code}] created by user {user_id}.",
        user_id=user_id,
    )

    publish_project_event(
        ProjectCreated(
            event_id=str(uuid.uuid4()),
            event_type="PROJECT_CREATED",
            organization_id=str(organization.id),
            project_id=str(project.id),
            code=code,
            name=name,
            project_type=project_type,
        )
    )

    logger.info("Project created: %s [%s] for Org %s.", name, code, organization.code)
    return project


@transaction.atomic
def activate_project(*, project: Project, user_id: str = "") -> Project:
    """Transition project status to IN_PROGRESS."""
    if project.status not in [ProjectStatus.DRAFT, ProjectStatus.PLANNING, ProjectStatus.APPROVED, ProjectStatus.ON_HOLD]:
        raise ProjectLifecycleError(f"Cannot activate project from status '{project.status}'.")

    prev_status = project.status
    project.status = ProjectStatus.IN_PROGRESS
    project.save(update_fields=["status", "updated_at"])

    _record_audit_log(
        project=project,
        action="PROJECT_ACTIVATED",
        description=f"Project status changed from {prev_status} to IN_PROGRESS.",
        user_id=user_id,
        changes={"previous_status": prev_status, "new_status": ProjectStatus.IN_PROGRESS},
    )

    publish_project_event(
        ProjectActivated(
            event_id=str(uuid.uuid4()),
            event_type="PROJECT_ACTIVATED",
            organization_id=str(project.organization_id),
            project_id=str(project.id),
            previous_status=prev_status,
        )
    )

    logger.info("Project %s activated (IN_PROGRESS).", project.code)
    return project


@transaction.atomic
def pause_project(*, project: Project, reason: str = "", user_id: str = "") -> Project:
    """Transition project status to ON_HOLD."""
    if project.status != ProjectStatus.IN_PROGRESS:
        raise ProjectLifecycleError(f"Cannot pause project from status '{project.status}'. Must be IN_PROGRESS.")

    project.status = ProjectStatus.ON_HOLD
    project.save(update_fields=["status", "updated_at"])

    _record_audit_log(
        project=project,
        action="PROJECT_PAUSED",
        description=f"Project paused: {reason}",
        user_id=user_id,
        changes={"reason": reason},
    )

    publish_project_event(
        ProjectPaused(
            event_id=str(uuid.uuid4()),
            event_type="PROJECT_PAUSED",
            organization_id=str(project.organization_id),
            project_id=str(project.id),
            reason=reason,
        )
    )

    logger.info("Project %s paused (ON_HOLD).", project.code)
    return project


@transaction.atomic
def resume_project(*, project: Project, user_id: str = "") -> Project:
    """Resume a paused project back to IN_PROGRESS."""
    if project.status != ProjectStatus.ON_HOLD:
        raise ProjectLifecycleError(f"Cannot resume project from status '{project.status}'. Must be ON_HOLD.")

    return activate_project(project=project, user_id=user_id)


@transaction.atomic
def complete_project(*, project: Project, user_id: str = "") -> Project:
    """Transition project status to COMPLETED."""
    if project.status not in [ProjectStatus.IN_PROGRESS, ProjectStatus.ON_HOLD]:
        raise ProjectLifecycleError(f"Cannot complete project from status '{project.status}'.")

    project.status = ProjectStatus.COMPLETED
    project.save(update_fields=["status", "updated_at"])

    _record_audit_log(
        project=project,
        action="PROJECT_COMPLETED",
        description="Project marked as completed successfully.",
        user_id=user_id,
    )

    publish_project_event(
        ProjectCompleted(
            event_id=str(uuid.uuid4()),
            event_type="PROJECT_COMPLETED",
            organization_id=str(project.organization_id),
            project_id=str(project.id),
            completion_date=date.today().isoformat(),
        )
    )

    logger.info("Project %s completed.", project.code)
    return project


@transaction.atomic
def archive_project(*, project: Project, user_id: str = "") -> Project:
    """Archive project record."""
    project.status = ProjectStatus.ARCHIVED
    project.is_archived = True
    project.is_active = False
    project.save(update_fields=["status", "is_archived", "is_active", "updated_at"])

    _record_audit_log(
        project=project,
        action="PROJECT_ARCHIVED",
        description="Project archived.",
        user_id=user_id,
    )

    publish_project_event(
        ProjectArchived(
            event_id=str(uuid.uuid4()),
            event_type="PROJECT_ARCHIVED",
            organization_id=str(project.organization_id),
            project_id=str(project.id),
            archived_by_user_id=user_id,
        )
    )

    logger.info("Project %s archived.", project.code)
    return project


@transaction.atomic
def restore_project(*, project: Project, user_id: str = "") -> Project:
    """Restore an archived project."""
    if not project.is_archived:
        raise ProjectLifecycleError("Project is not archived.")

    project.is_archived = False
    project.is_active = True
    project.status = ProjectStatus.DRAFT
    project.save(update_fields=["status", "is_archived", "is_active", "updated_at"])

    _record_audit_log(
        project=project,
        action="PROJECT_RESTORED",
        description="Project restored from archive to DRAFT status.",
        user_id=user_id,
    )

    logger.info("Project %s restored.", project.code)
    return project


@transaction.atomic
def add_project_member(
    *,
    project: Project,
    employee: Employee,
    role: str = ProjectMemberRole.DEVELOPER,
    allocated_hours_per_week: Decimal = Decimal("40.00"),
    user_id: str = "",
) -> ProjectMember:
    """Assign an employee as a project member."""
    member, created = ProjectMember.objects.update_or_create(
        project=project,
        employee=employee,
        defaults={
            "role": role,
            "allocated_hours_per_week": allocated_hours_per_week,
            "is_active": True,
            "left_at": None,
        },
    )

    _record_audit_log(
        project=project,
        action="PROJECT_MEMBER_ADDED",
        description=f"Employee {employee.display_name} assigned as {role}.",
        user_id=user_id,
    )

    publish_project_event(
        ProjectMemberAdded(
            event_id=str(uuid.uuid4()),
            event_type="PROJECT_MEMBER_ADDED",
            organization_id=str(project.organization_id),
            project_id=str(project.id),
            employee_id=str(employee.id),
            role=role,
        )
    )

    logger.info("Employee %s added to Project %s as %s.", employee.employee_id, project.code, role)
    return member


@transaction.atomic
def remove_project_member(*, project: Project, employee: Employee, user_id: str = "") -> None:
    """Deactivate member assignment from a project."""
    try:
        member = ProjectMember.objects.get(project=project, employee=employee, is_active=True)
        member.is_active = False
        member.left_at = date.today()
        member.save(update_fields=["is_active", "left_at", "updated_at"])

        _record_audit_log(
            project=project,
            action="PROJECT_MEMBER_REMOVED",
            description=f"Employee {employee.display_name} removed from project.",
            user_id=user_id,
        )

        publish_project_event(
            ProjectMemberRemoved(
                event_id=str(uuid.uuid4()),
                event_type="PROJECT_MEMBER_REMOVED",
                organization_id=str(project.organization_id),
                project_id=str(project.id),
                employee_id=str(employee.id),
            )
        )

        logger.info("Employee %s removed from Project %s.", employee.employee_id, project.code)
    except ProjectMember.DoesNotExist:
        pass


@transaction.atomic
def update_project_settings(*, project: Project, settings_dict: Dict, user_id: str = "") -> Project:
    """Update project settings JSON configuration."""
    current = project.settings_json or {}
    current.update(settings_dict)
    project.settings_json = current
    project.save(update_fields=["settings_json", "updated_at"])

    _record_audit_log(
        project=project,
        action="PROJECT_SETTINGS_UPDATED",
        description="Project configuration settings updated.",
        user_id=user_id,
        changes=settings_dict,
    )

    publish_project_event(
        ProjectSettingsUpdated(
            event_id=str(uuid.uuid4()),
            event_type="PROJECT_SETTINGS_UPDATED",
            organization_id=str(project.organization_id),
            project_id=str(project.id),
            updated_fields=",".join(settings_dict.keys()),
        )
    )

    logger.info("Settings updated for Project %s.", project.code)
    return project


# ── Enterprise Task, WBS & Work Management Services ────────────────────────

from .enums import AssignmentRole, DependencyType, ProjectPriority as TaskPriority, TaskSeverity, TaskStatus, TaskType
from .events import (
    TaskAssigned,
    TaskBlocked,
    TaskChecklistCompleted,
    TaskCommentAdded,
    TaskCompleted,
    TaskCreated,
    TaskReopened,
    TaskUpdated,
)
from .models import (
    Task,
    TaskActivityLog,
    TaskAssignment,
    TaskChecklist,
    TaskComment,
    TaskDependency,
)


def _record_task_activity(
    *,
    task: Task,
    action: str,
    description: str,
    user_id: str = "",
    metadata: Optional[Dict] = None,
) -> TaskActivityLog:
    """Record an activity timeline entry for a task."""
    return TaskActivityLog.objects.create(
        task=task,
        actor_user_id=user_id,
        action=action,
        description=description,
        metadata_json=metadata or {},
    )


def _detect_circular_dependency(source_task: Task, target_task: Task) -> bool:
    """Depth-First Search (DFS) to detect if adding source -> target creates a cycle."""
    if source_task.id == target_task.id:
        return True

    visited = set()
    stack = [target_task.id]

    while stack:
        curr_id = stack.pop()
        if curr_id == source_task.id:
            return True
        if curr_id not in visited:
            visited.add(curr_id)
            successors = TaskDependency.objects.filter(source_task_id=curr_id).values_list("target_task_id", flat=True)
            stack.extend(successors)

    return False


def _compute_wbs_code(project: Project, parent: Optional[Task]) -> str:
    """Generate hierarchical WBS code (e.g. 1.2.1)."""
    if not parent:
        count = Task.objects.filter(project=project, parent__isnull=True).count() + 1
        return str(count)
    else:
        siblings = Task.objects.filter(parent=parent).count() + 1
        return f"{parent.wbs_code}.{siblings}"


@transaction.atomic
def create_task(
    *,
    project: Project,
    reporter: Employee,
    code: str,
    title: str,
    description: str = "",
    task_type: str = TaskType.TASK,
    priority: str = TaskPriority.MEDIUM,
    severity: str = TaskSeverity.MINOR,
    parent: Optional[Task] = None,
    epic: Optional[Task] = None,
    assignee: Optional[Employee] = None,
    story_points: Decimal = Decimal("0.0"),
    estimated_hours: Decimal = Decimal("0.00"),
    start_date: Optional[date] = None,
    due_date: Optional[date] = None,
    user_id: str = "",
) -> Task:
    """Create a new task or WBS subtask and generate WBS code."""
    code = code.strip().upper()
    if Task.objects.filter(project=project, code=code).exists():
        raise ProjectValidationError(f"Task with code '{code}' already exists in project.")

    wbs_code = _compute_wbs_code(project, parent)

    task = Task.objects.create(
        organization=project.organization,
        project=project,
        parent=parent,
        epic=epic,
        reporter=reporter,
        assignee=assignee,
        code=code,
        wbs_code=wbs_code,
        title=title,
        description=description,
        task_type=task_type,
        status=TaskStatus.TODO,
        priority=priority,
        severity=severity,
        story_points=story_points,
        estimated_hours=estimated_hours,
        start_date=start_date,
        due_date=due_date,
    )

    if assignee:
        TaskAssignment.objects.create(
            task=task,
            employee=assignee,
            role=AssignmentRole.ASSIGNEE,
        )

    _record_task_activity(
        task=task,
        action="TASK_CREATED",
        description=f"Task [{code}] '{title}' created.",
        user_id=user_id,
    )

    publish_project_event(
        TaskCreated(
            event_id=str(uuid.uuid4()),
            event_type="TASK_CREATED",
            organization_id=str(project.organization_id),
            project_id=str(project.id),
            task_id=str(task.id),
            task_code=code,
            title=title,
            task_type=task_type,
        )
    )

    logger.info("Task created: %s [%s] in Project %s.", title, code, project.code)
    return task


@transaction.atomic
def update_task_status(*, task: Task, status: str, block_reason: str = "", user_id: str = "") -> Task:
    """Update task execution status and track completion timestamp."""
    prev_status = task.status
    task.status = status

    if status == TaskStatus.DONE:
        task.completed_at = timezone.now()
        task.progress_percentage = Decimal("100.00")
        publish_project_event(
            TaskCompleted(
                event_id=str(uuid.uuid4()),
                event_type="TASK_COMPLETED",
                organization_id=str(task.organization_id),
                project_id=str(task.project_id),
                task_id=str(task.id),
                completion_date=date.today().isoformat(),
            )
        )
    elif prev_status == TaskStatus.DONE and status != TaskStatus.DONE:
        task.completed_at = None
        publish_project_event(
            TaskReopened(
                event_id=str(uuid.uuid4()),
                event_type="TASK_REOPENED",
                organization_id=str(task.organization_id),
                project_id=str(task.project_id),
                task_id=str(task.id),
            )
        )
    elif status == TaskStatus.BLOCKED:
        publish_project_event(
            TaskBlocked(
                event_id=str(uuid.uuid4()),
                event_type="TASK_BLOCKED",
                organization_id=str(task.organization_id),
                project_id=str(task.project_id),
                task_id=str(task.id),
                block_reason=block_reason,
            )
        )

    task.save(update_fields=["status", "completed_at", "progress_percentage", "updated_at"])

    _record_task_activity(
        task=task,
        action="STATUS_CHANGED",
        description=f"Status changed from {prev_status} to {status}.",
        user_id=user_id,
        metadata={"previous_status": prev_status, "new_status": status, "block_reason": block_reason},
    )

    logger.info("Task %s status changed to %s.", task.code, status)
    return task


@transaction.atomic
def assign_task(*, task: Task, employee: Employee, role: str = AssignmentRole.ASSIGNEE, user_id: str = "") -> TaskAssignment:
    """Assign employee to task with role."""
    if role == AssignmentRole.ASSIGNEE:
        task.assignee = employee
        task.save(update_fields=["assignee", "updated_at"])

    assignment, _ = TaskAssignment.objects.update_or_create(
        task=task,
        employee=employee,
        role=role,
    )

    _record_task_activity(
        task=task,
        action="TASK_ASSIGNED",
        description=f"Assigned to {employee.display_name} as {role}.",
        user_id=user_id,
    )

    publish_project_event(
        TaskAssigned(
            event_id=str(uuid.uuid4()),
            event_type="TASK_ASSIGNED",
            organization_id=str(task.organization_id),
            project_id=str(task.project_id),
            task_id=str(task.id),
            assignee_id=str(employee.id),
            role=role,
        )
    )

    return assignment


@transaction.atomic
def add_task_dependency(
    *,
    source_task: Task,
    target_task: Task,
    dependency_type: str = DependencyType.FINISH_TO_START,
    user_id: str = "",
) -> TaskDependency:
    """Link source task as predecessor to target task with circular dependency validation."""
    if _detect_circular_dependency(source_task, target_task):
        raise ProjectValidationError(f"Circular dependency detected between {source_task.code} and {target_task.code}.")

    dependency, _ = TaskDependency.objects.update_or_create(
        source_task=source_task,
        target_task=target_task,
        defaults={"dependency_type": dependency_type},
    )

    _record_task_activity(
        task=target_task,
        action="DEPENDENCY_ADDED",
        description=f"Predecessor dependency added: {source_task.code} ({dependency_type}).",
        user_id=user_id,
    )

    return dependency


@transaction.atomic
def add_checklist_item(*, task: Task, title: str) -> TaskChecklist:
    """Add a checklist item to a task."""
    return TaskChecklist.objects.create(task=task, title=title)


@transaction.atomic
def toggle_checklist_item(*, item: TaskChecklist, is_completed: bool, user_id: str = "") -> TaskChecklist:
    """Toggle checklist item status and recalculate task progress percentage."""
    item.is_completed = is_completed
    item.completed_at = timezone.now() if is_completed else None
    item.save(update_fields=["is_completed", "completed_at", "updated_at"])

    # Auto recalculate task progress percentage
    total = item.task.checklists.count()
    completed = item.task.checklists.filter(is_completed=True).count()
    if total > 0:
        progress = (Decimal(str(completed)) / Decimal(str(total))) * Decimal("100.00")
        item.task.progress_percentage = progress.quantize(Decimal("0.01"))
        item.task.save(update_fields=["progress_percentage", "updated_at"])

        if completed == total:
            publish_project_event(
                TaskChecklistCompleted(
                    event_id=str(uuid.uuid4()),
                    event_type="TASK_CHECKLIST_COMPLETED",
                    organization_id=str(item.task.organization_id),
                    project_id=str(item.task.project_id),
                    task_id=str(item.task.id),
                )
            )

    _record_task_activity(
        task=item.task,
        action="CHECKLIST_TOGGLED",
        description=f"Checklist item '{item.title}' marked {'complete' if is_completed else 'incomplete'}.",
        user_id=user_id,
    )

    return item


@transaction.atomic
def add_task_comment(
    *,
    task: Task,
    author_user_id: str,
    author_name: str,
    content: str,
    parent_comment: Optional[TaskComment] = None,
    is_internal_note: bool = False,
) -> TaskComment:
    """Add a threaded comment to a task."""
    comment = TaskComment.objects.create(
        task=task,
        parent_comment=parent_comment,
        author_user_id=author_user_id,
        author_name=author_name,
        content=content,
        is_internal_note=is_internal_note,
    )

    _record_task_activity(
        task=task,
        action="COMMENT_ADDED",
        description=f"Comment posted by {author_name}.",
        user_id=author_user_id,
    )

    publish_project_event(
        TaskCommentAdded(
            event_id=str(uuid.uuid4()),
            event_type="TASK_COMMENT_ADDED",
            organization_id=str(task.organization_id),
            project_id=str(task.project_id),
            task_id=str(task.id),
            comment_id=str(comment.id),
        )
    )

    return comment


# ── Enterprise Agile Delivery, Sprint & Kanban Services ────────────────────

from .enums import BoardType, EstimationScale, SprintStatus, SprintType
from .events import (
    BoardUpdated,
    SprintCompleted,
    SprintCreated,
    SprintStarted,
    TaskMoved,
    VelocityCalculated,
)
from .models import BoardColumn, KanbanBoard, Release, Sprint, ProjectTeam


@transaction.atomic
def create_sprint(
    *,
    project: Project,
    owner: Employee,
    name: str,
    start_date: date,
    end_date: date,
    goal: str = "",
    sprint_type: str = SprintType.REGULAR,
    team: Optional[ProjectTeam] = None,
    capacity_hours: Decimal = Decimal("0.00"),
    user_id: str = "",
) -> Sprint:
    """Create a new Sprint / Iteration container."""
    if start_date >= end_date:
        raise ProjectValidationError("Sprint start date must be strictly before end date.")

    # Calculate sequential sprint number
    current_max = Sprint.objects.filter(project=project).aggregate(models.Max("sprint_number"))["sprint_number__max"] or 0
    sprint_number = current_max + 1

    sprint = Sprint.objects.create(
        organization=project.organization,
        project=project,
        team=team,
        owner=owner,
        sprint_number=sprint_number,
        name=name,
        goal=goal,
        sprint_type=sprint_type,
        status=SprintStatus.DRAFT,
        start_date=start_date,
        end_date=end_date,
        capacity_hours=capacity_hours,
    )

    _record_audit_log(
        project=project,
        action="SPRINT_CREATED",
        description=f"Sprint {name} [#{sprint_number}] created.",
        user_id=user_id,
    )

    publish_project_event(
        SprintCreated(
            event_id=str(uuid.uuid4()),
            event_type="SPRINT_CREATED",
            organization_id=str(project.organization_id),
            project_id=str(project.id),
            sprint_id=str(sprint.id),
            sprint_number=sprint_number,
            name=name,
        )
    )

    logger.info("Sprint created: %s [#%d] in Project %s.", name, sprint_number, project.code)
    return sprint


@transaction.atomic
def start_sprint(*, sprint: Sprint, user_id: str = "") -> Sprint:
    """Start a sprint and set status to ACTIVE."""
    if sprint.status != SprintStatus.DRAFT and sprint.status != SprintStatus.PLANNING:
        raise ProjectLifecycleError(f"Cannot start sprint in status {sprint.status}.")

    # Enforce only one active sprint per project if desired, or log active status
    active_exists = Sprint.objects.filter(project=sprint.project, status=SprintStatus.ACTIVE).exclude(id=sprint.id).exists()
    if active_exists:
        raise ProjectLifecycleError(f"Another sprint is already ACTIVE in project {sprint.project.code}.")

    sprint.status = SprintStatus.ACTIVE
    sprint.total_story_points = sum(t.story_points for t in sprint.tasks.all())
    sprint.save(update_fields=["status", "total_story_points", "updated_at"])

    _record_audit_log(
        project=sprint.project,
        action="SPRINT_STARTED",
        description=f"Sprint {sprint.name} started.",
        user_id=user_id,
    )

    publish_project_event(
        SprintStarted(
            event_id=str(uuid.uuid4()),
            event_type="SPRINT_STARTED",
            organization_id=str(sprint.organization_id),
            project_id=str(sprint.project_id),
            sprint_id=str(sprint.id),
            start_date=sprint.start_date.isoformat(),
            end_date=sprint.end_date.isoformat(),
        )
    )

    logger.info("Sprint %s started.", sprint.name)
    return sprint


@transaction.atomic
def complete_sprint(*, sprint: Sprint, user_id: str = "") -> Sprint:
    """Complete a sprint, calculate final velocity and completed story points."""
    if sprint.status != SprintStatus.ACTIVE:
        raise ProjectLifecycleError(f"Cannot complete sprint in status {sprint.status}.")

    sprint.status = SprintStatus.COMPLETED
    sprint.completed_at = timezone.now()

    tasks = sprint.tasks.all()
    completed_pts = sum(t.story_points for t in tasks if t.status == TaskStatus.DONE)
    sprint.completed_story_points = completed_pts
    sprint.velocity = completed_pts

    sprint.save(update_fields=["status", "completed_at", "completed_story_points", "velocity", "updated_at"])

    _record_audit_log(
        project=sprint.project,
        action="SPRINT_COMPLETED",
        description=f"Sprint {sprint.name} completed with velocity {completed_pts}.",
        user_id=user_id,
    )

    publish_project_event(
        SprintCompleted(
            event_id=str(uuid.uuid4()),
            event_type="SPRINT_COMPLETED",
            organization_id=str(sprint.organization_id),
            project_id=str(sprint.project_id),
            sprint_id=str(sprint.id),
            completed_points=str(completed_pts),
            velocity=str(completed_pts),
        )
    )

    logger.info("Sprint %s completed. Velocity: %s.", sprint.name, completed_pts)
    return sprint


@transaction.atomic
def add_tasks_to_sprint(*, sprint: Sprint, task_ids: List[str | uuid.UUID]) -> None:
    """Assign multiple tasks to a sprint."""
    if sprint.status == SprintStatus.COMPLETED:
        raise ProjectValidationError("Cannot add tasks to a completed sprint.")

    Task.objects.filter(id__in=task_ids, project=sprint.project).update(sprint=sprint, updated_at=timezone.now())


@transaction.atomic
def create_kanban_board(
    *,
    project: Project,
    name: str,
    board_type: str = BoardType.KANBAN,
    description: str = "",
    estimation_scale: str = EstimationScale.FIBONACCI,
) -> KanbanBoard:
    """Create a Kanban/Scrum board and default columns (To Do, In Progress, Review, Done)."""
    board = KanbanBoard.objects.create(
        organization=project.organization,
        project=project,
        name=name,
        board_type=board_type,
        description=description,
        estimation_scale=estimation_scale,
    )

    # Initialize default columns
    default_cols = [
        ("To Do", 1, TaskStatus.TODO, 0),
        ("In Progress", 2, TaskStatus.IN_PROGRESS, 5),
        ("Under Review", 3, TaskStatus.IN_REVIEW, 3),
        ("Done", 4, TaskStatus.DONE, 0),
    ]

    for c_name, order, mapped_status, wip in default_cols:
        BoardColumn.objects.create(
            board=board,
            name=c_name,
            order=order,
            mapped_status=mapped_status,
            wip_limit=wip,
        )

    return board


@transaction.atomic
def move_task_on_board(
    *,
    task: Task,
    target_column: BoardColumn,
    user_id: str = "",
) -> Task:
    """Move card to a new Kanban column with WIP limit validation."""
    if target_column.board.project_id != task.project_id:
        raise ProjectValidationError("Target column belongs to a different project board.")

    # Validate WIP Limit
    if target_column.wip_limit > 0:
        current_cards = target_column.tasks.filter(is_archived=False).exclude(id=task.id).count()
        if current_cards >= target_column.wip_limit:
            raise ProjectValidationError(
                f"Cannot move task. Column '{target_column.name}' has reached its WIP limit of {target_column.wip_limit}."
            )

    prev_column = task.board_column
    task.board_column = target_column
    task.status = target_column.mapped_status

    if target_column.mapped_status == TaskStatus.DONE:
        task.completed_at = timezone.now()
        task.progress_percentage = Decimal("100.00")
    elif prev_column and prev_column.mapped_status == TaskStatus.DONE and target_column.mapped_status != TaskStatus.DONE:
        task.completed_at = None

    task.save(update_fields=["board_column", "status", "completed_at", "progress_percentage", "updated_at"])

    _record_task_activity(
        task=task,
        action="TASK_MOVED_ON_BOARD",
        description=f"Moved to column '{target_column.name}' ({target_column.mapped_status}).",
        user_id=user_id,
    )

    publish_project_event(
        TaskMoved(
            event_id=str(uuid.uuid4()),
            event_type="TASK_MOVED",
            organization_id=str(task.organization_id),
            project_id=str(task.project_id),
            task_id=str(task.id),
            from_column_id=str(prev_column.id) if prev_column else "",
            to_column_id=str(target_column.id),
        )
    )

    return task


@transaction.atomic
def create_release(
    *,
    project: Project,
    name: str,
    version: str,
    description: str = "",
    target_date: Optional[date] = None,
) -> Release:
    """Create a version release milestone."""
    return Release.objects.create(
        organization=project.organization,
        project=project,
        name=name,
        version=version,
        description=description,
        target_date=target_date,
    )


# ── Enterprise Time Tracking, Timesheet & Worklog Services ───────────────

from .enums import BillableType, OvertimeCategory, TimeEntryType, TimesheetPeriod, TimesheetStatus
from .events import (
    TimeEntryValidated,
    TimeStarted,
    TimeStopped,
    TimesheetApproved,
    TimesheetRejected,
    TimesheetSubmitted,
    WorklogCreated,
    WorklogUpdated,
)
from .models import OvertimeRecord, TimeEntry, Timesheet, TimesheetApprovalLog


def validate_time_entry(*, employee: Employee, date_val: date, hours: Decimal) -> None:
    """Validate time entry bounds: max 24 hours per day and positive hours."""
    if hours <= Decimal("0.00"):
        raise ProjectValidationError("Worklog hours must be strictly positive.")

    # Check total hours logged on date_val for employee
    existing_hours = TimeEntry.objects.filter(employee=employee, date=date_val).aggregate(models.Sum("hours"))["hours__sum"] or Decimal("0.00")
    if (existing_hours + hours) > Decimal("24.00"):
        raise ProjectValidationError(f"Total logged hours for {employee.display_name} on {date_val} would exceed 24 hours limit.")


@transaction.atomic
def start_timer(
    *,
    employee: Employee,
    task: Task,
    notes: str = "",
    billable_type: str = BillableType.BILLABLE,
) -> TimeEntry:
    """Start live timer for an employee. Enforces single active timer rule."""
    active_timer = TimeEntry.objects.filter(employee=employee, is_timer_running=True).first()
    if active_timer:
        raise ProjectValidationError(f"Employee already has a running timer for task [{active_timer.task.code}]. Stop running timer before starting a new one.")

    now = timezone.now()
    entry = TimeEntry.objects.create(
        organization=task.organization,
        project=task.project,
        task=task,
        sprint=task.sprint,
        employee=employee,
        entry_type=TimeEntryType.TIMER,
        billable_type=billable_type,
        date=now.date(),
        hours=Decimal("0.00"),
        start_time=now,
        is_timer_running=True,
        timer_started_at=now,
        notes=notes,
    )

    publish_project_event(
        TimeStarted(
            event_id=str(uuid.uuid4()),
            event_type="TIME_STARTED",
            organization_id=str(task.organization_id),
            project_id=str(task.project_id),
            time_entry_id=str(entry.id),
            employee_id=str(employee.id),
            task_id=str(task.id),
        )
    )

    logger.info("Timer started for %s on Task %s.", employee.employee_id, task.code)
    return entry


@transaction.atomic
def stop_timer(*, entry: TimeEntry) -> TimeEntry:
    """Stop active timer and calculate elapsed effort hours."""
    if not entry.is_timer_running or not entry.timer_started_at:
        raise ProjectValidationError("Timer is not actively running for this entry.")

    now = timezone.now()
    duration_seconds = (now - entry.timer_started_at).total_seconds()
    elapsed_hours = (Decimal(str(duration_seconds)) / Decimal("3600.0")).quantize(Decimal("0.01"))
    if elapsed_hours <= Decimal("0.00"):
        elapsed_hours = Decimal("0.01")

    entry.end_time = now
    entry.hours = elapsed_hours
    entry.is_timer_running = False

    validate_time_entry(employee=entry.employee, date_val=entry.date, hours=elapsed_hours)

    entry.save(update_fields=["end_time", "hours", "is_timer_running", "updated_at"])

    # Update actual hours on Task
    task = entry.task
    task.actual_hours += elapsed_hours
    task.save(update_fields=["actual_hours", "updated_at"])

    publish_project_event(
        TimeStopped(
            event_id=str(uuid.uuid4()),
            event_type="TIME_STOPPED",
            organization_id=str(entry.organization_id),
            project_id=str(entry.project_id),
            time_entry_id=str(entry.id),
            employee_id=str(entry.employee_id),
            hours=str(elapsed_hours),
        )
    )

    logger.info("Timer stopped for %s on Task %s: %sh.", entry.employee.employee_id, task.code, elapsed_hours)
    return entry


@transaction.atomic
def create_manual_worklog(
    *,
    employee: Employee,
    task: Task,
    date_val: date,
    hours: Decimal,
    notes: str = "",
    billable_type: str = BillableType.BILLABLE,
) -> TimeEntry:
    """Create a manual worklog entry."""
    validate_time_entry(employee=employee, date_val=date_val, hours=hours)

    entry = TimeEntry.objects.create(
        organization=task.organization,
        project=task.project,
        task=task,
        sprint=task.sprint,
        employee=employee,
        entry_type=TimeEntryType.MANUAL,
        billable_type=billable_type,
        date=date_val,
        hours=hours,
        notes=notes,
    )

    # Update actual hours on Task
    task.actual_hours += hours
    task.save(update_fields=["actual_hours", "updated_at"])

    publish_project_event(
        WorklogCreated(
            event_id=str(uuid.uuid4()),
            event_type="WORKLOG_CREATED",
            organization_id=str(task.organization_id),
            project_id=str(task.project_id),
            time_entry_id=str(entry.id),
            employee_id=str(employee.id),
            hours=str(hours),
        )
    )

    logger.info("Worklog created: %s - %sh on Task %s.", employee.employee_id, hours, task.code)
    return entry


@transaction.atomic
def submit_timesheet(
    *,
    employee: Employee,
    period_type: str,
    start_date: date,
    end_date: date,
    project: Optional[Project] = None,
    user_id: str = "",
) -> Timesheet:
    """Submit timesheet for manager approval."""
    if start_date >= end_date:
        raise ProjectValidationError("Timesheet start date must be strictly before end date.")

    # Aggregate time entries in range
    entries = TimeEntry.objects.filter(employee=employee, date__gte=start_date, date__lte=end_date)
    if project:
        entries = entries.filter(project=project)

    total_hrs = sum(e.hours for e in entries)
    billable_hrs = sum(e.hours for e in entries if e.billable_type == BillableType.BILLABLE)
    non_billable_hrs = total_hrs - billable_hrs

    # Simple overtime calculation (> 40h per week)
    overtime_hrs = max(Decimal("0.00"), total_hrs - Decimal("40.00"))

    timesheet, _ = Timesheet.objects.update_or_create(
        employee=employee,
        period_type=period_type,
        start_date=start_date,
        defaults={
            "organization": employee.organization,
            "project": project,
            "end_date": end_date,
            "total_hours": total_hrs,
            "billable_hours": billable_hrs,
            "non_billable_hours": non_billable_hrs,
            "overtime_hours": overtime_hrs,
            "status": TimesheetStatus.SUBMITTED,
            "submitted_at": timezone.now(),
        },
    )

    TimesheetApprovalLog.objects.create(
        timesheet=timesheet,
        actor_user_id=user_id,
        action="SUBMITTED",
        comments="Timesheet submitted for approval.",
    )

    publish_project_event(
        TimesheetSubmitted(
            event_id=str(uuid.uuid4()),
            event_type="TIMESHEET_SUBMITTED",
            organization_id=str(employee.organization_id),
            project_id=str(project.id) if project else "",
            timesheet_id=str(timesheet.id),
            employee_id=str(employee.id),
            total_hours=str(total_hrs),
        )
    )

    logger.info("Timesheet submitted for %s [%s to %s].", employee.employee_id, start_date, end_date)
    return timesheet


@transaction.atomic
def approve_timesheet(*, timesheet: Timesheet, approver: Employee, user_id: str = "") -> Timesheet:
    """Approve timesheet and lock associated worklog entries."""
    if timesheet.status != TimesheetStatus.SUBMITTED:
        raise ProjectValidationError(f"Cannot approve timesheet in status {timesheet.status}.")

    timesheet.status = TimesheetStatus.APPROVED
    timesheet.approved_at = timezone.now()
    timesheet.approver = approver
    timesheet.save(update_fields=["status", "approved_at", "approver", "updated_at"])

    # Mark time entries approved and locked
    TimeEntry.objects.filter(
        employee=timesheet.employee, date__gte=timesheet.start_date, date__lte=timesheet.end_date
    ).update(is_approved=True, is_locked=True, updated_at=timezone.now())

    TimesheetApprovalLog.objects.create(
        timesheet=timesheet,
        actor_user_id=user_id,
        action="APPROVED",
        comments=f"Timesheet approved by {approver.display_name}.",
    )

    publish_project_event(
        TimesheetApproved(
            event_id=str(uuid.uuid4()),
            event_type="TIMESHEET_APPROVED",
            organization_id=str(timesheet.organization_id),
            project_id=str(timesheet.project_id) if timesheet.project_id else "",
            timesheet_id=str(timesheet.id),
            approver_id=str(approver.id),
        )
    )

    logger.info("Timesheet approved for %s by %s.", timesheet.employee.employee_id, approver.employee_id)
    return timesheet


@transaction.atomic
def reject_timesheet(*, timesheet: Timesheet, approver: Employee, reason: str, user_id: str = "") -> Timesheet:
    """Reject timesheet with comments."""
    if timesheet.status != TimesheetStatus.SUBMITTED:
        raise ProjectValidationError(f"Cannot reject timesheet in status {timesheet.status}.")

    timesheet.status = TimesheetStatus.REJECTED
    timesheet.rejection_reason = reason
    timesheet.approver = approver
    timesheet.save(update_fields=["status", "rejection_reason", "approver", "updated_at"])

    TimesheetApprovalLog.objects.create(
        timesheet=timesheet,
        actor_user_id=user_id,
        action="REJECTED",
        comments=reason,
    )

    publish_project_event(
        TimesheetRejected(
            event_id=str(uuid.uuid4()),
            event_type="TIMESHEET_REJECTED",
            organization_id=str(timesheet.organization_id),
            project_id=str(timesheet.project_id) if timesheet.project_id else "",
            timesheet_id=str(timesheet.id),
            approver_id=str(approver.id),
            rejection_reason=reason,
        )
    )

    logger.info("Timesheet rejected for %s by %s.", timesheet.employee.employee_id, approver.employee_id)
    return timesheet


# ── Enterprise Resource Planning, Capacity & Workload Services ───────────

from .enums import AllocationStatus, AllocationType
from .events import AllocationRemoved, AllocationUpdated, BenchAssigned, ConflictDetected, ResourceAllocated
from .models import ResourceAllocation, ResourceSkillRequirement


@transaction.atomic
def allocate_resource(
    *,
    employee: Employee,
    project: Project,
    start_date: date,
    end_date: date,
    allocation_percentage: Decimal = Decimal("100.00"),
    task: Optional[Task] = None,
    allocation_type: str = AllocationType.PROJECT,
    notes: str = "",
) -> ResourceAllocation:
    """Allocate an employee to a project with overallocation validation."""
    if start_date >= end_date:
        raise ProjectValidationError("Allocation start date must be strictly before end date.")

    if allocation_percentage <= Decimal("0.00") or allocation_percentage > Decimal("100.00"):
        raise ProjectValidationError("Allocation percentage must be between 1.00% and 100.00%.")

    # Check overallocation conflicts across concurrent active allocations
    existing_allocations = ResourceAllocation.objects.filter(
        employee=employee,
        status=AllocationStatus.ACTIVE,
        start_date__lte=end_date,
        end_date__gte=start_date,
    )
    current_total_pct = sum(a.allocation_percentage for a in existing_allocations)

    if (current_total_pct + allocation_percentage) > Decimal("100.00"):
        publish_project_event(
            ConflictDetected(
                event_id=str(uuid.uuid4()),
                event_type="CONFLICT_DETECTED",
                organization_id=str(project.organization_id),
                project_id=str(project.id),
                employee_id=str(employee.id),
                total_allocation_pct=str(current_total_pct + allocation_percentage),
            )
        )
        raise ProjectValidationError(
            f"Overallocation conflict: {employee.display_name} is already allocated {current_total_pct}%. Adding {allocation_percentage}% exceeds 100% maximum capacity."
        )

    daily_hours = (allocation_percentage / Decimal("100.0")) * Decimal("8.00")

    allocation = ResourceAllocation.objects.create(
        organization=project.organization,
        project=project,
        task=task,
        employee=employee,
        allocation_type=allocation_type,
        allocation_percentage=allocation_percentage,
        allocated_hours_per_day=daily_hours,
        start_date=start_date,
        end_date=end_date,
        status=AllocationStatus.ACTIVE,
        notes=notes,
    )

    publish_project_event(
        ResourceAllocated(
            event_id=str(uuid.uuid4()),
            event_type="RESOURCE_ALLOCATED",
            organization_id=str(project.organization_id),
            project_id=str(project.id),
            allocation_id=str(allocation.id),
            employee_id=str(employee.id),
            allocation_percentage=str(allocation_percentage),
        )
    )

    logger.info("Resource allocated: %s to %s (%s%%).", employee.display_name, project.code, allocation_percentage)
    return allocation


@transaction.atomic
def update_resource_allocation(
    *,
    allocation: ResourceAllocation,
    allocation_percentage: Optional[Decimal] = None,
    status: Optional[str] = None,
) -> ResourceAllocation:
    """Update resource allocation parameters."""
    if allocation_percentage is not None:
        if allocation_percentage <= Decimal("0.00") or allocation_percentage > Decimal("100.00"):
            raise ProjectValidationError("Allocation percentage must be between 1.00% and 100.00%.")

        allocation.allocation_percentage = allocation_percentage
        allocation.allocated_hours_per_day = (allocation_percentage / Decimal("100.0")) * Decimal("8.00")

    if status is not None:
        allocation.status = status

    allocation.save()

    publish_project_event(
        AllocationUpdated(
            event_id=str(uuid.uuid4()),
            event_type="ALLOCATION_UPDATED",
            organization_id=str(allocation.organization_id),
            project_id=str(allocation.project_id),
            allocation_id=str(allocation.id),
        )
    )

    return allocation


@transaction.atomic
def remove_resource_allocation(*, allocation: ResourceAllocation) -> None:
    """Soft-cancel or remove resource allocation."""
    allocation.status = AllocationStatus.CANCELLED
    allocation.save(update_fields=["status", "updated_at"])

    publish_project_event(
        AllocationRemoved(
            event_id=str(uuid.uuid4()),
            event_type="ALLOCATION_REMOVED",
            organization_id=str(allocation.organization_id),
            project_id=str(allocation.project_id),
            allocation_id=str(allocation.id),
        )
    )


@transaction.atomic
def assign_to_bench(*, employee: Employee, notes: str = "") -> None:
    """Move employee to bench status and clear active project allocations."""
    ResourceAllocation.objects.filter(employee=employee, status=AllocationStatus.ACTIVE).update(
        status=AllocationStatus.COMPLETED, updated_at=timezone.now()
    )

    publish_project_event(
        BenchAssigned(
            event_id=str(uuid.uuid4()),
            event_type="BENCH_ASSIGNED",
            organization_id=str(employee.organization_id),
            project_id="",
            employee_id=str(employee.id),
        )
    )

    logger.info("Employee %s moved to bench.", employee.employee_id)


# ── Enterprise Portfolio Management, Program & PMO Services ───────────────

from .enums import PortfolioStatus, PortfolioType, ProgramStatus, RiskLevel, RiskStatus
from .events import MilestoneCompleted, PortfolioCreated, PortfolioUpdated, ProgramCreated, RiskEscalated
from .models import Portfolio, PortfolioMilestone, PortfolioProjectMapping, PortfolioRisk, Program


@transaction.atomic
def create_portfolio(
    *,
    organization: Organization,
    owner: Employee,
    code: str,
    name: str,
    portfolio_type: str = PortfolioType.STRATEGIC,
    executive_sponsor: Optional[Employee] = None,
    description: str = "",
    budget: Decimal = Decimal("0.00"),
    priority: int = 1,
) -> Portfolio:
    """Create a strategic portfolio container."""
    if Portfolio.objects.filter(code=code).exists():
        raise ProjectValidationError(f"Portfolio code [{code}] already exists.")

    portfolio = Portfolio.objects.create(
        organization=organization,
        owner=owner,
        executive_sponsor=executive_sponsor,
        code=code,
        name=name,
        portfolio_type=portfolio_type,
        description=description,
        budget=budget,
        priority=priority,
        status=PortfolioStatus.ACTIVE,
    )

    publish_project_event(
        PortfolioCreated(
            event_id=str(uuid.uuid4()),
            event_type="PORTFOLIO_CREATED",
            organization_id=str(organization.id),
            portfolio_id=str(portfolio.id),
            code=code,
            name=name,
        )
    )

    logger.info("Portfolio created: %s [%s].", name, code)
    return portfolio


@transaction.atomic
def create_program(
    *,
    organization: Organization,
    program_manager: Employee,
    code: str,
    name: str,
    portfolio: Optional[Portfolio] = None,
    description: str = "",
    budget: Decimal = Decimal("0.00"),
    target_start_date: Optional[date] = None,
    target_end_date: Optional[date] = None,
) -> Program:
    """Create a cross-functional program container."""
    if Program.objects.filter(code=code).exists():
        raise ProjectValidationError(f"Program code [{code}] already exists.")

    program = Program.objects.create(
        organization=organization,
        program_manager=program_manager,
        portfolio=portfolio,
        code=code,
        name=name,
        description=description,
        budget=budget,
        target_start_date=target_start_date,
        target_end_date=target_end_date,
        status=ProgramStatus.ACTIVE,
    )

    publish_project_event(
        ProgramCreated(
            event_id=str(uuid.uuid4()),
            event_type="PROGRAM_CREATED",
            organization_id=str(organization.id),
            program_id=str(program.id),
            code=code,
            name=name,
        )
    )

    logger.info("Program created: %s [%s].", name, code)
    return program


@transaction.atomic
def map_projects_to_portfolio(*, portfolio: Portfolio, project_ids: List[str | uuid.UUID]) -> None:
    """Map projects into a portfolio container."""
    for pid in project_ids:
        project = Project.objects.filter(id=pid).first()
        if project:
            PortfolioProjectMapping.objects.get_or_create(portfolio=portfolio, project=project)


@transaction.atomic
def create_portfolio_risk(
    *,
    organization: Organization,
    title: str,
    probability: int = 3,
    impact: int = 3,
    portfolio: Optional[Portfolio] = None,
    program: Optional[Program] = None,
    project: Optional[Project] = None,
    risk_owner: Optional[Employee] = None,
    description: str = "",
    mitigation_plan: str = "",
) -> PortfolioRisk:
    """Log a portfolio or program risk with calculated risk score."""
    risk_score = probability * impact

    if risk_score >= 16:
        risk_level = RiskLevel.CRITICAL
    elif risk_score >= 10:
        risk_level = RiskLevel.HIGH
    elif risk_score >= 5:
        risk_level = RiskLevel.MEDIUM
    else:
        risk_level = RiskLevel.LOW

    risk = PortfolioRisk.objects.create(
        organization=organization,
        portfolio=portfolio,
        program=program,
        project=project,
        risk_owner=risk_owner,
        title=title,
        description=description,
        probability=probability,
        impact=impact,
        risk_score=risk_score,
        risk_level=risk_level,
        status=RiskStatus.IDENTIFIED,
        mitigation_plan=mitigation_plan,
    )

    if risk_level in [RiskLevel.HIGH, RiskLevel.CRITICAL]:
        publish_project_event(
            RiskEscalated(
                event_id=str(uuid.uuid4()),
                event_type="RISK_ESCALATED",
                organization_id=str(organization.id),
                risk_id=str(risk.id),
                risk_score=risk_score,
            )
        )

    logger.info("Portfolio risk created: %s (Score %d).", title, risk_score)
    return risk


@transaction.atomic
def create_portfolio_milestone(
    *,
    organization: Organization,
    title: str,
    target_date: date,
    portfolio: Optional[Portfolio] = None,
    program: Optional[Program] = None,
    description: str = "",
) -> PortfolioMilestone:
    """Create a program or portfolio strategic milestone."""
    return PortfolioMilestone.objects.create(
        organization=organization,
        portfolio=portfolio,
        program=program,
        title=title,
        description=description,
        target_date=target_date,
    )


@transaction.atomic
def complete_milestone(*, milestone: PortfolioMilestone) -> PortfolioMilestone:
    """Mark strategic milestone achieved."""
    milestone.is_completed = True
    milestone.achieved_date = date.today()
    milestone.save(update_fields=["is_completed", "achieved_date", "updated_at"])

    publish_project_event(
        MilestoneCompleted(
            event_id=str(uuid.uuid4()),
            event_type="MILESTONE_COMPLETED",
            organization_id=str(milestone.organization_id),
            milestone_id=str(milestone.id),
        )
    )

    logger.info("Milestone completed: %s.", milestone.title)
    return milestone





