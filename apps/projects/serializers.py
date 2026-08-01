"""DRF Serializers for Enterprise Project Management Foundation Engine."""

from rest_framework import serializers

from .models import (
    BoardColumn,
    KanbanBoard,
    OvertimeRecord,
    Portfolio,
    PortfolioMilestone,
    PortfolioProjectMapping,
    PortfolioRisk,
    Program,
    Project,
    ProjectAuditLog,
    ProjectMember,
    ProjectTeam,
    Release,
    ResourceAllocation,
    ResourceCapacitySnapshot,
    ResourceSkillRequirement,
    Sprint,
    Task,
    TaskActivityLog,
    TaskAssignment,
    TaskChecklist,
    TaskComment,
    TaskDependency,
    TimeEntry,
    Timesheet,
    TimesheetApprovalLog,
)


class ProjectSerializer(serializers.ModelSerializer):
    owner_name = serializers.CharField(source="owner.display_name", read_only=True)
    manager_name = serializers.CharField(source="manager.display_name", read_only=True)

    class Meta:
        model = Project
        fields = [
            "id",
            "organization",
            "branch",
            "department",
            "owner",
            "owner_name",
            "manager",
            "manager_name",
            "code",
            "name",
            "description",
            "project_type",
            "category",
            "status",
            "priority",
            "risk_level",
            "visibility",
            "start_date",
            "end_date",
            "estimated_budget",
            "estimated_hours",
            "is_active",
            "is_archived",
            "settings_json",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "is_active", "is_archived", "created_at", "updated_at"]


class ProjectCreateSerializer(serializers.Serializer):
    organization_id = serializers.UUIDField()
    owner_id = serializers.UUIDField()
    manager_id = serializers.UUIDField()
    code = serializers.CharField(max_length=50)
    name = serializers.CharField(max_length=200)
    description = serializers.CharField(required=False, allow_blank=True, default="")
    project_type = serializers.ChoiceField(
        choices=["INTERNAL", "CLIENT", "DEPARTMENT", "RESEARCH", "MAINTENANCE", "AUTOMATION", "AI", "CUSTOM"],
        default="INTERNAL",
    )
    category = serializers.ChoiceField(
        choices=["SOFTWARE", "MARKETING", "HR", "FINANCE", "OPERATIONS", "INFRASTRUCTURE", "RESEARCH", "CLIENT_DELIVERY", "CUSTOM"],
        default="SOFTWARE",
    )
    priority = serializers.ChoiceField(choices=["LOW", "MEDIUM", "HIGH", "URGENT", "CRITICAL"], default="MEDIUM")
    risk_level = serializers.ChoiceField(choices=["LOW", "MEDIUM", "HIGH", "CRITICAL"], default="LOW")
    visibility = serializers.ChoiceField(choices=["PRIVATE", "INTERNAL", "ORGANIZATION", "CLIENT"], default="ORGANIZATION")
    start_date = serializers.DateField(required=False, allow_null=True)
    end_date = serializers.DateField(required=False, allow_null=True)
    estimated_budget = serializers.DecimalField(max_digits=16, decimal_places=2, default=0.0)
    estimated_hours = serializers.DecimalField(max_digits=12, decimal_places=2, default=0.0)
    branch_id = serializers.UUIDField(required=False, allow_null=True)
    department_id = serializers.UUIDField(required=False, allow_null=True)


class ProjectMemberSerializer(serializers.ModelSerializer):
    employee_code = serializers.CharField(source="employee.employee_id", read_only=True)
    employee_name = serializers.CharField(source="employee.display_name", read_only=True)

    class Meta:
        model = ProjectMember
        fields = [
            "id",
            "project",
            "employee",
            "employee_code",
            "employee_name",
            "role",
            "allocated_hours_per_week",
            "joined_at",
            "left_at",
            "is_active",
        ]
        read_only_fields = ["id", "joined_at", "left_at", "is_active"]


class ProjectMemberAddSerializer(serializers.Serializer):
    employee_id = serializers.UUIDField()
    role = serializers.ChoiceField(
        choices=["OWNER", "MANAGER", "TEAM_LEAD", "DEVELOPER", "QA", "DESIGNER", "BUSINESS_ANALYST", "OBSERVER", "CUSTOM"],
        default="DEVELOPER",
    )
    allocated_hours_per_week = serializers.DecimalField(max_digits=5, decimal_places=2, default=40.0)


class ProjectSettingsUpdateSerializer(serializers.Serializer):
    settings = serializers.DictField()


class ProjectAuditLogSerializer(serializers.ModelSerializer):
    class Meta:
        model = ProjectAuditLog
        fields = [
            "id",
            "project",
            "actor_user_id",
            "action",
            "description",
            "changes_json",
            "created_at",
        ]
        read_only_fields = ["id", "created_at"]


class ProjectStatusActionSerializer(serializers.Serializer):
    reason = serializers.CharField(required=False, allow_blank=True, default="")


# ── Enterprise Task & WBS Serializers ──────────────────────────────────────


class TaskSerializer(serializers.ModelSerializer):
    reporter_name = serializers.CharField(source="reporter.display_name", read_only=True)
    assignee_name = serializers.CharField(source="assignee.display_name", read_only=True) if "assignee" else ""

    class Meta:
        model = Task
        fields = [
            "id",
            "organization",
            "project",
            "parent",
            "epic",
            "reporter",
            "reporter_name",
            "assignee",
            "assignee_name",
            "code",
            "wbs_code",
            "title",
            "description",
            "task_type",
            "status",
            "priority",
            "severity",
            "story_points",
            "estimated_hours",
            "actual_hours",
            "progress_percentage",
            "start_date",
            "due_date",
            "completed_at",
            "is_archived",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "wbs_code", "completed_at", "is_archived", "created_at", "updated_at"]


class TaskCreateSerializer(serializers.Serializer):
    project_id = serializers.UUIDField()
    reporter_id = serializers.UUIDField()
    code = serializers.CharField(max_length=50)
    title = serializers.CharField(max_length=250)
    description = serializers.CharField(required=False, allow_blank=True, default="")
    task_type = serializers.ChoiceField(
        choices=["EPIC", "STORY", "TASK", "SUBTASK", "BUG", "ISSUE", "FEATURE", "SPIKE", "RESEARCH", "IMPROVEMENT", "CUSTOM"],
        default="TASK",
    )
    priority = serializers.ChoiceField(choices=["LOW", "MEDIUM", "HIGH", "URGENT", "CRITICAL"], default="MEDIUM")
    severity = serializers.ChoiceField(choices=["TRIVIAL", "MINOR", "MAJOR", "CRITICAL", "BLOCKER"], default="MINOR")
    parent_id = serializers.UUIDField(required=False, allow_null=True)
    epic_id = serializers.UUIDField(required=False, allow_null=True)
    assignee_id = serializers.UUIDField(required=False, allow_null=True)
    story_points = serializers.DecimalField(max_digits=5, decimal_places=1, default=0.0)
    estimated_hours = serializers.DecimalField(max_digits=8, decimal_places=2, default=0.0)
    start_date = serializers.DateField(required=False, allow_null=True)
    due_date = serializers.DateField(required=False, allow_null=True)


class TaskStatusUpdateSerializer(serializers.Serializer):
    status = serializers.ChoiceField(
        choices=["BACKLOG", "TODO", "IN_PROGRESS", "IN_REVIEW", "BLOCKED", "DONE", "CANCELLED", "ARCHIVED"]
    )
    block_reason = serializers.CharField(required=False, allow_blank=True, default="")


class TaskDependencySerializer(serializers.ModelSerializer):
    source_code = serializers.CharField(source="source_task.code", read_only=True)
    target_code = serializers.CharField(source="target_task.code", read_only=True)

    class Meta:
        model = TaskDependency
        fields = ["id", "source_task", "source_code", "target_task", "target_code", "dependency_type", "created_at"]
        read_only_fields = ["id", "created_at"]


class TaskDependencyCreateSerializer(serializers.Serializer):
    source_task_id = serializers.UUIDField()
    target_task_id = serializers.UUIDField()
    dependency_type = serializers.ChoiceField(
        choices=["FINISH_TO_START", "START_TO_START", "FINISH_TO_FINISH", "START_TO_FINISH"],
        default="FINISH_TO_START",
    )


class TaskChecklistSerializer(serializers.ModelSerializer):
    class Meta:
        model = TaskChecklist
        fields = ["id", "task", "title", "is_completed", "completed_at", "created_at"]
        read_only_fields = ["id", "completed_at", "created_at"]


class TaskChecklistCreateSerializer(serializers.Serializer):
    title = serializers.CharField(max_length=200)


class TaskCommentSerializer(serializers.ModelSerializer):
    class Meta:
        model = TaskComment
        fields = [
            "id",
            "task",
            "parent_comment",
            "author_user_id",
            "author_name",
            "content",
            "is_internal_note",
            "created_at",
        ]
        read_only_fields = ["id", "created_at"]


class TaskCommentCreateSerializer(serializers.Serializer):
    content = serializers.CharField(required=True)
    parent_comment_id = serializers.UUIDField(required=False, allow_null=True)
    is_internal_note = serializers.BooleanField(default=False)


class TaskActivityLogSerializer(serializers.ModelSerializer):
    class Meta:
        model = TaskActivityLog
        fields = ["id", "task", "actor_user_id", "action", "description", "metadata_json", "created_at"]
        read_only_fields = ["id", "created_at"]


# ── Enterprise Agile Delivery, Sprint & Kanban Serializers ─────────────────


class SprintSerializer(serializers.ModelSerializer):
    owner_name = serializers.CharField(source="owner.display_name", read_only=True)

    class Meta:
        model = Sprint
        fields = [
            "id",
            "organization",
            "project",
            "team",
            "owner",
            "owner_name",
            "sprint_number",
            "name",
            "goal",
            "sprint_type",
            "status",
            "start_date",
            "end_date",
            "completed_at",
            "capacity_hours",
            "total_story_points",
            "completed_story_points",
            "velocity",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "sprint_number", "completed_at", "total_story_points", "completed_story_points", "velocity", "created_at", "updated_at"]


class SprintCreateSerializer(serializers.Serializer):
    project_id = serializers.UUIDField()
    owner_id = serializers.UUIDField()
    team_id = serializers.UUIDField(required=False, allow_null=True, default=None)
    name = serializers.CharField(max_length=150)
    goal = serializers.CharField(required=False, allow_blank=True, default="")
    sprint_type = serializers.ChoiceField(
        choices=["REGULAR", "ITERATION", "RELEASE", "PLANNING", "HARDENING", "CUSTOM"],
        default="REGULAR",
    )
    start_date = serializers.DateField()
    end_date = serializers.DateField()
    capacity_hours = serializers.DecimalField(max_digits=8, decimal_places=2, default=0.0)


class BoardColumnSerializer(serializers.ModelSerializer):
    cards_count = serializers.SerializerMethodField()

    class Meta:
        model = BoardColumn
        fields = ["id", "board", "name", "order", "wip_limit", "mapped_status", "policy_description", "cards_count"]

    def get_cards_count(self, obj):
        return obj.tasks.filter(is_archived=False).count()


class KanbanBoardSerializer(serializers.ModelSerializer):
    columns = BoardColumnSerializer(many=True, read_only=True)

    class Meta:
        model = KanbanBoard
        fields = ["id", "organization", "project", "name", "board_type", "description", "estimation_scale", "columns", "created_at"]
        read_only_fields = ["id", "created_at"]


class KanbanBoardCreateSerializer(serializers.Serializer):
    project_id = serializers.UUIDField()
    name = serializers.CharField(max_length=150)
    board_type = serializers.ChoiceField(choices=["SCRUM", "KANBAN", "HYBRID"], default="KANBAN")
    description = serializers.CharField(required=False, allow_blank=True, default="")
    estimation_scale = serializers.ChoiceField(choices=["FIBONACCI", "T_SHIRT", "HOURS", "CUSTOM"], default="FIBONACCI")


class TaskMoveOnBoardSerializer(serializers.Serializer):
    target_column_id = serializers.UUIDField()


class ReleaseSerializer(serializers.ModelSerializer):
    class Meta:
        model = Release
        fields = ["id", "organization", "project", "name", "version", "description", "target_date", "released_at", "is_released", "created_at"]
        read_only_fields = ["id", "released_at", "is_released", "created_at"]


class ReleaseCreateSerializer(serializers.Serializer):
    project_id = serializers.UUIDField()
    name = serializers.CharField(max_length=150)
    version = serializers.CharField(max_length=50)
    description = serializers.CharField(required=False, allow_blank=True, default="")
    target_date = serializers.DateField(required=False, allow_null=True)


# ── Enterprise Time Tracking, Timesheet & Worklog Serializers ─────────────


class TimeEntrySerializer(serializers.ModelSerializer):
    employee_name = serializers.CharField(source="employee.display_name", read_only=True)
    task_code = serializers.CharField(source="task.code", read_only=True)
    project_code = serializers.CharField(source="project.code", read_only=True)

    class Meta:
        model = TimeEntry
        fields = [
            "id",
            "organization",
            "project",
            "project_code",
            "task",
            "task_code",
            "sprint",
            "employee",
            "employee_name",
            "entry_type",
            "billable_type",
            "date",
            "hours",
            "start_time",
            "end_time",
            "is_timer_running",
            "timer_started_at",
            "notes",
            "is_approved",
            "is_locked",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "is_approved", "is_locked", "created_at", "updated_at"]


class TimerStartSerializer(serializers.Serializer):
    task_id = serializers.UUIDField()
    notes = serializers.CharField(required=False, allow_blank=True, default="")
    billable_type = serializers.ChoiceField(
        choices=["BILLABLE", "NON_BILLABLE", "INTERNAL", "TRAINING", "MEETING", "RESEARCH"],
        default="BILLABLE",
    )


class TimeEntryCreateSerializer(serializers.Serializer):
    employee_id = serializers.UUIDField()
    task_id = serializers.UUIDField()
    date = serializers.DateField()
    hours = serializers.DecimalField(max_digits=5, decimal_places=2)
    notes = serializers.CharField(required=False, allow_blank=True, default="")
    billable_type = serializers.ChoiceField(
        choices=["BILLABLE", "NON_BILLABLE", "INTERNAL", "TRAINING", "MEETING", "RESEARCH"],
        default="BILLABLE",
    )


class TimesheetSerializer(serializers.ModelSerializer):
    employee_name = serializers.CharField(source="employee.display_name", read_only=True)
    approver_name = serializers.CharField(source="approver.display_name", read_only=True)

    class Meta:
        model = Timesheet
        fields = [
            "id",
            "organization",
            "employee",
            "employee_name",
            "project",
            "period_type",
            "start_date",
            "end_date",
            "total_hours",
            "billable_hours",
            "non_billable_hours",
            "overtime_hours",
            "status",
            "submitted_at",
            "approved_at",
            "approver",
            "approver_name",
            "rejection_reason",
            "created_at",
            "updated_at",
        ]
        read_only_fields = [
            "id",
            "total_hours",
            "billable_hours",
            "non_billable_hours",
            "overtime_hours",
            "status",
            "submitted_at",
            "approved_at",
            "approver",
            "created_at",
            "updated_at",
        ]


class TimesheetSubmitSerializer(serializers.Serializer):
    employee_id = serializers.UUIDField()
    period_type = serializers.ChoiceField(choices=["DAILY", "WEEKLY", "BIWEEKLY", "MONTHLY"], default="WEEKLY")
    start_date = serializers.DateField()
    end_date = serializers.DateField()
    project_id = serializers.UUIDField(required=False, allow_null=True)


class TimesheetApprovalActionSerializer(serializers.Serializer):
    approver_id = serializers.UUIDField()
    comments = serializers.CharField(required=False, allow_blank=True, default="")


# ── Enterprise Resource Planning & Capacity Serializers ───────────────────


class ResourceAllocationSerializer(serializers.ModelSerializer):
    employee_name = serializers.CharField(source="employee.display_name", read_only=True)
    project_code = serializers.CharField(source="project.code", read_only=True)

    class Meta:
        model = ResourceAllocation
        fields = [
            "id",
            "organization",
            "project",
            "project_code",
            "task",
            "employee",
            "employee_name",
            "allocation_type",
            "allocation_percentage",
            "allocated_hours_per_day",
            "start_date",
            "end_date",
            "status",
            "notes",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "allocated_hours_per_day", "created_at", "updated_at"]


class ResourceAllocationCreateSerializer(serializers.Serializer):
    employee_id = serializers.UUIDField()
    project_id = serializers.UUIDField()
    task_id = serializers.UUIDField(required=False, allow_null=True, default=None)
    allocation_type = serializers.ChoiceField(
        choices=["PROJECT", "TASK", "TEAM", "BENCH", "TRAINING"],
        default="PROJECT",
    )
    allocation_percentage = serializers.DecimalField(max_digits=5, decimal_places=2, default=100.0)
    start_date = serializers.DateField()
    end_date = serializers.DateField()
    notes = serializers.CharField(required=False, allow_blank=True, default="")


class ResourceSkillRequirementSerializer(serializers.ModelSerializer):
    class Meta:
        model = ResourceSkillRequirement
        fields = ["id", "organization", "project", "task", "skill_name", "min_proficiency_level", "created_at"]
        read_only_fields = ["id", "created_at"]


# ── Enterprise Portfolio Management, Program & PMO Serializers ───────────


class PortfolioSerializer(serializers.ModelSerializer):
    owner_name = serializers.CharField(source="owner.display_name", read_only=True)
    sponsor_name = serializers.CharField(source="executive_sponsor.display_name", read_only=True)

    class Meta:
        model = Portfolio
        fields = [
            "id",
            "organization",
            "code",
            "name",
            "portfolio_type",
            "owner",
            "owner_name",
            "executive_sponsor",
            "sponsor_name",
            "description",
            "budget",
            "priority",
            "status",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "created_at", "updated_at"]


class PortfolioCreateSerializer(serializers.Serializer):
    organization_id = serializers.UUIDField()
    owner_id = serializers.UUIDField()
    executive_sponsor_id = serializers.UUIDField(required=False, allow_null=True, default=None)
    code = serializers.CharField(max_length=50)
    name = serializers.CharField(max_length=200)
    portfolio_type = serializers.ChoiceField(
        choices=["STRATEGIC", "TECHNOLOGY", "CLIENT", "DEPARTMENT", "BUSINESS_UNIT", "REGIONAL", "CUSTOM"],
        default="STRATEGIC",
    )
    description = serializers.CharField(required=False, allow_blank=True, default="")
    budget = serializers.DecimalField(max_digits=14, decimal_places=2, default=0.0)
    priority = serializers.IntegerField(default=1)


class ProgramSerializer(serializers.ModelSerializer):
    program_manager_name = serializers.CharField(source="program_manager.display_name", read_only=True)
    portfolio_name = serializers.CharField(source="portfolio.name", read_only=True)

    class Meta:
        model = Program
        fields = [
            "id",
            "organization",
            "code",
            "name",
            "program_manager",
            "program_manager_name",
            "portfolio",
            "portfolio_name",
            "description",
            "budget",
            "target_start_date",
            "target_end_date",
            "status",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "created_at", "updated_at"]


class ProgramCreateSerializer(serializers.Serializer):
    organization_id = serializers.UUIDField()
    program_manager_id = serializers.UUIDField()
    portfolio_id = serializers.UUIDField(required=False, allow_null=True, default=None)
    code = serializers.CharField(max_length=50)
    name = serializers.CharField(max_length=200)
    description = serializers.CharField(required=False, allow_blank=True, default="")
    budget = serializers.DecimalField(max_digits=14, decimal_places=2, default=0.0)
    target_start_date = serializers.DateField(required=False, allow_null=True)
    target_end_date = serializers.DateField(required=False, allow_null=True)


class PortfolioRiskSerializer(serializers.ModelSerializer):
    risk_owner_name = serializers.CharField(source="risk_owner.display_name", read_only=True)

    class Meta:
        model = PortfolioRisk
        fields = [
            "id",
            "organization",
            "portfolio",
            "program",
            "project",
            "risk_owner",
            "risk_owner_name",
            "title",
            "description",
            "probability",
            "impact",
            "risk_score",
            "risk_level",
            "status",
            "mitigation_plan",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "risk_score", "risk_level", "created_at", "updated_at"]


class PortfolioMilestoneSerializer(serializers.ModelSerializer):
    class Meta:
        model = PortfolioMilestone
        fields = [
            "id",
            "organization",
            "portfolio",
            "program",
            "title",
            "description",
            "target_date",
            "achieved_date",
            "is_completed",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "achieved_date", "is_completed", "created_at", "updated_at"]





