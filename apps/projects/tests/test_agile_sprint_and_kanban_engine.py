"""Unit tests for Enterprise Agile Delivery, Sprint & Kanban Engine."""

from datetime import date, timedelta
from decimal import Decimal
from django.test import TestCase
from rest_framework.test import APIClient

from apps.accounts.services import create_user
from apps.employees.services import create_employee
from apps.organizations.services import (
    create_branch,
    create_department,
    create_designation,
    create_organization,
)

from apps.projects import selectors, services
from apps.projects.enums import SprintStatus, SprintType, TaskStatus
from apps.projects.exceptions import ProjectLifecycleError, ProjectValidationError


class AgileSprintAndKanbanEngineTestCase(TestCase):
    """Test suite for Sprints, Kanban Boards, Columns, WIP Limits, Backlogs, Velocity, and Releases."""

    @classmethod
    def setUpTestData(cls):
        cls.org = create_organization(name="Agile Enterprise Corp")
        cls.branch = create_branch(organization=cls.org, code="AGLMAIN", name="Agile HQ")
        cls.dept = create_department(organization=cls.org, branch=cls.branch, code="AGLENG", name="Engineering Dept")
        cls.desg = create_designation(organization=cls.org, department=cls.dept, code="AGLSENG", name="Scrum Master")

        cls.user = create_user(email="scrummaster@agilecorp.com", password="SecurePassword123!")

        cls.owner = create_employee(
            organization=cls.org,
            branch=cls.branch,
            department=cls.dept,
            designation=cls.desg,
            first_name="Arthur",
            last_name="ScrumMaster",
            official_email="ascrum@agilecorp.com",
            date_of_joining=date(2023, 1, 1),
        )

        cls.manager = create_employee(
            organization=cls.org,
            branch=cls.branch,
            department=cls.dept,
            designation=cls.desg,
            first_name="Alice",
            last_name="Manager",
            official_email="amanager@agilecorp.com",
            date_of_joining=date(2023, 6, 1),
        )

        cls.dev = create_employee(
            organization=cls.org,
            branch=cls.branch,
            department=cls.dept,
            designation=cls.desg,
            first_name="Alex",
            last_name="Developer",
            official_email="adeveloper@agilecorp.com",
            date_of_joining=date(2024, 1, 1),
        )

        cls.project = services.create_project(
            organization=cls.org,
            owner=cls.owner,
            manager=cls.manager,
            code="PRJ-AGL-001",
            name="Agile Delivery Project",
        )
        services.activate_project(project=cls.project)

    def setUp(self):
        self.client = APIClient()
        self.client.force_authenticate(user=self.user)

    def test_sprint_lifecycle_flow(self):
        """Create, start, and complete a sprint, verifying velocity calculations."""
        today = date.today()
        sprint = services.create_sprint(
            project=self.project,
            owner=self.owner,
            name="Sprint 1 - Core Engine",
            start_date=today,
            end_date=today + timedelta(days=14),
            capacity_hours=Decimal("160.00"),
            user_id=str(self.user.id),
        )

        self.assertEqual(sprint.sprint_number, 1)
        self.assertEqual(sprint.status, SprintStatus.DRAFT)

        # Create tasks and assign to sprint
        t1 = services.create_task(project=self.project, reporter=self.owner, code="AGL-1", title="Feature A", story_points=Decimal("5.0"))
        t2 = services.create_task(project=self.project, reporter=self.owner, code="AGL-2", title="Feature B", story_points=Decimal("8.0"))
        services.add_tasks_to_sprint(sprint=sprint, task_ids=[t1.id, t2.id])

        # Start Sprint
        started = services.start_sprint(sprint=sprint, user_id=str(self.user.id))
        self.assertEqual(started.status, SprintStatus.ACTIVE)
        self.assertEqual(started.total_story_points, Decimal("13.0"))

        # Complete task 1
        services.update_task_status(task=t1, status=TaskStatus.DONE)

        # Complete Sprint
        completed = services.complete_sprint(sprint=started, user_id=str(self.user.id))
        self.assertEqual(completed.status, SprintStatus.COMPLETED)
        self.assertEqual(completed.completed_story_points, Decimal("5.0"))
        self.assertEqual(completed.velocity, Decimal("5.0"))

    def test_kanban_board_wip_limit_enforcement(self):
        """Move task card on Kanban board and enforce column WIP limits."""
        board = services.create_kanban_board(
            project=self.project,
            name="Agile Dev Board",
        )
        self.assertEqual(board.columns.count(), 4)

        in_progress_col = board.columns.get(mapped_status=TaskStatus.IN_PROGRESS)
        # Set tight WIP limit of 1
        in_progress_col.wip_limit = 1
        in_progress_col.save()

        t1 = services.create_task(project=self.project, reporter=self.owner, code="AGL-WIP-1", title="Task 1")
        t2 = services.create_task(project=self.project, reporter=self.owner, code="AGL-WIP-2", title="Task 2")

        # Move T1 to In Progress (Allowed)
        services.move_task_on_board(task=t1, target_column=in_progress_col, user_id=str(self.user.id))
        t1.refresh_from_db()
        self.assertEqual(t1.status, TaskStatus.IN_PROGRESS)

        # Move T2 to In Progress (Should fail due to WIP limit)
        with self.assertRaises(ProjectValidationError):
            services.move_task_on_board(task=t2, target_column=in_progress_col, user_id=str(self.user.id))

    def test_sprint_velocity_calculation(self):
        """Calculate project velocity trend across completed sprints."""
        today = date.today()
        sprint1 = services.create_sprint(project=self.project, owner=self.owner, name="S1", start_date=today, end_date=today + timedelta(days=7))
        t1 = services.create_task(project=self.project, reporter=self.owner, code="V-1", title="Task V1", story_points=Decimal("10.0"))
        services.add_tasks_to_sprint(sprint=sprint1, task_ids=[t1.id])
        services.start_sprint(sprint=sprint1)
        services.update_task_status(task=t1, status=TaskStatus.DONE)
        services.complete_sprint(sprint=sprint1)

        velocity_rpt = selectors.calculate_sprint_velocity(project_id=self.project.id)
        self.assertEqual(velocity_rpt["completed_sprints_count"], 1)
        self.assertEqual(Decimal(str(velocity_rpt["average_velocity"])), Decimal("10.0"))

    def test_burndown_dataset_foundation(self):
        """Verify burndown chart dataset calculations."""
        today = date.today()
        sprint = services.create_sprint(project=self.project, owner=self.owner, name="S-Burn", start_date=today, end_date=today + timedelta(days=7))
        t1 = services.create_task(project=self.project, reporter=self.owner, code="B-1", title="Burn Task 1", story_points=Decimal("8.0"))
        services.add_tasks_to_sprint(sprint=sprint, task_ids=[t1.id])

        dataset = selectors.get_burndown_dataset(sprint_id=sprint.id)
        self.assertEqual(dataset["total_story_points"], 8.0)
        self.assertEqual(dataset["remaining_story_points"], 8.0)

    def test_release_planning(self):
        """Create a version release milestone."""
        rel = services.create_release(
            project=self.project,
            name="Version 1.0.0 - General Availability",
            version="v1.0.0",
            target_date=date.today() + timedelta(days=30),
        )
        self.assertEqual(rel.version, "v1.0.0")

    def test_agile_api_views(self):
        """Test REST APIView endpoints for Sprints, Boards, Card Moves, Velocity, and Releases."""
        today = date.today()
        # Create Sprint API
        res_sprint = self.client.post(
            "/api/v1/projects/sprints/",
            {
                "project_id": str(self.project.id),
                "owner_id": str(self.owner.id),
                "name": "API Sprint 1",
                "start_date": today.isoformat(),
                "end_date": (today + timedelta(days=14)).isoformat(),
                "capacity_hours": 80.0,
            },
            format="json",
        )
        self.assertEqual(res_sprint.status_code, 201)
        sprint_id = res_sprint.data["data"]["id"]

        # Start Sprint API
        res_start = self.client.post(f"/api/v1/projects/sprints/{sprint_id}/start/")
        self.assertEqual(res_start.status_code, 200)

        # Create Kanban Board API
        res_board = self.client.post(
            "/api/v1/projects/boards/",
            {
                "project_id": str(self.project.id),
                "name": "API Board",
                "board_type": "KANBAN",
            },
            format="json",
        )
        self.assertEqual(res_board.status_code, 201)
        board_id = res_board.data["data"]["id"]

        # Get Board Detail API
        res_board_detail = self.client.get(f"/api/v1/projects/boards/?project_id={self.project.id}")
        self.assertEqual(res_board_detail.status_code, 200)

        # Velocity API
        res_vel = self.client.get(f"/api/v1/projects/sprints/velocity/?project_id={self.project.id}")
        self.assertEqual(res_vel.status_code, 200)

        # Create Release API
        res_rel = self.client.post(
            "/api/v1/projects/releases/",
            {
                "project_id": str(self.project.id),
                "name": "v1.0 API Release",
                "version": "v1.0.0",
            },
            format="json",
        )
        self.assertEqual(res_rel.status_code, 201)
