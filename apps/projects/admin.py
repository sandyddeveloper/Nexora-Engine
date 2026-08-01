"""Django Admin registration for Enterprise Project Management Foundation Engine."""

from django.contrib import admin

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


@admin.register(Project)
class ProjectAdmin(admin.ModelAdmin):
    list_display = ("code", "name", "organization", "project_type", "category", "status", "priority", "owner", "manager", "is_active")
    list_filter = ("project_type", "category", "status", "priority", "risk_level", "is_active", "is_archived")
    search_fields = ("code", "name", "organization__name", "owner__first_name", "manager__first_name")


@admin.register(ProjectTeam)
class ProjectTeamAdmin(admin.ModelAdmin):
    list_display = ("name", "project")
    search_fields = ("name", "project__code", "project__name")


@admin.register(ProjectMember)
class ProjectMemberAdmin(admin.ModelAdmin):
    list_display = ("project", "employee", "role", "allocated_hours_per_week", "joined_at", "is_active")
    list_filter = ("role", "is_active")
    search_fields = ("project__code", "employee__first_name", "employee__last_name", "employee__employee_id")


@admin.register(ProjectAuditLog)
class ProjectAuditLogAdmin(admin.ModelAdmin):
    list_display = ("project", "action", "actor_user_id", "created_at")
    list_filter = ("action",)
    search_fields = ("project__code", "action", "description")


@admin.register(Task)
class TaskAdmin(admin.ModelAdmin):
    list_display = ("code", "title", "project", "task_type", "status", "priority", "severity", "wbs_code", "assignee")
    list_filter = ("task_type", "status", "priority", "severity", "is_archived")
    search_fields = ("code", "title", "project__code", "assignee__first_name")


@admin.register(TaskAssignment)
class TaskAssignmentAdmin(admin.ModelAdmin):
    list_display = ("task", "employee", "role", "assigned_at")
    list_filter = ("role",)


@admin.register(TaskDependency)
class TaskDependencyAdmin(admin.ModelAdmin):
    list_display = ("source_task", "target_task", "dependency_type")
    list_filter = ("dependency_type",)


@admin.register(TaskChecklist)
class TaskChecklistAdmin(admin.ModelAdmin):
    list_display = ("task", "title", "is_completed", "completed_at")
    list_filter = ("is_completed",)


@admin.register(TaskComment)
class TaskCommentAdmin(admin.ModelAdmin):
    list_display = ("task", "author_name", "is_internal_note", "created_at")
    list_filter = ("is_internal_note",)


@admin.register(TaskActivityLog)
class TaskActivityLogAdmin(admin.ModelAdmin):
    list_display = ("task", "action", "actor_user_id", "created_at")
    list_filter = ("action",)


@admin.register(Sprint)
class SprintAdmin(admin.ModelAdmin):
    list_display = ("name", "sprint_number", "project", "sprint_type", "status", "start_date", "end_date", "velocity")
    list_filter = ("sprint_type", "status")
    search_fields = ("name", "project__code", "goal")


@admin.register(KanbanBoard)
class KanbanBoardAdmin(admin.ModelAdmin):
    list_display = ("name", "project", "board_type", "estimation_scale")
    list_filter = ("board_type", "estimation_scale")
    search_fields = ("name", "project__code")


@admin.register(BoardColumn)
class BoardColumnAdmin(admin.ModelAdmin):
    list_display = ("name", "board", "order", "wip_limit", "mapped_status")
    list_filter = ("mapped_status",)


@admin.register(Release)
class ReleaseAdmin(admin.ModelAdmin):
    list_display = ("name", "version", "project", "target_date", "is_released")
    list_filter = ("is_released",)
    search_fields = ("name", "version", "project__code")


@admin.register(TimeEntry)
class TimeEntryAdmin(admin.ModelAdmin):
    list_display = ("employee", "task", "project", "date", "hours", "entry_type", "billable_type", "is_timer_running", "is_approved")
    list_filter = ("entry_type", "billable_type", "is_timer_running", "is_approved")
    search_fields = ("employee__first_name", "task__code", "project__code", "notes")


@admin.register(Timesheet)
class TimesheetAdmin(admin.ModelAdmin):
    list_display = ("employee", "period_type", "start_date", "end_date", "total_hours", "billable_hours", "status", "approver")
    list_filter = ("period_type", "status")
    search_fields = ("employee__first_name", "employee__last_name")


@admin.register(TimesheetApprovalLog)
class TimesheetApprovalLogAdmin(admin.ModelAdmin):
    list_display = ("timesheet", "action", "actor_user_id", "created_at")
    list_filter = ("action",)


@admin.register(OvertimeRecord)
class OvertimeRecordAdmin(admin.ModelAdmin):
    list_display = ("employee", "date", "regular_hours", "overtime_hours", "category")
    list_filter = ("category",)


@admin.register(ResourceAllocation)
class ResourceAllocationAdmin(admin.ModelAdmin):
    list_display = ("employee", "project", "allocation_type", "allocation_percentage", "allocated_hours_per_day", "start_date", "end_date", "status")
    list_filter = ("allocation_type", "status")
    search_fields = ("employee__first_name", "project__code")


@admin.register(ResourceSkillRequirement)
class ResourceSkillRequirementAdmin(admin.ModelAdmin):
    list_display = ("project", "skill_name", "min_proficiency_level")
    search_fields = ("project__code", "skill_name")


@admin.register(ResourceCapacitySnapshot)
class ResourceCapacitySnapshotAdmin(admin.ModelAdmin):
    list_display = ("employee", "period_start", "planned_capacity_hours", "allocated_hours", "utilization_rate", "workload_status")
    list_filter = ("workload_status",)


@admin.register(Portfolio)
class PortfolioAdmin(admin.ModelAdmin):
    list_display = ("name", "code", "portfolio_type", "owner", "executive_sponsor", "budget", "priority", "status")
    list_filter = ("portfolio_type", "status")
    search_fields = ("name", "code")


@admin.register(Program)
class ProgramAdmin(admin.ModelAdmin):
    list_display = ("name", "code", "program_manager", "portfolio", "budget", "status")
    list_filter = ("status",)
    search_fields = ("name", "code")


@admin.register(PortfolioRisk)
class PortfolioRiskAdmin(admin.ModelAdmin):
    list_display = ("title", "portfolio", "program", "project", "risk_score", "risk_level", "status", "risk_owner")
    list_filter = ("risk_level", "status")
    search_fields = ("title",)


@admin.register(PortfolioMilestone)
class PortfolioMilestoneAdmin(admin.ModelAdmin):
    list_display = ("title", "portfolio", "program", "target_date", "is_completed")
    list_filter = ("is_completed",)
    search_fields = ("title",)





