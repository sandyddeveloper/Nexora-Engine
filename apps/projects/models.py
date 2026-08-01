"""Domain models for Enterprise Project Management Foundation Engine extending BaseModel."""

from decimal import Decimal
from django.db import models
from django.utils.translation import gettext_lazy as _

from apps.common.models import BaseModel
from apps.employees.models import Employee
from apps.organizations.models import Branch, Department, Organization

from .enums import (
    AllocationStatus,
    AllocationType,
    AssignmentRole,
    BillableType,
    BoardType,
    DependencyType,
    EstimationScale,
    HealthStatus,
    OvertimeCategory,
    PortfolioStatus,
    PortfolioType,
    ProgramStatus,
    ProjectCategory,
    ProjectMemberRole,
    ProjectPriority,
    ProjectRiskLevel,
    ProjectStatus,
    ProjectType,
    ProjectVisibility,
    ResourceAvailabilityState,
    RiskLevel,
    RiskStatus,
    SprintStatus,
    SprintType,
    TaskSeverity,
    TaskStatus,
    TaskType,
    TimeEntryType,
    TimesheetPeriod,
    TimesheetStatus,
    WorkloadStatus,
)


class Project(BaseModel):
    """Core enterprise project domain model."""

    organization = models.ForeignKey(
        Organization,
        on_delete=models.PROTECT,
        related_name="projects",
        help_text=_("Owning organization."),
    )
    branch = models.ForeignKey(
        Branch,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="projects",
        help_text=_("Associated branch location if applicable."),
    )
    department = models.ForeignKey(
        Department,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="projects",
        help_text=_("Associated department if applicable."),
    )
    owner = models.ForeignKey(
        Employee,
        on_delete=models.PROTECT,
        related_name="owned_projects",
        help_text=_("Executive project owner."),
    )
    manager = models.ForeignKey(
        Employee,
        on_delete=models.PROTECT,
        related_name="managed_projects",
        help_text=_("Designated project manager."),
    )
    program = models.ForeignKey(
        "Program",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="projects",
        help_text=_("Parent program if part of a program initiative."),
    )

    code = models.CharField(
        max_length=50,
        help_text=_("Unique project code within organization (e.g. PRJ-2026-001)."),
    )
    name = models.CharField(
        max_length=200,
        help_text=_("Human-readable project name."),
    )
    description = models.TextField(
        blank=True,
        help_text=_("Detailed project scope description."),
    )
    project_type = models.CharField(
        max_length=50,
        choices=ProjectType.choices,
        default=ProjectType.INTERNAL,
        help_text=_("Classification of project type."),
    )
    category = models.CharField(
        max_length=50,
        choices=ProjectCategory.choices,
        default=ProjectCategory.SOFTWARE,
        help_text=_("Business category."),
    )
    status = models.CharField(
        max_length=50,
        choices=ProjectStatus.choices,
        default=ProjectStatus.DRAFT,
        help_text=_("Lifecycle status."),
    )
    priority = models.CharField(
        max_length=50,
        choices=ProjectPriority.choices,
        default=ProjectPriority.MEDIUM,
        help_text=_("Execution priority."),
    )
    risk_level = models.CharField(
        max_length=50,
        choices=ProjectRiskLevel.choices,
        default=ProjectRiskLevel.LOW,
        help_text=_("Assessed risk level."),
    )
    visibility = models.CharField(
        max_length=50,
        choices=ProjectVisibility.choices,
        default=ProjectVisibility.ORGANIZATION,
        help_text=_("Visibility scope."),
    )

    start_date = models.DateField(
        null=True,
        blank=True,
        help_text=_("Planned start date."),
    )
    end_date = models.DateField(
        null=True,
        blank=True,
        help_text=_("Planned target completion date."),
    )

    estimated_budget = models.DecimalField(
        max_digits=16,
        decimal_places=2,
        default=Decimal("0.00"),
        help_text=_("Estimated total budget."),
    )
    estimated_hours = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=Decimal("0.00"),
        help_text=_("Estimated total effort hours."),
    )

    is_active = models.BooleanField(
        default=True,
        help_text=_("Whether project is active."),
    )
    is_archived = models.BooleanField(
        default=False,
        help_text=_("Whether project is archived."),
    )

    settings_json = models.JSONField(
        default=dict,
        blank=True,
        help_text=_("Project configuration settings (calendar, working days, timezone, task prefix)."),
    )

    class Meta:
        verbose_name = _("Project")
        verbose_name_plural = _("Projects")
        unique_together = ("organization", "code")
        indexes = [
            models.Index(fields=["organization", "status"], name="idx_project_org_status"),
            models.Index(fields=["organization", "project_type"], name="idx_project_org_type"),
        ]

    def __str__(self) -> str:
        return f"[{self.code}] {self.name} ({self.status})"


class ProjectTeam(BaseModel):
    """Team container associated with a project."""

    project = models.ForeignKey(
        Project,
        on_delete=models.CASCADE,
        related_name="teams",
        help_text=_("Associated project."),
    )
    name = models.CharField(
        max_length=150,
        help_text=_("Team name (e.g. Frontend Team, Core Backend)."),
    )
    description = models.TextField(
        blank=True,
        help_text=_("Team description and responsibilities."),
    )

    class Meta:
        verbose_name = _("Project Team")
        verbose_name_plural = _("Project Teams")

    def __str__(self) -> str:
        return f"{self.name} ({self.project.code})"


class ProjectMember(BaseModel):
    """Assignment of an employee to a project with role and effort allocation."""

    project = models.ForeignKey(
        Project,
        on_delete=models.CASCADE,
        related_name="members",
        help_text=_("Assigned project."),
    )
    employee = models.ForeignKey(
        Employee,
        on_delete=models.PROTECT,
        related_name="project_assignments",
        help_text=_("Assigned employee."),
    )
    role = models.CharField(
        max_length=50,
        choices=ProjectMemberRole.choices,
        default=ProjectMemberRole.DEVELOPER,
        help_text=_("Project member role."),
    )
    allocated_hours_per_week = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=Decimal("40.00"),
        help_text=_("Weekly allocated capacity hours."),
    )

    joined_at = models.DateField(
        auto_now_add=True,
        help_text=_("Date member joined project."),
    )
    left_at = models.DateField(
        null=True,
        blank=True,
        help_text=_("Date member left project if unassigned."),
    )
    is_active = models.BooleanField(
        default=True,
        help_text=_("Whether member assignment is active."),
    )

    class Meta:
        verbose_name = _("Project Member")
        verbose_name_plural = _("Project Members")
        unique_together = ("project", "employee")
        indexes = [
            models.Index(fields=["project", "is_active"], name="idx_projmem_proj_active"),
        ]

    def __str__(self) -> str:
        return f"{self.employee.display_name} as {self.role} in {self.project.code}"


class ProjectAuditLog(BaseModel):
    """Immutable audit trail for all project state transitions and updates."""

    project = models.ForeignKey(
        Project,
        on_delete=models.CASCADE,
        related_name="audit_logs",
        help_text=_("Target project."),
    )
    actor_user_id = models.CharField(
        max_length=100,
        blank=True,
        help_text=_("User ID who performed action."),
    )
    action = models.CharField(
        max_length=100,
        help_text=_("Action key (e.g. PROJECT_CREATED, PROJECT_ACTIVATED)."),
    )
    description = models.TextField(
        help_text=_("Human-readable log description."),
    )
    changes_json = models.JSONField(
        default=dict,
        blank=True,
        help_text=_("Delta payload of modified fields."),
    )

    class Meta:
        verbose_name = _("Project Audit Log")
        verbose_name_plural = _("Project Audit Logs")
        ordering = ["-created_at"]

    def __str__(self) -> str:
        return f"[{self.action}] {self.project.code} at {self.created_at}"


# ── Enterprise Task, WBS & Work Management Engine Models ───────────────────


class Task(BaseModel):
    """Core enterprise task & WBS work unit model supporting recursive parent-child hierarchy."""

    organization = models.ForeignKey(
        Organization,
        on_delete=models.PROTECT,
        related_name="tasks",
        help_text=_("Owning organization."),
    )
    project = models.ForeignKey(
        Project,
        on_delete=models.CASCADE,
        related_name="tasks",
        help_text=_("Associated project."),
    )
    parent = models.ForeignKey(
        "self",
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="subtasks",
        help_text=_("Parent task for WBS hierarchical decomposition."),
    )
    epic = models.ForeignKey(
        "self",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="epic_tasks",
        help_text=_("Associated parent epic if applicable."),
    )
    sprint = models.ForeignKey(
        "Sprint",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="tasks",
        help_text=_("Assigned Sprint container."),
    )
    board_column = models.ForeignKey(
        "BoardColumn",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="tasks",
        help_text=_("Current Kanban board column."),
    )
    backlog_rank = models.PositiveIntegerField(
        default=0,
        help_text=_("Product backlog sequence ranking order."),
    )

    reporter = models.ForeignKey(
        Employee,
        on_delete=models.PROTECT,
        related_name="reported_tasks",
        help_text=_("Employee who reported or created task."),
    )
    assignee = models.ForeignKey(
        Employee,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="assigned_tasks",
        help_text=_("Primary assigned employee."),
    )

    code = models.CharField(
        max_length=50,
        help_text=_("Unique task code within project (e.g. PRJ-NEX-12)."),
    )
    wbs_code = models.CharField(
        max_length=50,
        blank=True,
        help_text=_("Hierarchical WBS numbering code (e.g. 1.2.1)."),
    )
    title = models.CharField(
        max_length=250,
        help_text=_("Task title."),
    )
    description = models.TextField(
        blank=True,
        help_text=_("Detailed task specification."),
    )

    task_type = models.CharField(
        max_length=50,
        choices=TaskType.choices,
        default=TaskType.TASK,
        help_text=_("Classification of task type."),
    )
    status = models.CharField(
        max_length=50,
        choices=TaskStatus.choices,
        default=TaskStatus.TODO,
        help_text=_("Current execution status."),
    )
    priority = models.CharField(
        max_length=50,
        choices=ProjectPriority.choices,
        default=ProjectPriority.MEDIUM,
        help_text=_("Priority level."),
    )
    severity = models.CharField(
        max_length=50,
        choices=TaskSeverity.choices,
        default=TaskSeverity.MINOR,
        help_text=_("Impact severity."),
    )

    story_points = models.DecimalField(
        max_digits=5,
        decimal_places=1,
        default=Decimal("0.0"),
        help_text=_("Agile story points effort estimate."),
    )
    estimated_hours = models.DecimalField(
        max_digits=8,
        decimal_places=2,
        default=Decimal("0.00"),
        help_text=_("Estimated effort hours."),
    )
    actual_hours = models.DecimalField(
        max_digits=8,
        decimal_places=2,
        default=Decimal("0.00"),
        help_text=_("Actual logged effort hours."),
    )
    progress_percentage = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=Decimal("0.00"),
        help_text=_("Calculated progress percentage (0.00 - 100.00)."),
    )

    start_date = models.DateField(
        null=True,
        blank=True,
        help_text=_("Planned start date."),
    )
    due_date = models.DateField(
        null=True,
        blank=True,
        help_text=_("Target due date."),
    )
    completed_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text=_("Timestamp when task reached DONE status."),
    )

    is_archived = models.BooleanField(
        default=False,
        help_text=_("Whether task is archived."),
    )

    class Meta:
        verbose_name = _("Task")
        verbose_name_plural = _("Tasks")
        unique_together = ("project", "code")
        indexes = [
            models.Index(fields=["project", "status"], name="idx_task_proj_status"),
            models.Index(fields=["project", "task_type"], name="idx_task_proj_type"),
            models.Index(fields=["parent", "wbs_code"], name="idx_task_parent_wbs"),
        ]

    def __str__(self) -> str:
        return f"[{self.code}] {self.title} ({self.status})"


class TaskAssignment(BaseModel):
    """Multi-role employee assignment for tasks (Assignee, Reviewer, Approver, Observer)."""

    task = models.ForeignKey(
        Task,
        on_delete=models.CASCADE,
        related_name="assignments",
        help_text=_("Assigned task."),
    )
    employee = models.ForeignKey(
        Employee,
        on_delete=models.PROTECT,
        related_name="task_assignments",
        help_text=_("Assigned employee."),
    )
    role = models.CharField(
        max_length=50,
        choices=AssignmentRole.choices,
        default=AssignmentRole.ASSIGNEE,
        help_text=_("Assignment role."),
    )
    assigned_at = models.DateTimeField(
        auto_now_add=True,
        help_text=_("Timestamp of assignment."),
    )

    class Meta:
        verbose_name = _("Task Assignment")
        verbose_name_plural = _("Task Assignments")
        unique_together = ("task", "employee", "role")

    def __str__(self) -> str:
        return f"{self.employee.display_name} as {self.role} on {self.task.code}"


class TaskDependency(BaseModel):
    """Dependency link between source predecessor task and target successor task."""

    source_task = models.ForeignKey(
        Task,
        on_delete=models.CASCADE,
        related_name="predecessor_dependencies",
        help_text=_("Source predecessor task."),
    )
    target_task = models.ForeignKey(
        Task,
        on_delete=models.CASCADE,
        related_name="successor_dependencies",
        help_text=_("Target successor task."),
    )
    dependency_type = models.CharField(
        max_length=50,
        choices=DependencyType.choices,
        default=DependencyType.FINISH_TO_START,
        help_text=_("Type of dependency linkage."),
    )

    class Meta:
        verbose_name = _("Task Dependency")
        verbose_name_plural = _("Task Dependencies")
        unique_together = ("source_task", "target_task")

    def __str__(self) -> str:
        return f"{self.source_task.code} -> {self.target_task.code} ({self.dependency_type})"


class TaskChecklist(BaseModel):
    """Checklist item on a task with completion tracking."""

    task = models.ForeignKey(
        Task,
        on_delete=models.CASCADE,
        related_name="checklists",
        help_text=_("Target task."),
    )
    title = models.CharField(
        max_length=200,
        help_text=_("Checklist item title."),
    )
    is_completed = models.BooleanField(
        default=False,
        help_text=_("Whether checklist item is marked completed."),
    )
    completed_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text=_("Timestamp when completed."),
    )

    class Meta:
        verbose_name = _("Task Checklist Item")
        verbose_name_plural = _("Task Checklist Items")

    def __str__(self) -> str:
        status_str = "DONE" if self.is_completed else "PENDING"
        return f"[{status_str}] {self.title} on {self.task.code}"


class TaskComment(BaseModel):
    """Threaded comment posted on a task."""

    task = models.ForeignKey(
        Task,
        on_delete=models.CASCADE,
        related_name="comments",
        help_text=_("Target task."),
    )
    parent_comment = models.ForeignKey(
        "self",
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="replies",
        help_text=_("Parent comment for threaded replies."),
    )
    author_user_id = models.CharField(
        max_length=100,
        help_text=_("User ID of comment author."),
    )
    author_name = models.CharField(
        max_length=150,
        help_text=_("Display name of comment author."),
    )
    content = models.TextField(
        help_text=_("Comment text body."),
    )
    is_internal_note = models.BooleanField(
        default=False,
        help_text=_("Whether comment is restricted to internal team."),
    )

    class Meta:
        verbose_name = _("Task Comment")
        verbose_name_plural = _("Task Comments")
        ordering = ["created_at"]

    def __str__(self) -> str:
        return f"Comment by {self.author_name} on {self.task.code}"


class TaskActivityLog(BaseModel):
    """Immutable activity timeline log for task updates and actions."""

    task = models.ForeignKey(
        Task,
        on_delete=models.CASCADE,
        related_name="activities",
        help_text=_("Target task."),
    )
    actor_user_id = models.CharField(
        max_length=100,
        blank=True,
        help_text=_("User ID of actor."),
    )
    action = models.CharField(
        max_length=100,
        help_text=_("Action key (e.g. TASK_CREATED, STATUS_CHANGED, ASSIGNED)."),
    )
    description = models.TextField(
        help_text=_("Human-readable log entry."),
    )
    metadata_json = models.JSONField(
        default=dict,
        blank=True,
        help_text=_("Delta parameters of activity."),
    )

    class Meta:
        verbose_name = _("Task Activity Log")
        verbose_name_plural = _("Task Activity Logs")
        ordering = ["-created_at"]

    def __str__(self) -> str:
        return f"[{self.action}] {self.task.code} at {self.created_at}"


# ── Enterprise Agile Delivery, Sprint & Kanban Engine Models ───────────────


class Sprint(BaseModel):
    """Agile Sprint / Iteration execution container."""

    organization = models.ForeignKey(
        Organization,
        on_delete=models.PROTECT,
        related_name="sprints",
        help_text=_("Owning organization."),
    )
    project = models.ForeignKey(
        Project,
        on_delete=models.CASCADE,
        related_name="sprints",
        help_text=_("Associated project."),
    )
    team = models.ForeignKey(
        ProjectTeam,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="sprints",
        help_text=_("Assigned project team if applicable."),
    )
    owner = models.ForeignKey(
        Employee,
        on_delete=models.PROTECT,
        related_name="owned_sprints",
        help_text=_("Scrum Master / Sprint Owner."),
    )

    sprint_number = models.PositiveIntegerField(
        help_text=_("Sequential sprint number within project."),
    )
    name = models.CharField(
        max_length=150,
        help_text=_("Sprint title (e.g. Sprint 12 - Core Engine)."),
    )
    goal = models.TextField(
        blank=True,
        help_text=_("Sprint business goal statement."),
    )
    sprint_type = models.CharField(
        max_length=50,
        choices=SprintType.choices,
        default=SprintType.REGULAR,
        help_text=_("Sprint classification."),
    )
    status = models.CharField(
        max_length=50,
        choices=SprintStatus.choices,
        default=SprintStatus.DRAFT,
        help_text=_("Current sprint lifecycle status."),
    )

    start_date = models.DateField(
        help_text=_("Planned start date."),
    )
    end_date = models.DateField(
        help_text=_("Planned end date."),
    )
    completed_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text=_("Actual completion timestamp."),
    )

    capacity_hours = models.DecimalField(
        max_digits=8,
        decimal_places=2,
        default=Decimal("0.00"),
        help_text=_("Total team effort capacity in hours."),
    )
    total_story_points = models.DecimalField(
        max_digits=8,
        decimal_places=1,
        default=Decimal("0.0"),
        help_text=_("Total committed story points."),
    )
    completed_story_points = models.DecimalField(
        max_digits=8,
        decimal_places=1,
        default=Decimal("0.0"),
        help_text=_("Actual completed story points at sprint close."),
    )
    velocity = models.DecimalField(
        max_digits=8,
        decimal_places=1,
        default=Decimal("0.0"),
        help_text=_("Calculated velocity for sprint."),
    )

    class Meta:
        verbose_name = _("Sprint")
        verbose_name_plural = _("Sprints")
        unique_together = ("project", "sprint_number")
        ordering = ["-sprint_number"]

    def __str__(self) -> str:
        return f"{self.name} ({self.status})"


class KanbanBoard(BaseModel):
    """Configurable Scrum or Kanban visual work board."""

    organization = models.ForeignKey(
        Organization,
        on_delete=models.PROTECT,
        related_name="boards",
        help_text=_("Owning organization."),
    )
    project = models.ForeignKey(
        Project,
        on_delete=models.CASCADE,
        related_name="boards",
        help_text=_("Associated project."),
    )
    name = models.CharField(
        max_length=150,
        help_text=_("Board title (e.g. Main Engineering Kanban)."),
    )
    board_type = models.CharField(
        max_length=50,
        choices=BoardType.choices,
        default=BoardType.KANBAN,
        help_text=_("Board workflow type."),
    )
    description = models.TextField(
        blank=True,
        help_text=_("Board description."),
    )
    estimation_scale = models.CharField(
        max_length=50,
        choices=EstimationScale.choices,
        default=EstimationScale.FIBONACCI,
        help_text=_("Estimation scale used on board."),
    )

    class Meta:
        verbose_name = _("Kanban Board")
        verbose_name_plural = _("Kanban Boards")

    def __str__(self) -> str:
        return f"{self.name} ({self.project.code})"


class BoardColumn(BaseModel):
    """Configurable column within a Kanban board with WIP limits."""

    board = models.ForeignKey(
        KanbanBoard,
        on_delete=models.CASCADE,
        related_name="columns",
        help_text=_("Parent board."),
    )
    name = models.CharField(
        max_length=100,
        help_text=_("Column header (e.g. In Review)."),
    )
    order = models.PositiveIntegerField(
        default=1,
        help_text=_("Display sequence order."),
    )
    wip_limit = models.PositiveIntegerField(
        default=0,
        help_text=_("Maximum Work-In-Progress card capacity (0 = unlimited)."),
    )
    mapped_status = models.CharField(
        max_length=50,
        choices=TaskStatus.choices,
        default=TaskStatus.TODO,
        help_text=_("Task status mapped to this column."),
    )
    policy_description = models.TextField(
        blank=True,
        help_text=_("Definition of Done / Entry policy for column."),
    )

    class Meta:
        verbose_name = _("Board Column")
        verbose_name_plural = _("Board Columns")
        ordering = ["order"]

    def __str__(self) -> str:
        return f"{self.name} [{self.board.name}]"


class Release(BaseModel):
    """Version milestone and release planning entity."""

    organization = models.ForeignKey(
        Organization,
        on_delete=models.PROTECT,
        related_name="releases",
        help_text=_("Owning organization."),
    )
    project = models.ForeignKey(
        Project,
        on_delete=models.CASCADE,
        related_name="releases",
        help_text=_("Associated project."),
    )
    name = models.CharField(
        max_length=150,
        help_text=_("Release name (e.g. Version 2.5.0 - Enterprise)."),
    )
    version = models.CharField(
        max_length=50,
        help_text=_("SemVer version code (e.g. v2.5.0)."),
    )
    description = models.TextField(
        blank=True,
        help_text=_("Release notes summary."),
    )
    target_date = models.DateField(
        null=True,
        blank=True,
        help_text=_("Planned release date."),
    )
    released_at = models.DateField(
        null=True,
        blank=True,
        help_text=_("Actual release date."),
    )
    is_released = models.BooleanField(
        default=False,
        help_text=_("Whether release is published."),
    )

    class Meta:
        verbose_name = _("Release")
        verbose_name_plural = _("Releases")

    def __str__(self) -> str:
        return f"{self.name} ({self.version})"


# ── Enterprise Time Tracking, Timesheet & Worklog Models ───────────────────


class TimeEntry(BaseModel):
    """Worklog entry model supporting manual worklogs and live start/stop timers."""

    organization = models.ForeignKey(
        Organization,
        on_delete=models.PROTECT,
        related_name="time_entries",
        help_text=_("Owning organization."),
    )
    project = models.ForeignKey(
        Project,
        on_delete=models.CASCADE,
        related_name="time_entries",
        help_text=_("Associated project."),
    )
    task = models.ForeignKey(
        Task,
        on_delete=models.CASCADE,
        related_name="time_entries",
        help_text=_("Associated task."),
    )
    sprint = models.ForeignKey(
        Sprint,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="time_entries",
        help_text=_("Associated sprint if applicable."),
    )
    employee = models.ForeignKey(
        Employee,
        on_delete=models.PROTECT,
        related_name="time_entries",
        help_text=_("Employee logging time."),
    )

    entry_type = models.CharField(
        max_length=50,
        choices=TimeEntryType.choices,
        default=TimeEntryType.MANUAL,
        help_text=_("Type of time entry."),
    )
    billable_type = models.CharField(
        max_length=50,
        choices=BillableType.choices,
        default=BillableType.BILLABLE,
        help_text=_("Billable classification."),
    )

    date = models.DateField(
        help_text=_("Worklog date."),
    )
    hours = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=Decimal("0.00"),
        help_text=_("Logged effort hours (e.g. 2.50)."),
    )
    start_time = models.DateTimeField(
        null=True,
        blank=True,
        help_text=_("Start timestamp if timer entry."),
    )
    end_time = models.DateTimeField(
        null=True,
        blank=True,
        help_text=_("End timestamp if timer entry."),
    )

    is_timer_running = models.BooleanField(
        default=False,
        help_text=_("Whether live timer is actively running for employee."),
    )
    timer_started_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text=_("Timestamp when live timer started."),
    )

    notes = models.TextField(
        blank=True,
        help_text=_("Detailed activity description notes."),
    )

    is_approved = models.BooleanField(
        default=False,
        help_text=_("Whether entry is approved via timesheet."),
    )
    is_locked = models.BooleanField(
        default=False,
        help_text=_("Whether entry is locked for payroll/invoicing."),
    )

    class Meta:
        verbose_name = _("Time Entry")
        verbose_name_plural = _("Time Entries")
        ordering = ["-date", "-created_at"]
        indexes = [
            models.Index(fields=["employee", "date"], name="idx_tentry_emp_date"),
            models.Index(fields=["project", "date"], name="idx_tentry_proj_date"),
            models.Index(fields=["employee", "is_timer_running"], name="idx_tentry_emp_timer"),
        ]

    def __str__(self) -> str:
        return f"{self.employee.display_name} - {self.hours}h on {self.task.code} ({self.date})"


class Timesheet(BaseModel):
    """Timesheet submission container for multi-period approval workflows."""

    organization = models.ForeignKey(
        Organization,
        on_delete=models.PROTECT,
        related_name="timesheets",
        help_text=_("Owning organization."),
    )
    employee = models.ForeignKey(
        Employee,
        on_delete=models.PROTECT,
        related_name="timesheets",
        help_text=_("Submitting employee."),
    )
    project = models.ForeignKey(
        Project,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="timesheets",
        help_text=_("Associated project if project-specific timesheet."),
    )

    period_type = models.CharField(
        max_length=50,
        choices=TimesheetPeriod.choices,
        default=TimesheetPeriod.WEEKLY,
        help_text=_("Timesheet period frequency."),
    )
    start_date = models.DateField(
        help_text=_("Period start date."),
    )
    end_date = models.DateField(
        help_text=_("Period end date."),
    )

    total_hours = models.DecimalField(
        max_digits=7,
        decimal_places=2,
        default=Decimal("0.00"),
        help_text=_("Total logged hours in period."),
    )
    billable_hours = models.DecimalField(
        max_digits=7,
        decimal_places=2,
        default=Decimal("0.00"),
        help_text=_("Total billable hours."),
    )
    non_billable_hours = models.DecimalField(
        max_digits=7,
        decimal_places=2,
        default=Decimal("0.00"),
        help_text=_("Total non-billable hours."),
    )
    overtime_hours = models.DecimalField(
        max_digits=7,
        decimal_places=2,
        default=Decimal("0.00"),
        help_text=_("Calculated overtime hours."),
    )

    status = models.CharField(
        max_length=50,
        choices=TimesheetStatus.choices,
        default=TimesheetStatus.DRAFT,
        help_text=_("Current timesheet approval status."),
    )

    submitted_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text=_("Submission timestamp."),
    )
    approved_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text=_("Approval timestamp."),
    )
    approver = models.ForeignKey(
        Employee,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="approved_timesheets",
        help_text=_("Approving manager employee."),
    )

    rejection_reason = models.TextField(
        blank=True,
        help_text=_("Rejection comments if rejected."),
    )

    class Meta:
        verbose_name = _("Timesheet")
        verbose_name_plural = _("Timesheets")
        unique_together = ("employee", "period_type", "start_date")
        ordering = ["-start_date"]

    def __str__(self) -> str:
        return f"{self.employee.display_name} Timesheet [{self.start_date} to {self.end_date}] ({self.status})"


class TimesheetApprovalLog(BaseModel):
    """Audit log history for timesheet approvals, rejections, and submissions."""

    timesheet = models.ForeignKey(
        Timesheet,
        on_delete=models.CASCADE,
        related_name="approval_logs",
        help_text=_("Target timesheet."),
    )
    actor_user_id = models.CharField(
        max_length=100,
        help_text=_("User ID of actor."),
    )
    action = models.CharField(
        max_length=50,
        help_text=_("Action key (e.g. SUBMITTED, APPROVED, REJECTED)."),
    )
    comments = models.TextField(
        blank=True,
        help_text=_("Action approval / rejection comments."),
    )

    class Meta:
        verbose_name = _("Timesheet Approval Log")
        verbose_name_plural = _("Timesheet Approval Logs")
        ordering = ["-created_at"]

    def __str__(self) -> str:
        return f"[{self.action}] Timesheet {self.timesheet.id} by User {self.actor_user_id}"


class OvertimeRecord(BaseModel):
    """Reusable daily/weekly overtime tracking structure for payroll integration."""

    employee = models.ForeignKey(
        Employee,
        on_delete=models.PROTECT,
        related_name="overtime_records",
        help_text=_("Target employee."),
    )
    date = models.DateField(
        help_text=_("Date of overtime."),
    )
    regular_hours = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=Decimal("8.00"),
        help_text=_("Regular work hours."),
    )
    overtime_hours = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=Decimal("0.00"),
        help_text=_("Overtime hours logged."),
    )
    category = models.CharField(
        max_length=50,
        choices=OvertimeCategory.choices,
        default=OvertimeCategory.DAILY_OVERTIME,
        help_text=_("Overtime category classification."),
    )

    class Meta:
        verbose_name = _("Overtime Record")
        verbose_name_plural = _("Overtime Records")
        unique_together = ("employee", "date", "category")

    def __str__(self) -> str:
        return f"{self.employee.display_name} - {self.overtime_hours}h OT on {self.date}"


# ── Enterprise Resource Planning, Capacity & Workload Models ─────────────


class ResourceAllocation(BaseModel):
    """Resource allocation model supporting percentage allocations and concurrent assignments."""

    organization = models.ForeignKey(
        Organization,
        on_delete=models.PROTECT,
        related_name="resource_allocations",
        help_text=_("Owning organization."),
    )
    project = models.ForeignKey(
        Project,
        on_delete=models.CASCADE,
        related_name="resource_allocations",
        help_text=_("Allocated project."),
    )
    task = models.ForeignKey(
        Task,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="resource_allocations",
        help_text=_("Optional specific task allocation."),
    )
    employee = models.ForeignKey(
        Employee,
        on_delete=models.PROTECT,
        related_name="resource_allocations",
        help_text=_("Allocated employee."),
    )

    allocation_type = models.CharField(
        max_length=50,
        choices=AllocationType.choices,
        default=AllocationType.PROJECT,
        help_text=_("Type of allocation."),
    )
    allocation_percentage = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=Decimal("100.00"),
        help_text=_("Allocation percentage (e.g. 50.00 for 50%)."),
    )
    allocated_hours_per_day = models.DecimalField(
        max_digits=4,
        decimal_places=2,
        default=Decimal("8.00"),
        help_text=_("Daily planned capacity hours (e.g. 4.00h)."),
    )

    start_date = models.DateField(
        help_text=_("Allocation start date."),
    )
    end_date = models.DateField(
        help_text=_("Allocation end date."),
    )

    status = models.CharField(
        max_length=50,
        choices=AllocationStatus.choices,
        default=AllocationStatus.ACTIVE,
        help_text=_("Allocation status."),
    )

    notes = models.TextField(
        blank=True,
        help_text=_("Allocation assignment notes."),
    )

    class Meta:
        verbose_name = _("Resource Allocation")
        verbose_name_plural = _("Resource Allocations")
        ordering = ["-start_date"]
        indexes = [
            models.Index(fields=["employee", "start_date", "end_date"], name="idx_resalloc_emp_dates"),
            models.Index(fields=["project", "status"], name="idx_resalloc_proj_status"),
        ]

    def __str__(self) -> str:
        return f"{self.employee.display_name} -> {self.project.code} ({self.allocation_percentage}%)"


class ResourceSkillRequirement(BaseModel):
    """Required skill profile for project or task resource matching."""

    organization = models.ForeignKey(
        Organization,
        on_delete=models.PROTECT,
        related_name="skill_requirements",
        help_text=_("Owning organization."),
    )
    project = models.ForeignKey(
        Project,
        on_delete=models.CASCADE,
        related_name="skill_requirements",
        help_text=_("Target project."),
    )
    task = models.ForeignKey(
        Task,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="skill_requirements",
        help_text=_("Optional target task."),
    )

    skill_name = models.CharField(
        max_length=100,
        help_text=_("Skill name (e.g. Python, React, PostgreSQL)."),
    )
    min_proficiency_level = models.IntegerField(
        default=3,
        help_text=_("Minimum required proficiency scale (1-5)."),
    )

    class Meta:
        verbose_name = _("Resource Skill Requirement")
        verbose_name_plural = _("Resource Skill Requirements")
        ordering = ["skill_name"]

    def __str__(self) -> str:
        return f"{self.project.code} requires {self.skill_name} (Level {self.min_proficiency_level}+)"


class ResourceCapacitySnapshot(BaseModel):
    """Capacity snapshot for workload and forecast analysis."""

    organization = models.ForeignKey(
        Organization,
        on_delete=models.PROTECT,
        related_name="capacity_snapshots",
        help_text=_("Owning organization."),
    )
    employee = models.ForeignKey(
        Employee,
        on_delete=models.PROTECT,
        related_name="capacity_snapshots",
        help_text=_("Target employee."),
    )

    period_start = models.DateField(
        help_text=_("Snapshot period start."),
    )
    period_end = models.DateField(
        help_text=_("Snapshot period end."),
    )

    planned_capacity_hours = models.DecimalField(
        max_digits=7,
        decimal_places=2,
        default=Decimal("160.00"),
        help_text=_("Total available working hours in period."),
    )
    allocated_hours = models.DecimalField(
        max_digits=7,
        decimal_places=2,
        default=Decimal("0.00"),
        help_text=_("Total allocated hours across projects."),
    )
    actual_logged_hours = models.DecimalField(
        max_digits=7,
        decimal_places=2,
        default=Decimal("0.00"),
        help_text=_("Actual worklog hours logged."),
    )

    utilization_rate = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=Decimal("0.00"),
        help_text=_("Utilization percentage (0 - 100+ %)."),
    )

    workload_status = models.CharField(
        max_length=50,
        choices=WorkloadStatus.choices,
        default=WorkloadStatus.OPTIMAL,
        help_text=_("Workload utilization classification."),
    )

    class Meta:
        verbose_name = _("Resource Capacity Snapshot")
        verbose_name_plural = _("Resource Capacity Snapshots")
        ordering = ["-period_start"]

    def __str__(self) -> str:
        return f"{self.employee.display_name} Capacity [{self.period_start}] ({self.utilization_rate}%)"


# ── Enterprise Portfolio Management, Program & PMO Models ─────────────────


class Portfolio(BaseModel):
    """Strategic portfolio container grouping programs and projects."""

    organization = models.ForeignKey(
        Organization,
        on_delete=models.PROTECT,
        related_name="portfolios",
        help_text=_("Owning organization."),
    )
    owner = models.ForeignKey(
        Employee,
        on_delete=models.PROTECT,
        related_name="owned_portfolios",
        help_text=_("Portfolio owner / director."),
    )
    executive_sponsor = models.ForeignKey(
        Employee,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="sponsored_portfolios",
        help_text=_("Executive C-level sponsor."),
    )

    code = models.CharField(
        max_length=50,
        unique=True,
        help_text=_("Unique portfolio code (e.g. PORT-STRAT-001)."),
    )
    name = models.CharField(
        max_length=200,
        help_text=_("Portfolio name."),
    )
    portfolio_type = models.CharField(
        max_length=50,
        choices=PortfolioType.choices,
        default=PortfolioType.STRATEGIC,
        help_text=_("Portfolio classification type."),
    )
    description = models.TextField(
        blank=True,
        help_text=_("Portfolio strategic vision and objectives."),
    )

    budget = models.DecimalField(
        max_digits=14,
        decimal_places=2,
        default=Decimal("0.00"),
        help_text=_("Total allocated portfolio budget."),
    )
    priority = models.IntegerField(
        default=1,
        help_text=_("Strategic priority rank (1 = Highest)."),
    )

    status = models.CharField(
        max_length=50,
        choices=PortfolioStatus.choices,
        default=PortfolioStatus.ACTIVE,
        help_text=_("Portfolio lifecycle status."),
    )

    class Meta:
        verbose_name = _("Portfolio")
        verbose_name_plural = _("Portfolios")
        ordering = ["priority", "name"]

    def __str__(self) -> str:
        return f"{self.name} [{self.code}] ({self.portfolio_type})"


class Program(BaseModel):
    """Cross-functional program container grouping strategic multi-project initiatives."""

    organization = models.ForeignKey(
        Organization,
        on_delete=models.PROTECT,
        related_name="programs",
        help_text=_("Owning organization."),
    )
    program_manager = models.ForeignKey(
        Employee,
        on_delete=models.PROTECT,
        related_name="managed_programs",
        help_text=_("Designated program manager."),
    )
    portfolio = models.ForeignKey(
        Portfolio,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="programs",
        help_text=_("Parent strategic portfolio if mapped."),
    )

    code = models.CharField(
        max_length=50,
        unique=True,
        help_text=_("Unique program code (e.g. PRG-DIG-TRANS)."),
    )
    name = models.CharField(
        max_length=200,
        help_text=_("Program name."),
    )
    description = models.TextField(
        blank=True,
        help_text=_("Program charter and objectives."),
    )

    budget = models.DecimalField(
        max_digits=14,
        decimal_places=2,
        default=Decimal("0.00"),
        help_text=_("Allocated program budget."),
    )
    target_start_date = models.DateField(
        null=True,
        blank=True,
        help_text=_("Target start date."),
    )
    target_end_date = models.DateField(
        null=True,
        blank=True,
        help_text=_("Target completion date."),
    )

    status = models.CharField(
        max_length=50,
        choices=ProgramStatus.choices,
        default=ProgramStatus.ACTIVE,
        help_text=_("Program lifecycle status."),
    )

    class Meta:
        verbose_name = _("Program")
        verbose_name_plural = _("Programs")
        ordering = ["code"]

    def __str__(self) -> str:
        return f"{self.name} [{self.code}]"


class PortfolioProjectMapping(BaseModel):
    """Many-to-many relationship mapping projects into multiple portfolios."""

    portfolio = models.ForeignKey(
        Portfolio,
        on_delete=models.CASCADE,
        related_name="project_mappings",
        help_text=_("Target portfolio."),
    )
    project = models.ForeignKey(
        Project,
        on_delete=models.CASCADE,
        related_name="portfolio_mappings",
        help_text=_("Mapped project."),
    )
    strategic_weight = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=Decimal("1.00"),
        help_text=_("Strategic weighting in portfolio (e.g. 1.00)."),
    )

    class Meta:
        verbose_name = _("Portfolio Project Mapping")
        verbose_name_plural = _("Portfolio Project Mappings")
        unique_together = ("portfolio", "project")

    def __str__(self) -> str:
        return f"Project {self.project.code} -> Portfolio {self.portfolio.code}"


class PortfolioRisk(BaseModel):
    """Portfolio or Program risk log entity."""

    organization = models.ForeignKey(
        Organization,
        on_delete=models.PROTECT,
        related_name="portfolio_risks",
        help_text=_("Owning organization."),
    )
    portfolio = models.ForeignKey(
        Portfolio,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="risks",
        help_text=_("Associated portfolio."),
    )
    program = models.ForeignKey(
        Program,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="risks",
        help_text=_("Associated program."),
    )
    project = models.ForeignKey(
        Project,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="risks",
        help_text=_("Associated project."),
    )
    risk_owner = models.ForeignKey(
        Employee,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="owned_risks",
        help_text=_("Designated risk owner."),
    )

    title = models.CharField(
        max_length=200,
        help_text=_("Risk summary title."),
    )
    description = models.TextField(
        blank=True,
        help_text=_("Detailed risk description."),
    )

    probability = models.IntegerField(
        default=3,
        help_text=_("Probability scale (1 = Rare, 5 = Almost Certain)."),
    )
    impact = models.IntegerField(
        default=3,
        help_text=_("Impact scale (1 = Negligible, 5 = Severe)."),
    )
    risk_score = models.IntegerField(
        default=9,
        help_text=_("Calculated risk score (Probability * Impact: 1 - 25)."),
    )

    risk_level = models.CharField(
        max_length=50,
        choices=RiskLevel.choices,
        default=RiskLevel.MEDIUM,
        help_text=_("Risk severity classification."),
    )
    status = models.CharField(
        max_length=50,
        choices=RiskStatus.choices,
        default=RiskStatus.IDENTIFIED,
        help_text=_("Current risk status."),
    )

    mitigation_plan = models.TextField(
        blank=True,
        help_text=_("Actionable mitigation plan."),
    )

    class Meta:
        verbose_name = _("Portfolio Risk")
        verbose_name_plural = _("Portfolio Risks")
        ordering = ["-risk_score", "-created_at"]

    def __str__(self) -> str:
        return f"{self.title} (Score: {self.risk_score} - {self.risk_level})"


class PortfolioMilestone(BaseModel):
    """Program or Portfolio level strategic milestone."""

    organization = models.ForeignKey(
        Organization,
        on_delete=models.PROTECT,
        related_name="portfolio_milestones",
        help_text=_("Owning organization."),
    )
    portfolio = models.ForeignKey(
        Portfolio,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="milestones",
        help_text=_("Associated portfolio."),
    )
    program = models.ForeignKey(
        Program,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="milestones",
        help_text=_("Associated program."),
    )

    title = models.CharField(
        max_length=200,
        help_text=_("Milestone title."),
    )
    description = models.TextField(
        blank=True,
        help_text=_("Milestone deliverables."),
    )
    target_date = models.DateField(
        help_text=_("Target delivery date."),
    )
    achieved_date = models.DateField(
        null=True,
        blank=True,
        help_text=_("Date milestone was achieved."),
    )

    is_completed = models.BooleanField(
        default=False,
        help_text=_("Whether milestone has been achieved."),
    )

    class Meta:
        verbose_name = _("Portfolio Milestone")
        verbose_name_plural = _("Portfolio Milestones")
        ordering = ["target_date"]

    def __str__(self) -> str:
        return f"{self.title} (Target: {self.target_date})"





