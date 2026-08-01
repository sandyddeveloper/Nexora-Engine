"""Unit tests for Enterprise Task, Work Breakdown Structure (WBS) & Work Management Engine."""

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
from apps.projects.enums import DependencyType, ProjectMemberRole, TaskStatus, TaskType
from apps.projects.exceptions import ProjectValidationError


class TaskAndWBSEngineTestCase(TestCase):
    """Test suite for Tasks, Epics, Subtasks, WBS, Dependencies, Checklists, Comments, and Activity Timeline."""

    @classmethod
    def setUpTestData(cls):
        cls.org = create_organization(name="WBS Enterprise Corp")
        cls.branch = create_branch(organization=cls.org, code="WBSMAIN", name="WBS HQ")
        cls.dept = create_department(organization=cls.org, branch=cls.branch, code="WBSENG", name="Engineering Dept")
        cls.desg = create_designation(organization=cls.org, department=cls.dept, code="WBSSENG", name="Senior Engineer")

        cls.user = create_user(email="wbsadmin@wbscorp.com", password="SecurePassword123!")

        cls.owner = create_employee(
            organization=cls.org,
            branch=cls.branch,
            department=cls.dept,
            designation=cls.desg,
            first_name="William",
            last_name="Owner",
            official_email="wowner@wbscorp.com",
            date_of_joining=date(2023, 1, 1),
        )

        cls.manager = create_employee(
            organization=cls.org,
            branch=cls.branch,
            department=cls.dept,
            designation=cls.desg,
            first_name="Wendy",
            last_name="Manager",
            official_email="wmanager@wbscorp.com",
            date_of_joining=date(2023, 6, 1),
        )

        cls.dev = create_employee(
            organization=cls.org,
            branch=cls.branch,
            department=cls.dept,
            designation=cls.desg,
            first_name="Wade",
            last_name="Developer",
            official_email="wdeveloper@wbscorp.com",
            date_of_joining=date(2024, 1, 1),
        )

        cls.project = services.create_project(
            organization=cls.org,
            owner=cls.owner,
            manager=cls.manager,
            code="PRJ-WBS-001",
            name="WBS Delivery Project",
        )
        services.activate_project(project=cls.project)

    def setUp(self):
        self.client = APIClient()
        self.client.force_authenticate(user=self.user)

    def test_create_task_and_subtasks_wbs_numbering(self):
        """Create parent task and child subtasks and verify automated WBS numbering."""
        parent_task = services.create_task(
            project=self.project,
            reporter=self.owner,
            code="TASK-WBS-100",
            title="Parent Architecture Task",
            task_type=TaskType.EPIC,
            user_id=str(self.user.id),
        )
        self.assertEqual(parent_task.wbs_code, "1")

        child_1 = services.create_task(
            project=self.project,
            reporter=self.owner,
            code="TASK-WBS-101",
            title="Child Module Design",
            parent=parent_task,
            user_id=str(self.user.id),
        )
        self.assertEqual(child_1.wbs_code, "1.1")

        child_2 = services.create_task(
            project=self.project,
            reporter=self.owner,
            code="TASK-WBS-102",
            title="Child Database Schema",
            parent=parent_task,
            user_id=str(self.user.id),
        )
        self.assertEqual(child_2.wbs_code, "1.2")

    def test_wbs_tree_generation(self):
        """Generate hierarchical Work Breakdown Structure tree nodes."""
        parent = services.create_task(
            project=self.project,
            reporter=self.owner,
            code="TASK-TREE-1",
            title="Tree Parent",
        )
        services.create_task(
            project=self.project,
            reporter=self.owner,
            code="TASK-TREE-1-1",
            title="Tree Child 1",
            parent=parent,
        )

        tree = selectors.get_wbs_tree(project_id=self.project.id)
        self.assertIsInstance(tree, list)
        self.assertGreater(len(tree), 0)

    def test_task_status_transitions(self):
        """Transition task status (TODO -> IN_PROGRESS -> BLOCKED -> DONE -> TODO) and verify timestamps."""
        task = services.create_task(
            project=self.project,
            reporter=self.owner,
            code="TASK-STAT-001",
            title="Status Flow Task",
        )

        # Move to IN_PROGRESS
        services.update_task_status(task=task, status=TaskStatus.IN_PROGRESS, user_id=str(self.user.id))
        self.assertEqual(task.status, TaskStatus.IN_PROGRESS)

        # Move to BLOCKED
        services.update_task_status(task=task, status=TaskStatus.BLOCKED, block_reason="Waiting on API schema", user_id=str(self.user.id))
        self.assertEqual(task.status, TaskStatus.BLOCKED)

        # Move to DONE
        services.update_task_status(task=task, status=TaskStatus.DONE, user_id=str(self.user.id))
        self.assertEqual(task.status, TaskStatus.DONE)
        self.assertIsNotNone(task.completed_at)
        self.assertEqual(task.progress_percentage, Decimal("100.00"))

        # Reopen (DONE -> TODO)
        services.update_task_status(task=task, status=TaskStatus.TODO, user_id=str(self.user.id))
        self.assertEqual(task.status, TaskStatus.TODO)
        self.assertIsNone(task.completed_at)

    def test_task_dependency_circular_prevention(self):
        """Prevent circular dependency loops (A -> B -> C -> A raises validation error)."""
        task_a = services.create_task(project=self.project, reporter=self.owner, code="TASK-A", title="Task A")
        task_b = services.create_task(project=self.project, reporter=self.owner, code="TASK-B", title="Task B")
        task_c = services.create_task(project=self.project, reporter=self.owner, code="TASK-C", title="Task C")

        # A -> B
        services.add_task_dependency(source_task=task_a, target_task=task_b, dependency_type=DependencyType.FINISH_TO_START)
        # B -> C
        services.add_task_dependency(source_task=task_b, target_task=task_c, dependency_type=DependencyType.FINISH_TO_START)

        # Attempt C -> A should fail due to cycle
        with self.assertRaises(ProjectValidationError):
            services.add_task_dependency(source_task=task_c, target_task=task_a, dependency_type=DependencyType.FINISH_TO_START)

    def test_task_checklist_auto_progress(self):
        """Add checklist items, toggle completion, and verify auto progress percentage recalculation."""
        task = services.create_task(
            project=self.project,
            reporter=self.owner,
            code="TASK-CHK-001",
            title="Checklist Task",
        )

        item_1 = services.add_checklist_item(task=task, title="Step 1: Write Unit Test")
        item_2 = services.add_checklist_item(task=task, title="Step 2: Code Review")

        # Toggle item 1 -> 50%
        services.toggle_checklist_item(item=item_1, is_completed=True, user_id=str(self.user.id))
        task.refresh_from_db()
        self.assertEqual(task.progress_percentage, Decimal("50.00"))

        # Toggle item 2 -> 100%
        services.toggle_checklist_item(item=item_2, is_completed=True, user_id=str(self.user.id))
        task.refresh_from_db()
        self.assertEqual(task.progress_percentage, Decimal("100.00"))

    def test_task_threaded_comments(self):
        """Add parent comment and threaded reply comment."""
        task = services.create_task(
            project=self.project,
            reporter=self.owner,
            code="TASK-CMT-001",
            title="Comment Task",
        )

        parent_comment = services.add_task_comment(
            task=task,
            author_user_id=str(self.user.id),
            author_name="William Owner",
            content="Initial architecture discussion note.",
        )

        reply = services.add_task_comment(
            task=task,
            author_user_id=str(self.user.id),
            author_name="Wade Developer",
            content="Understood, starting implementation.",
            parent_comment=parent_comment,
        )

        self.assertEqual(reply.parent_comment, parent_comment)
        comments = selectors.list_task_comments(task_id=task.id)
        self.assertEqual(comments.count(), 1)
        self.assertEqual(comments[0].replies.count(), 1)

    def test_task_api_views(self):
        """Test REST APIView endpoints for task creation, WBS tree, dependencies, checklists, comments, and timeline."""
        # Create Task API
        res_create = self.client.post(
            "/api/v1/projects/tasks/",
            {
                "project_id": str(self.project.id),
                "reporter_id": str(self.owner.id),
                "assignee_id": str(self.dev.id),
                "code": "TASK-API-001",
                "title": "API Task Integration",
                "task_type": "TASK",
                "priority": "HIGH",
                "severity": "MINOR",
                "story_points": 5.0,
                "estimated_hours": 20.0,
            },
            format="json",
        )
        self.assertEqual(res_create.status_code, 201)
        task_id = res_create.data["data"]["id"]

        # List Tasks API
        res_list = self.client.get(f"/api/v1/projects/tasks/?project_id={self.project.id}")
        self.assertEqual(res_list.status_code, 200)

        # WBS Tree API
        res_wbs = self.client.get(f"/api/v1/projects/tasks/wbs-tree/?project_id={self.project.id}")
        self.assertEqual(res_wbs.status_code, 200)

        # Add Checklist Item API
        res_chk = self.client.post(f"/api/v1/projects/tasks/{task_id}/checklists/", {"title": "API Checklist 1"}, format="json")
        self.assertEqual(res_chk.status_code, 201)

        # Post Comment API
        res_cmt = self.client.post(f"/api/v1/projects/tasks/{task_id}/comments/", {"content": "API Comment body"}, format="json")
        self.assertEqual(res_cmt.status_code, 201)

        # Timeline API
        res_timeline = self.client.get(f"/api/v1/projects/tasks/{task_id}/timeline/")
        self.assertEqual(res_timeline.status_code, 200)
