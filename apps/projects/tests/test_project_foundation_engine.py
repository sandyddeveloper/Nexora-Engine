"""Unit tests for Enterprise Project Management Foundation Engine."""

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
from apps.projects.enums import ProjectCategory, ProjectMemberRole, ProjectPriority, ProjectStatus, ProjectType
from apps.projects.exceptions import ProjectLifecycleError, ProjectValidationError


class ProjectFoundationEngineTestCase(TestCase):
    """Test suite for Enterprise Project Management Foundation Engine."""

    @classmethod
    def setUpTestData(cls):
        cls.org = create_organization(name="Apex Enterprise Corp")
        cls.branch = create_branch(organization=cls.org, code="APXMAIN", name="Apex HQ")
        cls.dept = create_department(organization=cls.org, branch=cls.branch, code="APXENG", name="Engineering Dept")
        cls.desg = create_designation(organization=cls.org, department=cls.dept, code="APXSENG", name="Senior Engineer")

        cls.user = create_user(email="pmadmin@apexcorp.com", password="SecurePassword123!")

        cls.owner = create_employee(
            organization=cls.org,
            branch=cls.branch,
            department=cls.dept,
            designation=cls.desg,
            first_name="Victor",
            last_name="Director",
            official_email="vdirector@apexcorp.com",
            date_of_joining=date(2023, 1, 1),
        )

        cls.manager = create_employee(
            organization=cls.org,
            branch=cls.branch,
            department=cls.dept,
            designation=cls.desg,
            first_name="Pamela",
            last_name="Manager",
            official_email="pmanager@apexcorp.com",
            date_of_joining=date(2023, 6, 1),
        )

        cls.dev = create_employee(
            organization=cls.org,
            branch=cls.branch,
            department=cls.dept,
            designation=cls.desg,
            first_name="David",
            last_name="Developer",
            official_email="ddeveloper@apexcorp.com",
            date_of_joining=date(2024, 1, 1),
        )

    def setUp(self):
        self.client = APIClient()
        self.client.force_authenticate(user=self.user)

    def test_create_project(self):
        """Create a new project and verify default owner/manager member assignments."""
        project = services.create_project(
            organization=self.org,
            owner=self.owner,
            manager=self.manager,
            code="PRJ-NEX-001",
            name="Nexora Engine Core Upgrade",
            description="Core operational foundation project.",
            project_type=ProjectType.INTERNAL,
            category=ProjectCategory.SOFTWARE,
            priority=ProjectPriority.HIGH,
            estimated_budget=Decimal("500000.00"),
            estimated_hours=Decimal("2000.00"),
            user_id=str(self.user.id),
        )

        self.assertEqual(project.code, "PRJ-NEX-001")
        self.assertEqual(project.status, ProjectStatus.DRAFT)
        self.assertEqual(project.owner, self.owner)
        self.assertEqual(project.manager, self.manager)

        # Check automatic member assignment for Owner & Manager
        members = selectors.list_project_members(project_id=project.id)
        self.assertEqual(members.count(), 2)

    def test_duplicate_project_code_raises_error(self):
        """Creating a project with duplicate code in same org raises validation error."""
        services.create_project(
            organization=self.org,
            owner=self.owner,
            manager=self.manager,
            code="PRJ-DUP-001",
            name="Original Project",
        )
        with self.assertRaises(ProjectValidationError):
            services.create_project(
                organization=self.org,
                owner=self.owner,
                manager=self.manager,
                code="PRJ-DUP-001",
                name="Duplicate Code Project",
            )

    def test_project_lifecycle_state_machine(self):
        """Test valid state transitions: DRAFT -> IN_PROGRESS -> ON_HOLD -> IN_PROGRESS -> COMPLETED -> ARCHIVED."""
        project = services.create_project(
            organization=self.org,
            owner=self.owner,
            manager=self.manager,
            code="PRJ-LIFECYCLE-001",
            name="Lifecycle Flow Project",
        )

        # Activate (DRAFT -> IN_PROGRESS)
        activated = services.activate_project(project=project, user_id=str(self.user.id))
        self.assertEqual(activated.status, ProjectStatus.IN_PROGRESS)

        # Pause (IN_PROGRESS -> ON_HOLD)
        paused = services.pause_project(project=activated, reason="Resource reallocation", user_id=str(self.user.id))
        self.assertEqual(paused.status, ProjectStatus.ON_HOLD)

        # Resume (ON_HOLD -> IN_PROGRESS)
        resumed = services.resume_project(project=paused, user_id=str(self.user.id))
        self.assertEqual(resumed.status, ProjectStatus.IN_PROGRESS)

        # Complete (IN_PROGRESS -> COMPLETED)
        completed = services.complete_project(project=resumed, user_id=str(self.user.id))
        self.assertEqual(completed.status, ProjectStatus.COMPLETED)

        # Archive (COMPLETED -> ARCHIVED)
        archived = services.archive_project(project=completed, user_id=str(self.user.id))
        self.assertEqual(archived.status, ProjectStatus.ARCHIVED)
        self.assertTrue(archived.is_archived)

        # Restore (ARCHIVED -> DRAFT)
        restored = services.restore_project(project=archived, user_id=str(self.user.id))
        self.assertFalse(restored.is_archived)
        self.assertEqual(restored.status, ProjectStatus.DRAFT)

    def test_invalid_lifecycle_transition_raises_error(self):
        """Attempting invalid state transition (e.g. DRAFT -> ON_HOLD) raises LifecycleError."""
        project = services.create_project(
            organization=self.org,
            owner=self.owner,
            manager=self.manager,
            code="PRJ-ERR-001",
            name="Error Flow Project",
        )

        with self.assertRaises(ProjectLifecycleError):
            services.pause_project(project=project, reason="Cannot pause draft")

    def test_add_and_remove_project_member(self):
        """Assign employee to project with specific role and allocated hours."""
        project = services.create_project(
            organization=self.org,
            owner=self.owner,
            manager=self.manager,
            code="PRJ-MEM-001",
            name="Member Project",
        )

        member = services.add_project_member(
            project=project,
            employee=self.dev,
            role=ProjectMemberRole.DEVELOPER,
            allocated_hours_per_week=Decimal("30.00"),
            user_id=str(self.user.id),
        )
        self.assertEqual(member.role, ProjectMemberRole.DEVELOPER)
        self.assertEqual(member.allocated_hours_per_week, Decimal("30.00"))

        # Remove member
        services.remove_project_member(project=project, employee=self.dev, user_id=str(self.user.id))
        active_members = selectors.list_project_members(project_id=project.id)
        self.assertNotIn(self.dev, [m.employee for m in active_members])

    def test_update_project_settings(self):
        """Update project configuration settings JSON."""
        project = services.create_project(
            organization=self.org,
            owner=self.owner,
            manager=self.manager,
            code="PRJ-SET-001",
            name="Settings Project",
        )

        updated = services.update_project_settings(
            project=project,
            settings_dict={"timezone": "Asia/Kolkata", "sprint_duration_weeks": 2},
            user_id=str(self.user.id),
        )
        self.assertEqual(updated.settings_json["timezone"], "Asia/Kolkata")
        self.assertEqual(updated.settings_json["sprint_duration_weeks"], 2)

    def test_project_audit_logs(self):
        """Verify audit trail entries generated during project operations."""
        project = services.create_project(
            organization=self.org,
            owner=self.owner,
            manager=self.manager,
            code="PRJ-AUDIT-001",
            name="Audit Log Project",
            user_id=str(self.user.id),
        )

        services.activate_project(project=project, user_id=str(self.user.id))
        logs = selectors.get_project_audit_logs(project_id=project.id)
        self.assertGreaterEqual(logs.count(), 2)
        actions = [log.action for log in logs]
        self.assertIn("PROJECT_CREATED", actions)
        self.assertIn("PROJECT_ACTIVATED", actions)

    def test_project_api_views(self):
        """Test REST APIView endpoints for project CRUD, lifecycle actions, member assignment, and settings."""
        # Create Project API
        res_create = self.client.post(
            "/api/v1/projects/",
            {
                "organization_id": str(self.org.id),
                "owner_id": str(self.owner.id),
                "manager_id": str(self.manager.id),
                "code": "PRJ-API-001",
                "name": "API Test Project",
                "project_type": "CLIENT",
                "category": "CLIENT_DELIVERY",
                "priority": "HIGH",
                "estimated_budget": 100000.0,
                "estimated_hours": 500.0,
            },
            format="json",
        )
        self.assertEqual(res_create.status_code, 201)
        project_id = res_create.data["data"]["id"]

        # List Projects API
        res_list = self.client.get(f"/api/v1/projects/?organization_id={self.org.id}")
        self.assertEqual(res_list.status_code, 200)

        # Get Project Detail API
        res_detail = self.client.get(f"/api/v1/projects/{project_id}/")
        self.assertEqual(res_detail.status_code, 200)

        # Activate Project API
        res_act = self.client.post(f"/api/v1/projects/{project_id}/activate/")
        self.assertEqual(res_act.status_code, 200)
        self.assertEqual(res_act.data["data"]["status"], "IN_PROGRESS")

        # Pause Project API
        res_pause = self.client.post(f"/api/v1/projects/{project_id}/pause/", {"reason": "On hold for testing"}, format="json")
        self.assertEqual(res_pause.status_code, 200)
        self.assertEqual(res_pause.data["data"]["status"], "ON_HOLD")

        # Resume Project API
        res_resume = self.client.post(f"/api/v1/projects/{project_id}/resume/")
        self.assertEqual(res_resume.status_code, 200)

        # Add Member API
        res_mem = self.client.post(
            f"/api/v1/projects/{project_id}/members/",
            {"employee_id": str(self.dev.id), "role": "DEVELOPER", "allocated_hours_per_week": 40.0},
            format="json",
        )
        self.assertEqual(res_mem.status_code, 201)

        # Update Settings API
        res_set = self.client.put(
            f"/api/v1/projects/{project_id}/settings/",
            {"settings": {"timezone": "Europe/London"}},
            format="json",
        )
        self.assertEqual(res_set.status_code, 200)
