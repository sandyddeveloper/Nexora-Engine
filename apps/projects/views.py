"""Thin REST API views for Enterprise Project Management Foundation Engine."""

from drf_spectacular.utils import extend_schema, extend_schema_view
from rest_framework.permissions import IsAuthenticated
from rest_framework.views import APIView

from core.responses import (
    created_response,
    not_found_response,
    success_response,
    validation_error_response,
)
from apps.employees.models import Employee
from apps.employees.selectors import get_employee
from apps.organizations.selectors import get_branch, get_department, get_organization

from . import selectors, services
from .serializers import (
    KanbanBoardCreateSerializer,
    KanbanBoardSerializer,
    PortfolioCreateSerializer,
    PortfolioMilestoneSerializer,
    PortfolioRiskSerializer,
    PortfolioSerializer,
    ProgramCreateSerializer,
    ProgramSerializer,
    ProjectAuditLogSerializer,
    ProjectCreateSerializer,
    ProjectMemberAddSerializer,
    ProjectMemberSerializer,
    ProjectSerializer,
    ProjectSettingsUpdateSerializer,
    ProjectStatusActionSerializer,
    ReleaseCreateSerializer,
    ReleaseSerializer,
    ResourceAllocationCreateSerializer,
    ResourceAllocationSerializer,
    ResourceSkillRequirementSerializer,
    SprintCreateSerializer,
    SprintSerializer,
    TaskActivityLogSerializer,
    TaskChecklistCreateSerializer,
    TaskChecklistSerializer,
    TaskCommentCreateSerializer,
    TaskCommentSerializer,
    TaskCreateSerializer,
    TaskDependencyCreateSerializer,
    TaskDependencySerializer,
    TaskMoveOnBoardSerializer,
    TaskSerializer,
    TaskStatusUpdateSerializer,
    TimeEntryCreateSerializer,
    TimeEntrySerializer,
    TimerStartSerializer,
    TimesheetApprovalActionSerializer,
    TimesheetSerializer,
    TimesheetSubmitSerializer,
)


@extend_schema_view(
    get=extend_schema(
        tags=["Project Management"],
        summary="List Projects",
        description="Retrieve projects for an organization filtered by status, category, or project type.",
    ),
    post=extend_schema(
        tags=["Project Management"],
        summary="Create Project",
        description="Create a new enterprise project with designated owner, manager, and settings.",
    ),
)
class ProjectListCreateAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        organization_id = request.query_params.get("organization_id")
        if not organization_id:
            return validation_error_response(message="organization_id query parameter is required.")

        status = request.query_params.get("status", "")
        project_type = request.query_params.get("project_type", "")
        category = request.query_params.get("category", "")
        search = request.query_params.get("search", "")

        projects = selectors.list_projects(
            organization_id=organization_id,
            status=status,
            project_type=project_type,
            category=category,
            search=search,
        )
        return success_response(
            message="Projects retrieved successfully.",
            data=ProjectSerializer(projects, many=True).data,
        )

    def post(self, request):
        serializer = ProjectCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        org = get_organization(organization_id=data["organization_id"])
        if not org:
            return not_found_response(message="Organization not found.")

        owner = get_employee(employee_id=data["owner_id"])
        if not owner:
            return not_found_response(message="Project owner employee not found.")

        manager = get_employee(employee_id=data["manager_id"])
        if not manager:
            return not_found_response(message="Project manager employee not found.")

        branch = get_branch(branch_id=data["branch_id"]) if data.get("branch_id") else None
        department = get_department(department_id=data["department_id"]) if data.get("department_id") else None

        try:
            project = services.create_project(
                organization=org,
                owner=owner,
                manager=manager,
                code=data["code"],
                name=data["name"],
                description=data.get("description", ""),
                project_type=data.get("project_type", "INTERNAL"),
                category=data.get("category", "SOFTWARE"),
                priority=data.get("priority", "MEDIUM"),
                risk_level=data.get("risk_level", "LOW"),
                visibility=data.get("visibility", "ORGANIZATION"),
                start_date=data.get("start_date"),
                end_date=data.get("end_date"),
                estimated_budget=data.get("estimated_budget", 0.0),
                estimated_hours=data.get("estimated_hours", 0.0),
                branch=branch,
                department=department,
                user_id=str(request.user.id),
            )
            return created_response(
                message="Project created successfully.",
                data=ProjectSerializer(project).data,
            )
        except Exception as e:
            return validation_error_response(errors={"project": str(e)}, message="Project creation failed.")


@extend_schema_view(
    get=extend_schema(
        tags=["Project Management"],
        summary="Get Project Detail",
        description="Retrieve full details for a specific project.",
    ),
)
class ProjectDetailAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, pk):
        project = selectors.get_project(project_id=pk)
        if not project:
            return not_found_response(message="Project not found.")

        return success_response(
            message="Project detail retrieved.",
            data=ProjectSerializer(project).data,
        )


@extend_schema(
    tags=["Project Lifecycle"],
    summary="Activate Project",
    description="Transition project lifecycle status to IN_PROGRESS.",
)
class ProjectActivateAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, pk):
        project = selectors.get_project(project_id=pk)
        if not project:
            return not_found_response(message="Project not found.")

        try:
            activated = services.activate_project(project=project, user_id=str(request.user.id))
            return success_response(
                message="Project activated successfully.",
                data=ProjectSerializer(activated).data,
            )
        except Exception as e:
            return validation_error_response(errors={"lifecycle": str(e)}, message="Project activation failed.")


@extend_schema(
    tags=["Project Lifecycle"],
    summary="Pause Project",
    description="Transition active project lifecycle status to ON_HOLD.",
)
class ProjectPauseAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, pk):
        project = selectors.get_project(project_id=pk)
        if not project:
            return not_found_response(message="Project not found.")

        serializer = ProjectStatusActionSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        try:
            paused = services.pause_project(
                project=project,
                reason=serializer.validated_data.get("reason", ""),
                user_id=str(request.user.id),
            )
            return success_response(
                message="Project paused successfully.",
                data=ProjectSerializer(paused).data,
            )
        except Exception as e:
            return validation_error_response(errors={"lifecycle": str(e)}, message="Project pause failed.")


@extend_schema(
    tags=["Project Lifecycle"],
    summary="Resume Project",
    description="Resume paused project back to IN_PROGRESS.",
)
class ProjectResumeAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, pk):
        project = selectors.get_project(project_id=pk)
        if not project:
            return not_found_response(message="Project not found.")

        try:
            resumed = services.resume_project(project=project, user_id=str(request.user.id))
            return success_response(
                message="Project resumed successfully.",
                data=ProjectSerializer(resumed).data,
            )
        except Exception as e:
            return validation_error_response(errors={"lifecycle": str(e)}, message="Project resume failed.")


@extend_schema(
    tags=["Project Lifecycle"],
    summary="Complete Project",
    description="Transition project lifecycle status to COMPLETED.",
)
class ProjectCompleteAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, pk):
        project = selectors.get_project(project_id=pk)
        if not project:
            return not_found_response(message="Project not found.")

        try:
            completed = services.complete_project(project=project, user_id=str(request.user.id))
            return success_response(
                message="Project marked as completed successfully.",
                data=ProjectSerializer(completed).data,
            )
        except Exception as e:
            return validation_error_response(errors={"lifecycle": str(e)}, message="Project completion failed.")


@extend_schema(
    tags=["Project Lifecycle"],
    summary="Archive Project",
    description="Archive project record.",
)
class ProjectArchiveAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, pk):
        project = selectors.get_project(project_id=pk)
        if not project:
            return not_found_response(message="Project not found.")

        try:
            archived = services.archive_project(project=project, user_id=str(request.user.id))
            return success_response(
                message="Project archived successfully.",
                data=ProjectSerializer(archived).data,
            )
        except Exception as e:
            return validation_error_response(errors={"lifecycle": str(e)}, message="Project archiving failed.")


@extend_schema_view(
    get=extend_schema(
        tags=["Project Members"],
        summary="List Project Members",
        description="Retrieve active members assigned to a project.",
    ),
    post=extend_schema(
        tags=["Project Members"],
        summary="Add Project Member",
        description="Assign an employee as a project member with specified role and allocated hours.",
    ),
)
class ProjectMemberListAddAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, pk):
        project = selectors.get_project(project_id=pk)
        if not project:
            return not_found_response(message="Project not found.")

        members = selectors.list_project_members(project_id=pk)
        return success_response(
            message="Project members retrieved.",
            data=ProjectMemberSerializer(members, many=True).data,
        )

    def post(self, request, pk):
        project = selectors.get_project(project_id=pk)
        if not project:
            return not_found_response(message="Project not found.")

        serializer = ProjectMemberAddSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        employee = get_employee(employee_id=data["employee_id"])
        if not employee:
            return not_found_response(message="Employee not found.")

        try:
            member = services.add_project_member(
                project=project,
                employee=employee,
                role=data.get("role", "DEVELOPER"),
                allocated_hours_per_week=data.get("allocated_hours_per_week", 40.0),
                user_id=str(request.user.id),
            )
            return created_response(
                message="Project member added successfully.",
                data=ProjectMemberSerializer(member).data,
            )
        except Exception as e:
            return validation_error_response(errors={"member": str(e)}, message="Adding project member failed.")


@extend_schema_view(
    get=extend_schema(
        tags=["Project Settings"],
        summary="Get Project Settings",
        description="Retrieve configuration settings for a project.",
    ),
    put=extend_schema(
        tags=["Project Settings"],
        summary="Update Project Settings",
        description="Update project working days, timezone, and calendar configuration settings.",
    ),
)
class ProjectSettingsAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, pk):
        project = selectors.get_project(project_id=pk)
        if not project:
            return not_found_response(message="Project not found.")

        return success_response(
            message="Project settings retrieved.",
            data=project.settings_json or {},
        )

    def put(self, request, pk):
        project = selectors.get_project(project_id=pk)
        if not project:
            return not_found_response(message="Project not found.")

        serializer = ProjectSettingsUpdateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        try:
            updated_proj = services.update_project_settings(
                project=project,
                settings_dict=serializer.validated_data["settings"],
                user_id=str(request.user.id),
            )
            return success_response(
                message="Project settings updated successfully.",
                data=updated_proj.settings_json,
            )
        except Exception as e:
            return validation_error_response(errors={"settings": str(e)}, message="Project settings update failed.")


# ── Enterprise Task & WBS Views ────────────────────────────────────────────


@extend_schema_view(
    get=extend_schema(
        tags=["Task Management"],
        summary="List Project Tasks",
        description="Retrieve tasks for a project with optional status, task_type, assignee, or search filtering.",
    ),
    post=extend_schema(
        tags=["Task Management"],
        summary="Create Task / WBS Subtask",
        description="Create a new task, user story, bug, or subtask and automatically compute WBS code.",
    ),
)
class TaskListCreateAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        project_id = request.query_params.get("project_id")
        if not project_id:
            return validation_error_response(message="project_id query parameter is required.")

        status = request.query_params.get("status", "")
        task_type = request.query_params.get("task_type", "")
        assignee_id = request.query_params.get("assignee_id", "")
        search = request.query_params.get("search", "")

        tasks = selectors.list_project_tasks(
            project_id=project_id,
            status=status,
            task_type=task_type,
            assignee_id=assignee_id,
            search=search,
        )
        return success_response(
            message="Tasks retrieved successfully.",
            data=TaskSerializer(tasks, many=True).data,
        )

    def post(self, request):
        serializer = TaskCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        project = selectors.get_project(project_id=data["project_id"])
        if not project:
            return not_found_response(message="Project not found.")

        reporter = get_employee(employee_id=data["reporter_id"])
        if not reporter:
            return not_found_response(message="Reporter employee not found.")

        parent = selectors.get_task(task_id=data["parent_id"]) if data.get("parent_id") else None
        epic = selectors.get_task(task_id=data["epic_id"]) if data.get("epic_id") else None
        assignee = get_employee(employee_id=data["assignee_id"]) if data.get("assignee_id") else None

        try:
            task = services.create_task(
                project=project,
                reporter=reporter,
                code=data["code"],
                title=data["title"],
                description=data.get("description", ""),
                task_type=data.get("task_type", "TASK"),
                priority=data.get("priority", "MEDIUM"),
                severity=data.get("severity", "MINOR"),
                parent=parent,
                epic=epic,
                assignee=assignee,
                story_points=data.get("story_points", 0.0),
                estimated_hours=data.get("estimated_hours", 0.0),
                start_date=data.get("start_date"),
                due_date=data.get("due_date"),
                user_id=str(request.user.id),
            )
            return created_response(
                message="Task created successfully.",
                data=TaskSerializer(task).data,
            )
        except Exception as e:
            return validation_error_response(errors={"task": str(e)}, message="Task creation failed.")


@extend_schema_view(
    get=extend_schema(
        tags=["Task Management"],
        summary="Get Task Detail",
        description="Retrieve detailed specification of a task.",
    ),
    put=extend_schema(
        tags=["Task Management"],
        summary="Update Task Status",
        description="Update task execution status (TODO, IN_PROGRESS, BLOCKED, DONE).",
    ),
)
class TaskDetailAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, pk):
        task = selectors.get_task(task_id=pk)
        if not task:
            return not_found_response(message="Task not found.")

        return success_response(
            message="Task detail retrieved.",
            data=TaskSerializer(task).data,
        )

    def put(self, request, pk):
        task = selectors.get_task(task_id=pk)
        if not task:
            return not_found_response(message="Task not found.")

        serializer = TaskStatusUpdateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        try:
            updated = services.update_task_status(
                task=task,
                status=serializer.validated_data["status"],
                block_reason=serializer.validated_data.get("block_reason", ""),
                user_id=str(request.user.id),
            )
            return success_response(
                message="Task status updated successfully.",
                data=TaskSerializer(updated).data,
            )
        except Exception as e:
            return validation_error_response(errors={"task": str(e)}, message="Task status update failed.")


@extend_schema(
    tags=["Work Breakdown Structure"],
    summary="Get Project WBS Tree",
    description="Generate hierarchical Work Breakdown Structure (WBS) tree for a project.",
)
class WBSTreeAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        project_id = request.query_params.get("project_id")
        if not project_id:
            return validation_error_response(message="project_id query parameter is required.")

        tree = selectors.get_wbs_tree(project_id=project_id)
        return success_response(message="WBS tree generated successfully.", data=tree)


@extend_schema_view(
    get=extend_schema(
        tags=["Task Dependencies"],
        summary="List Task Dependencies",
        description="List predecessor dependencies for a task.",
    ),
    post=extend_schema(
        tags=["Task Dependencies"],
        summary="Add Task Dependency",
        description="Link source predecessor task to target task with circular dependency validation.",
    ),
)
class TaskDependencyListCreateAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        task_id = request.query_params.get("task_id")
        if not task_id:
            return validation_error_response(message="task_id query parameter is required.")

        deps = selectors.list_task_dependencies(task_id=task_id)
        return success_response(
            message="Task dependencies retrieved.",
            data=TaskDependencySerializer(deps, many=True).data,
        )

    def post(self, request):
        serializer = TaskDependencyCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        source_task = selectors.get_task(task_id=data["source_task_id"])
        if not source_task:
            return not_found_response(message="Source predecessor task not found.")

        target_task = selectors.get_task(task_id=data["target_task_id"])
        if not target_task:
            return not_found_response(message="Target successor task not found.")

        try:
            dep = services.add_task_dependency(
                source_task=source_task,
                target_task=target_task,
                dependency_type=data.get("dependency_type", "FINISH_TO_START"),
                user_id=str(request.user.id),
            )
            return created_response(
                message="Task dependency added successfully.",
                data=TaskDependencySerializer(dep).data,
            )
        except Exception as e:
            return validation_error_response(errors={"dependency": str(e)}, message="Task dependency creation failed.")


@extend_schema_view(
    get=extend_schema(
        tags=["Task Checklists"],
        summary="List Task Checklists",
        description="Retrieve checklist items for a task.",
    ),
    post=extend_schema(
        tags=["Task Checklists"],
        summary="Add Task Checklist Item",
        description="Add a checklist item to a task.",
    ),
)
class TaskChecklistListCreateAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, task_id):
        task = selectors.get_task(task_id=task_id)
        if not task:
            return not_found_response(message="Task not found.")

        items = task.checklists.all().order_by("created_at")
        return success_response(
            message="Task checklist items retrieved.",
            data=TaskChecklistSerializer(items, many=True).data,
        )

    def post(self, request, task_id):
        task = selectors.get_task(task_id=task_id)
        if not task:
            return not_found_response(message="Task not found.")

        serializer = TaskChecklistCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        try:
            item = services.add_checklist_item(task=task, title=serializer.validated_data["title"])
            return created_response(
                message="Checklist item added successfully.",
                data=TaskChecklistSerializer(item).data,
            )
        except Exception as e:
            return validation_error_response(errors={"checklist": str(e)}, message="Checklist item addition failed.")


@extend_schema_view(
    get=extend_schema(
        tags=["Task Comments"],
        summary="List Task Comments",
        description="Retrieve threaded comments for a task.",
    ),
    post=extend_schema(
        tags=["Task Comments"],
        summary="Add Task Comment",
        description="Post a threaded comment or internal note on a task.",
    ),
)
class TaskCommentListCreateAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, task_id):
        task = selectors.get_task(task_id=task_id)
        if not task:
            return not_found_response(message="Task not found.")

        comments = selectors.list_task_comments(task_id=task_id)
        return success_response(
            message="Task comments retrieved.",
            data=TaskCommentSerializer(comments, many=True).data,
        )

    def post(self, request, task_id):
        task = selectors.get_task(task_id=task_id)
        if not task:
            return not_found_response(message="Task not found.")

        serializer = TaskCommentCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        parent_comment = selectors.TaskComment.objects.get(id=data["parent_comment_id"]) if data.get("parent_comment_id") else None

        try:
            comment = services.add_task_comment(
                task=task,
                author_user_id=str(request.user.id),
                author_name=getattr(request.user, "display_name", str(request.user)),
                content=data["content"],
                parent_comment=parent_comment,
                is_internal_note=data.get("is_internal_note", False),
            )
            return created_response(
                message="Task comment posted successfully.",
                data=TaskCommentSerializer(comment).data,
            )
        except Exception as e:
            return validation_error_response(errors={"comment": str(e)}, message="Posting task comment failed.")


@extend_schema(
    tags=["Task Activity Timeline"],
    summary="Get Task Activity Timeline",
    description="Retrieve immutable activity timeline entries for a task.",
)
class TaskActivityTimelineAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, task_id):
        task = selectors.get_task(task_id=task_id)
        if not task:
            return not_found_response(message="Task not found.")

        logs = selectors.get_task_activity_logs(task_id=task_id)
        return success_response(
            message="Task activity timeline retrieved.",
            data=TaskActivityLogSerializer(logs, many=True).data,
        )


# ── Enterprise Agile Delivery, Sprint & Kanban Views ───────────────────────


@extend_schema_view(
    get=extend_schema(
        tags=["Sprint Engine"],
        summary="List Project Sprints",
        description="Retrieve sprints for a project.",
    ),
    post=extend_schema(
        tags=["Sprint Engine"],
        summary="Create Sprint",
        description="Create a new Sprint or Iteration container.",
    ),
)
class SprintListCreateAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        project_id = request.query_params.get("project_id")
        if not project_id:
            return validation_error_response(message="project_id query parameter is required.")

        status = request.query_params.get("status", "")
        sprints = selectors.list_project_sprints(project_id=project_id, status=status)
        return success_response(
            message="Sprints retrieved successfully.",
            data=SprintSerializer(sprints, many=True).data,
        )

    def post(self, request):
        serializer = SprintCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        project = selectors.get_project(project_id=data["project_id"])
        if not project:
            return not_found_response(message="Project not found.")

        owner = get_employee(employee_id=data["owner_id"])
        if not owner:
            return not_found_response(message="Sprint owner employee not found.")

        try:
            sprint = services.create_sprint(
                project=project,
                owner=owner,
                name=data["name"],
                start_date=data["start_date"],
                end_date=data["end_date"],
                goal=data.get("goal", ""),
                sprint_type=data.get("sprint_type", "REGULAR"),
                capacity_hours=data.get("capacity_hours", 0.0),
                user_id=str(request.user.id),
            )
            return created_response(
                message="Sprint created successfully.",
                data=SprintSerializer(sprint).data,
            )
        except Exception as e:
            return validation_error_response(errors={"sprint": str(e)}, message="Sprint creation failed.")


@extend_schema_view(
    get=extend_schema(
        tags=["Sprint Engine"],
        summary="Get Sprint Detail",
        description="Retrieve detailed specification of a sprint.",
    ),
)
class SprintDetailAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, pk):
        sprint = selectors.get_sprint(sprint_id=pk)
        if not sprint:
            return not_found_response(message="Sprint not found.")

        return success_response(
            message="Sprint detail retrieved.",
            data=SprintSerializer(sprint).data,
        )


@extend_schema(
    tags=["Sprint Engine"],
    summary="Start Sprint",
    description="Start a sprint and set status to ACTIVE.",
)
class SprintStartAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, pk):
        sprint = selectors.get_sprint(sprint_id=pk)
        if not sprint:
            return not_found_response(message="Sprint not found.")

        try:
            started = services.start_sprint(sprint=sprint, user_id=str(request.user.id))
            return success_response(
                message="Sprint started successfully.",
                data=SprintSerializer(started).data,
            )
        except Exception as e:
            return validation_error_response(errors={"sprint": str(e)}, message="Starting sprint failed.")


@extend_schema(
    tags=["Sprint Engine"],
    summary="Complete Sprint",
    description="Complete a sprint, calculate final velocity and completed story points.",
)
class SprintCompleteAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, pk):
        sprint = selectors.get_sprint(sprint_id=pk)
        if not sprint:
            return not_found_response(message="Sprint not found.")

        try:
            completed = services.complete_sprint(sprint=sprint, user_id=str(request.user.id))
            return success_response(
                message="Sprint completed successfully.",
                data=SprintSerializer(completed).data,
            )
        except Exception as e:
            return validation_error_response(errors={"sprint": str(e)}, message="Completing sprint failed.")


@extend_schema_view(
    get=extend_schema(
        tags=["Kanban Board"],
        summary="List Kanban Boards",
        description="List Kanban or Scrum boards for a project.",
    ),
    post=extend_schema(
        tags=["Kanban Board"],
        summary="Create Kanban Board",
        description="Create a new visual board and initialize default columns.",
    ),
)
class KanbanBoardListCreateAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        project_id = request.query_params.get("project_id")
        if not project_id:
            return validation_error_response(message="project_id query parameter is required.")

        boards = selectors.list_project_boards(project_id=project_id)
        return success_response(
            message="Kanban boards retrieved successfully.",
            data=KanbanBoardSerializer(boards, many=True).data,
        )

    def post(self, request):
        serializer = KanbanBoardCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        project = selectors.get_project(project_id=data["project_id"])
        if not project:
            return not_found_response(message="Project not found.")

        try:
            board = services.create_kanban_board(
                project=project,
                name=data["name"],
                board_type=data.get("board_type", "KANBAN"),
                description=data.get("description", ""),
                estimation_scale=data.get("estimation_scale", "FIBONACCI"),
            )
            return created_response(
                message="Kanban board created successfully.",
                data=KanbanBoardSerializer(board).data,
            )
        except Exception as e:
            return validation_error_response(errors={"board": str(e)}, message="Kanban board creation failed.")


@extend_schema_view(
    get=extend_schema(
        tags=["Kanban Board"],
        summary="Get Kanban Board Detail",
        description="Retrieve visual Kanban board detail with columns and tasks.",
    ),
)
class KanbanBoardDetailAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, pk):
        board = selectors.get_board_detail(board_id=pk)
        if not board:
            return not_found_response(message="Kanban board not found.")

        return success_response(
            message="Kanban board detail retrieved.",
            data=KanbanBoardSerializer(board).data,
        )


@extend_schema(
    tags=["Kanban Board"],
    summary="Move Task Card on Board",
    description="Move task card to a new column on a board with WIP limit enforcement.",
)
class TaskMoveOnBoardAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, task_id):
        task = selectors.get_task(task_id=task_id)
        if not task:
            return not_found_response(message="Task not found.")

        serializer = TaskMoveOnBoardSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        try:
            target_column = selectors.BoardColumn.objects.get(id=serializer.validated_data["target_column_id"])
            moved = services.move_task_on_board(task=task, target_column=target_column, user_id=str(request.user.id))
            return success_response(
                message="Task moved on board successfully.",
                data=TaskSerializer(moved).data,
            )
        except Exception as e:
            return validation_error_response(errors={"board_move": str(e)}, message="Moving task on board failed.")


@extend_schema(
    tags=["Agile Velocity & Burndown"],
    summary="Get Sprint Velocity Report",
    description="Calculate average sprint velocity and trend history for a project.",
)
class SprintVelocityReportAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        project_id = request.query_params.get("project_id")
        if not project_id:
            return validation_error_response(message="project_id query parameter is required.")

        velocity_data = selectors.calculate_sprint_velocity(project_id=project_id)
        return success_response(
            message="Sprint velocity report calculated.",
            data=velocity_data,
        )


@extend_schema(
    tags=["Agile Velocity & Burndown"],
    summary="Get Sprint Burndown Dataset",
    description="Prepare burndown chart dataset foundation for a sprint.",
)
class SprintBurndownReportAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, sprint_id):
        burndown_data = selectors.get_burndown_dataset(sprint_id=sprint_id)
        if not burndown_data:
            return not_found_response(message="Sprint not found.")

        return success_response(
            message="Sprint burndown dataset retrieved.",
            data=burndown_data,
        )


@extend_schema_view(
    get=extend_schema(
        tags=["Release Planning"],
        summary="List Project Releases",
        description="Retrieve release milestones for a project.",
    ),
    post=extend_schema(
        tags=["Release Planning"],
        summary="Create Release Milestone",
        description="Create a version release milestone.",
    ),
)
class ReleaseListCreateAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        project_id = request.query_params.get("project_id")
        if not project_id:
            return validation_error_response(message="project_id query parameter is required.")

        releases = selectors.Release.objects.filter(project_id=project_id).order_by("-created_at")
        return success_response(
            message="Releases retrieved successfully.",
            data=ReleaseSerializer(releases, many=True).data,
        )

    def post(self, request):
        serializer = ReleaseCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        project = selectors.get_project(project_id=data["project_id"])
        if not project:
            return not_found_response(message="Project not found.")

        try:
            rel = services.create_release(
                project=project,
                name=data["name"],
                version=data["version"],
                description=data.get("description", ""),
                target_date=data.get("target_date"),
            )
            return created_response(
                message="Release created successfully.",
                data=ReleaseSerializer(rel).data,
            )
        except Exception as e:
            return validation_error_response(errors={"release": str(e)}, message="Release creation failed.")


# ── Enterprise Time Tracking, Timesheet & Worklog Views ───────────────────


@extend_schema(
    tags=["Time Tracking"],
    summary="Start Live Timer",
    description="Start live timer on a task. Enforces single running timer rule.",
)
class TimerStartAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        serializer = TimerStartSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        employee = Employee.objects.filter(user=request.user).first()
        if not employee:
            return not_found_response(message="Employee profile for logged-in user not found.")

        task = selectors.get_task(task_id=data["task_id"])
        if not task:
            return not_found_response(message="Task not found.")

        try:
            entry = services.start_timer(
                employee=employee,
                task=task,
                notes=data.get("notes", ""),
                billable_type=data.get("billable_type", "BILLABLE"),
            )
            return created_response(
                message="Live timer started successfully.",
                data=TimeEntrySerializer(entry).data,
            )
        except Exception as e:
            return validation_error_response(errors={"timer": str(e)}, message="Starting timer failed.")


@extend_schema(
    tags=["Time Tracking"],
    summary="Stop Live Timer",
    description="Stop active running timer and calculate elapsed worklog effort.",
)
class TimerStopAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        employee = Employee.objects.filter(user=request.user).first()
        if not employee:
            return not_found_response(message="Employee profile for logged-in user not found.")

        active_entry = selectors.get_active_timer(employee_id=employee.id)
        if not active_entry:
            return not_found_response(message="No active running timer found for employee.")

        try:
            stopped = services.stop_timer(entry=active_entry)
            return success_response(
                message="Live timer stopped successfully.",
                data=TimeEntrySerializer(stopped).data,
            )
        except Exception as e:
            return validation_error_response(errors={"timer": str(e)}, message="Stopping timer failed.")


@extend_schema_view(
    get=extend_schema(
        tags=["Time Tracking"],
        summary="List Worklogs / Time Entries",
        description="List time entries for an employee with optional date range or project filter.",
    ),
    post=extend_schema(
        tags=["Time Tracking"],
        summary="Create Manual Worklog",
        description="Log manual worklog hours on a task with 24h daily limit validation.",
    ),
)
class TimeEntryListCreateAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        employee_id = request.query_params.get("employee_id")
        if not employee_id:
            employee = Employee.objects.filter(user=request.user).first()
            if not employee:
                return validation_error_response(message="employee_id query parameter is required.")
            employee_id = str(employee.id)

        entries = selectors.list_employee_time_entries(
            employee_id=employee_id,
            project_id=request.query_params.get("project_id", ""),
        )
        return success_response(
            message="Time entries retrieved successfully.",
            data=TimeEntrySerializer(entries, many=True).data,
        )

    def post(self, request):
        serializer = TimeEntryCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        employee = get_employee(employee_id=data["employee_id"])
        if not employee:
            return not_found_response(message="Employee not found.")

        task = selectors.get_task(task_id=data["task_id"])
        if not task:
            return not_found_response(message="Task not found.")

        try:
            entry = services.create_manual_worklog(
                employee=employee,
                task=task,
                date_val=data["date"],
                hours=data["hours"],
                notes=data.get("notes", ""),
                billable_type=data.get("billable_type", "BILLABLE"),
            )
            return created_response(
                message="Manual worklog created successfully.",
                data=TimeEntrySerializer(entry).data,
            )
        except Exception as e:
            return validation_error_response(errors={"worklog": str(e)}, message="Worklog creation failed.")


@extend_schema_view(
    get=extend_schema(
        tags=["Timesheet Management"],
        summary="List Timesheets",
        description="Retrieve timesheet submissions for employee or manager review.",
    ),
    post=extend_schema(
        tags=["Timesheet Management"],
        summary="Submit Timesheet",
        description="Submit timesheet for manager approval.",
    ),
)
class TimesheetListCreateAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        timesheets = selectors.list_timesheets(
            employee_id=request.query_params.get("employee_id", ""),
            project_id=request.query_params.get("project_id", ""),
            status=request.query_params.get("status", ""),
        )
        return success_response(
            message="Timesheets retrieved successfully.",
            data=TimesheetSerializer(timesheets, many=True).data,
        )

    def post(self, request):
        serializer = TimesheetSubmitSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        employee = get_employee(employee_id=data["employee_id"])
        if not employee:
            return not_found_response(message="Employee not found.")

        project = selectors.get_project(project_id=data["project_id"]) if data.get("project_id") else None

        try:
            timesheet = services.submit_timesheet(
                employee=employee,
                period_type=data.get("period_type", "WEEKLY"),
                start_date=data["start_date"],
                end_date=data["end_date"],
                project=project,
                user_id=str(request.user.id),
            )
            return created_response(
                message="Timesheet submitted for approval.",
                data=TimesheetSerializer(timesheet).data,
            )
        except Exception as e:
            return validation_error_response(errors={"timesheet": str(e)}, message="Timesheet submission failed.")


@extend_schema(
    tags=["Timesheet Management"],
    summary="Approve Timesheet",
    description="Approve timesheet and lock associated worklog entries.",
)
class TimesheetApproveAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, pk):
        timesheet = selectors.get_timesheet_detail(timesheet_id=pk)
        if not timesheet:
            return not_found_response(message="Timesheet not found.")

        serializer = TimesheetApprovalActionSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        approver = get_employee(employee_id=serializer.validated_data["approver_id"])
        if not approver:
            return not_found_response(message="Approver employee not found.")

        try:
            approved = services.approve_timesheet(timesheet=timesheet, approver=approver, user_id=str(request.user.id))
            return success_response(
                message="Timesheet approved successfully.",
                data=TimesheetSerializer(approved).data,
            )
        except Exception as e:
            return validation_error_response(errors={"timesheet": str(e)}, message="Approving timesheet failed.")


@extend_schema(
    tags=["Timesheet Management"],
    summary="Reject Timesheet",
    description="Reject timesheet with comments.",
)
class TimesheetRejectAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, pk):
        timesheet = selectors.get_timesheet_detail(timesheet_id=pk)
        if not timesheet:
            return not_found_response(message="Timesheet not found.")

        serializer = TimesheetApprovalActionSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        approver = get_employee(employee_id=serializer.validated_data["approver_id"])
        if not approver:
            return not_found_response(message="Approver employee not found.")

        try:
            rejected = services.reject_timesheet(
                timesheet=timesheet,
                approver=approver,
                reason=serializer.validated_data.get("comments", "Timesheet rejected."),
                user_id=str(request.user.id),
            )
            return success_response(
                message="Timesheet rejected.",
                data=TimesheetSerializer(rejected).data,
            )
        except Exception as e:
            return validation_error_response(errors={"timesheet": str(e)}, message="Rejecting timesheet failed.")


@extend_schema(
    tags=["Productivity Metrics"],
    summary="Get Employee Productivity Metrics",
    description="Calculate billable vs non-billable utilization rates and total effort hours.",
)
class ProductivityMetricsAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        employee_id = request.query_params.get("employee_id")
        start_date_str = request.query_params.get("start_date")
        end_date_str = request.query_params.get("end_date")

        if not employee_id or not start_date_str or not end_date_str:
            return validation_error_response(message="employee_id, start_date, and end_date query parameters are required.")

        try:
            from datetime import datetime
            start_date = datetime.strptime(start_date_str, "%Y-%m-%d").date()
            end_date = datetime.strptime(end_date_str, "%Y-%m-%d").date()
            metrics = selectors.calculate_employee_productivity(employee_id=employee_id, start_date=start_date, end_date=end_date)
            return success_response(
                message="Productivity metrics calculated.",
                data=metrics,
            )
        except Exception as e:
            return validation_error_response(errors={"productivity": str(e)}, message="Productivity calculation failed.")


# ── Enterprise Resource Planning, Capacity & Workload Views ───────────────


@extend_schema_view(
    get=extend_schema(
        tags=["Resource Planning"],
        summary="List Resource Allocations",
        description="Retrieve resource allocations for an employee or project.",
    ),
    post=extend_schema(
        tags=["Resource Planning"],
        summary="Create Resource Allocation",
        description="Allocate employee to project with overallocation validation.",
    ),
)
class ResourceAllocationListCreateAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        employee_id = request.query_params.get("employee_id")
        project_id = request.query_params.get("project_id")

        if project_id:
            allocations = selectors.list_project_allocations(project_id=project_id)
        elif employee_id:
            allocations = selectors.list_employee_allocations(employee_id=employee_id)
        else:
            return validation_error_response(message="Either employee_id or project_id query parameter is required.")

        return success_response(
            message="Resource allocations retrieved successfully.",
            data=ResourceAllocationSerializer(allocations, many=True).data,
        )

    def post(self, request):
        serializer = ResourceAllocationCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        employee = get_employee(employee_id=data["employee_id"])
        if not employee:
            return not_found_response(message="Employee not found.")

        project = selectors.get_project(project_id=data["project_id"])
        if not project:
            return not_found_response(message="Project not found.")

        task = selectors.get_task(task_id=data["task_id"]) if data.get("task_id") else None

        try:
            allocation = services.allocate_resource(
                employee=employee,
                project=project,
                task=task,
                start_date=data["start_date"],
                end_date=data["end_date"],
                allocation_percentage=data.get("allocation_percentage", 100.0),
                allocation_type=data.get("allocation_type", "PROJECT"),
                notes=data.get("notes", ""),
            )
            return created_response(
                message="Resource allocated successfully.",
                data=ResourceAllocationSerializer(allocation).data,
            )
        except Exception as e:
            return validation_error_response(errors={"allocation": str(e)}, message="Resource allocation failed.")


@extend_schema(
    tags=["Resource Planning"],
    summary="Get Employee Capacity & Utilization",
    description="Calculate employee planned vs allocated capacity and workload status.",
)
class ResourceCapacityAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        employee_id = request.query_params.get("employee_id")
        start_date_str = request.query_params.get("start_date")
        end_date_str = request.query_params.get("end_date")

        if not employee_id or not start_date_str or not end_date_str:
            return validation_error_response(message="employee_id, start_date, and end_date query parameters are required.")

        try:
            from datetime import datetime
            start_date = datetime.strptime(start_date_str, "%Y-%m-%d").date()
            end_date = datetime.strptime(end_date_str, "%Y-%m-%d").date()
            cap = selectors.calculate_employee_capacity(employee_id=employee_id, start_date=start_date, end_date=end_date)
            return success_response(
                message="Resource capacity calculated.",
                data=cap,
            )
        except Exception as e:
            return validation_error_response(errors={"capacity": str(e)}, message="Capacity calculation failed.")


@extend_schema(
    tags=["Resource Planning"],
    summary="List Bench Resources",
    description="List underutilized resources (< 50% capacity) available on the bench.",
)
class BenchManagementAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        organization_id = request.query_params.get("organization_id")
        if not organization_id:
            employee = Employee.objects.filter(user=request.user).first()
            if not employee:
                return validation_error_response(message="organization_id query parameter is required.")
            organization_id = str(employee.organization_id)

        bench = selectors.list_bench_resources(organization_id=organization_id)
        return success_response(
            message="Bench resources retrieved.",
            data=bench,
        )


@extend_schema(
    tags=["Resource Planning"],
    summary="Skill-Based Candidate Match",
    description="Match candidate employees against project skill requirements.",
)
class ResourceSkillMatchAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        project_id = request.query_params.get("project_id")
        if not project_id:
            return validation_error_response(message="project_id query parameter is required.")

        matches = selectors.match_resources_by_skill(project_id=project_id)
        return success_response(
            message="Skill-based candidate matches generated.",
            data=matches,
        )


# ── Enterprise Portfolio Management, Program & PMO Views ─────────────────


@extend_schema_view(
    get=extend_schema(
        tags=["Portfolio Management"],
        summary="List Portfolios",
        description="Retrieve strategic portfolios for an organization.",
    ),
    post=extend_schema(
        tags=["Portfolio Management"],
        summary="Create Portfolio",
        description="Create a new strategic portfolio container.",
    ),
)
class PortfolioListCreateAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        organization_id = request.query_params.get("organization_id")
        if not organization_id:
            employee = Employee.objects.filter(user=request.user).first()
            if not employee:
                return validation_error_response(message="organization_id query parameter is required.")
            organization_id = str(employee.organization_id)

        portfolios = selectors.list_portfolios(organization_id=organization_id)
        return success_response(
            message="Portfolios retrieved successfully.",
            data=PortfolioSerializer(portfolios, many=True).data,
        )

    def post(self, request):
        serializer = PortfolioCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        org = get_organization(organization_id=data["organization_id"])
        if not org:
            return not_found_response(message="Organization not found.")

        owner = get_employee(employee_id=data["owner_id"])
        if not owner:
            return not_found_response(message="Portfolio owner employee not found.")

        sponsor = get_employee(employee_id=data["executive_sponsor_id"]) if data.get("executive_sponsor_id") else None

        try:
            portfolio = services.create_portfolio(
                organization=org,
                owner=owner,
                executive_sponsor=sponsor,
                code=data["code"],
                name=data["name"],
                portfolio_type=data.get("portfolio_type", "STRATEGIC"),
                description=data.get("description", ""),
                budget=data.get("budget", 0.0),
                priority=data.get("priority", 1),
            )
            return created_response(
                message="Portfolio created successfully.",
                data=PortfolioSerializer(portfolio).data,
            )
        except Exception as e:
            return validation_error_response(errors={"portfolio": str(e)}, message="Portfolio creation failed.")


@extend_schema_view(
    get=extend_schema(
        tags=["Program Management"],
        summary="List Programs",
        description="Retrieve cross-functional programs for an organization.",
    ),
    post=extend_schema(
        tags=["Program Management"],
        summary="Create Program",
        description="Create a new program container.",
    ),
)
class ProgramListCreateAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        organization_id = request.query_params.get("organization_id")
        if not organization_id:
            employee = Employee.objects.filter(user=request.user).first()
            if not employee:
                return validation_error_response(message="organization_id query parameter is required.")
            organization_id = str(employee.organization_id)

        programs = selectors.list_programs(organization_id=organization_id)
        return success_response(
            message="Programs retrieved successfully.",
            data=ProgramSerializer(programs, many=True).data,
        )

    def post(self, request):
        serializer = ProgramCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        org = get_organization(organization_id=data["organization_id"])
        if not org:
            return not_found_response(message="Organization not found.")

        manager = get_employee(employee_id=data["program_manager_id"])
        if not manager:
            return not_found_response(message="Program manager employee not found.")

        portfolio = selectors.get_portfolio(portfolio_id=data["portfolio_id"]) if data.get("portfolio_id") else None

        try:
            program = services.create_program(
                organization=org,
                program_manager=manager,
                portfolio=portfolio,
                code=data["code"],
                name=data["name"],
                description=data.get("description", ""),
                budget=data.get("budget", 0.0),
                target_start_date=data.get("target_start_date"),
                target_end_date=data.get("target_end_date"),
            )
            return created_response(
                message="Program created successfully.",
                data=ProgramSerializer(program).data,
            )
        except Exception as e:
            return validation_error_response(errors={"program": str(e)}, message="Program creation failed.")


@extend_schema(
    tags=["Executive Dashboards"],
    summary="Get Executive Dashboard Analytics",
    description="Retrieve high-level PMO and C-level executive dashboard metrics.",
)
class ExecutiveDashboardAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        dashboard_type = request.query_params.get("dashboard_type", "CEO")
        employee = Employee.objects.filter(user=request.user).first()
        if not employee:
            return validation_error_response(message="Logged in employee context not found.")

        metrics = selectors.get_executive_dashboard_metrics(
            organization_id=employee.organization_id,
            dashboard_type=dashboard_type,
        )
        return success_response(
            message="Executive dashboard metrics retrieved.",
            data=metrics,
        )


@extend_schema(
    tags=["Project PMO"],
    summary="Get Project RAG Health Score",
    description="Calculate automated Schedule, Resource, Risk, and Overall RAG health status.",
)
class ProjectHealthScoreAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, pk):
        health = selectors.calculate_project_health_score(project_id=pk)
        return success_response(
            message="Project health score calculated.",
            data=health,
        )





