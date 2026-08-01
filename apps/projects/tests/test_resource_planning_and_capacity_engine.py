"""Unit tests for Enterprise Resource Planning, Capacity Management & Workload Optimization Engine."""

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
from apps.projects.enums import AllocationStatus, AllocationType, WorkloadStatus
from apps.projects.exceptions import ProjectValidationError


class ResourcePlanningAndCapacityEngineTestCase(TestCase):
    """Test suite for Resource Allocation, Capacity, Workload, Bench Management, and Skill Matching."""

    @classmethod
    def setUpTestData(cls):
        cls.org = create_organization(name="Resource Enterprise Corp")
        cls.branch = create_branch(organization=cls.org, code="RESHQ", name="Resource HQ")
        cls.dept = create_department(organization=cls.org, branch=cls.branch, code="RESLAB", name="R&D Lab")
        cls.desg = create_designation(organization=cls.org, department=cls.dept, code="RESSENG", name="Principal Engineer")

        cls.user_res = create_user(email="resourceuser@rescorp.com", password="SecurePassword123!")

        cls.owner = create_employee(
            organization=cls.org,
            branch=cls.branch,
            department=cls.dept,
            designation=cls.desg,
            first_name="Ray",
            last_name="Owner",
            official_email="rowner@rescorp.com",
            date_of_joining=date(2023, 1, 1),
        )

        cls.dev = create_employee(
            organization=cls.org,
            branch=cls.branch,
            department=cls.dept,
            designation=cls.desg,
            user=cls.user_res,
            first_name="Rita",
            last_name="Resource",
            official_email="rresource@rescorp.com",
            date_of_joining=date(2024, 1, 1),
        )

        cls.project1 = services.create_project(
            organization=cls.org,
            owner=cls.owner,
            manager=cls.owner,
            code="PRJ-RES-01",
            name="Resource Planning Project 1",
        )
        services.activate_project(project=cls.project1)

        cls.project2 = services.create_project(
            organization=cls.org,
            owner=cls.owner,
            manager=cls.owner,
            code="PRJ-RES-02",
            name="Resource Planning Project 2",
        )
        services.activate_project(project=cls.project2)

    def setUp(self):
        self.client = APIClient()
        self.client.force_authenticate(user=self.user_res)

    def test_resource_allocation_percentage_and_hours(self):
        """Allocate resource at 50% and verify daily planned hours calculation."""
        today = date.today()
        alloc = services.allocate_resource(
            employee=self.dev,
            project=self.project1,
            start_date=today,
            end_date=today + timedelta(days=30),
            allocation_percentage=Decimal("50.00"),
            notes="50% allocation on Project 1",
        )

        self.assertEqual(alloc.allocation_percentage, Decimal("50.00"))
        self.assertEqual(alloc.allocated_hours_per_day, Decimal("4.00"))
        self.assertEqual(alloc.status, AllocationStatus.ACTIVE)

    def test_overallocation_conflict_detection(self):
        """Attempt to overallocate resource beyond 100% and enforce validation failure."""
        today = date.today()
        # Allocate 60% on Project 1
        services.allocate_resource(
            employee=self.dev,
            project=self.project1,
            start_date=today,
            end_date=today + timedelta(days=30),
            allocation_percentage=Decimal("60.00"),
        )

        # Conflict check selector
        conflict = selectors.detect_allocation_conflicts(
            employee_id=self.dev.id,
            start_date=today,
            end_date=today + timedelta(days=10),
        )
        self.assertFalse(conflict["is_conflicted"])
        self.assertEqual(conflict["total_allocation_percentage"], 60.0)

        # Attempt adding 50% on Project 2 (Total 110% > 100% - Should fail)
        with self.assertRaises(ProjectValidationError):
            services.allocate_resource(
                employee=self.dev,
                project=self.project2,
                start_date=today,
                end_date=today + timedelta(days=30),
                allocation_percentage=Decimal("50.00"),
            )

    def test_capacity_and_workload_metrics_calculation(self):
        """Calculate employee capacity, utilization rate, and workload status."""
        today = date.today()
        services.allocate_resource(
            employee=self.dev,
            project=self.project1,
            start_date=today,
            end_date=today + timedelta(days=7),
            allocation_percentage=Decimal("75.00"),
        )

        cap = selectors.calculate_employee_capacity(
            employee_id=self.dev.id,
            start_date=today,
            end_date=today + timedelta(days=7),
        )
        self.assertEqual(cap["workload_status"], WorkloadStatus.OPTIMAL)
        self.assertEqual(cap["utilization_rate"], 75.0)

    def test_bench_management(self):
        """Identify underutilized bench resources and assign to bench."""
        bench = selectors.list_bench_resources(organization_id=self.org.id)
        self.assertTrue(any(b["employee_id"] == str(self.dev.id) for b in bench))

        # Assign to bench
        services.assign_to_bench(employee=self.dev)
        allocs = selectors.list_employee_allocations(employee_id=self.dev.id, active_only=True)
        self.assertEqual(allocs.count(), 0)

    def test_resource_planning_api_endpoints(self):
        """Test REST APIView endpoints for allocations, capacity, bench, and skill match."""
        today = date.today()

        # Create Allocation API
        res_alloc = self.client.post(
            "/api/v1/projects/resources/allocations/",
            {
                "employee_id": str(self.dev.id),
                "project_id": str(self.project1.id),
                "allocation_percentage": 50.0,
                "start_date": today.isoformat(),
                "end_date": (today + timedelta(days=14)).isoformat(),
            },
            format="json",
        )
        self.assertEqual(res_alloc.status_code, 201)

        # List Allocations API
        res_list = self.client.get(f"/api/v1/projects/resources/allocations/?project_id={self.project1.id}")
        self.assertEqual(res_list.status_code, 200)

        # Capacity API
        res_cap = self.client.get(f"/api/v1/projects/resources/capacity/?employee_id={self.dev.id}&start_date={today.isoformat()}&end_date={(today + timedelta(days=7)).isoformat()}")
        self.assertEqual(res_cap.status_code, 200)

        # Bench API
        res_bench = self.client.get(f"/api/v1/projects/resources/bench/?organization_id={self.org.id}")
        self.assertEqual(res_bench.status_code, 200)

        # Skill Match API
        res_skill = self.client.get(f"/api/v1/projects/resources/skill-match/?project_id={self.project1.id}")
        self.assertEqual(res_skill.status_code, 200)
