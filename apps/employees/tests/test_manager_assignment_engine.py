"""Unit tests for Manager Assignment Engine and Bulk Manager Assignment."""

import datetime
from django.test import TestCase

from apps.employees.models import ManagerAssignment, ManagerType
from apps.employees.services import (
    assign_manager,
    bulk_assign_manager,
    create_employee,
)
from apps.organizations.services import (
    create_branch,
    create_department,
    create_designation,
    create_organization,
)


class ManagerAssignmentEngineTests(TestCase):
    """Test suite for primary/secondary manager assignments and bulk manager changes."""

    def setUp(self):
        self.org = create_organization(name="Mgr Test Org")
        self.branch = create_branch(organization=self.org, code="BR-1", name="Branch 1")
        self.dept = create_department(organization=self.org, branch=self.branch, code="DEP-1", name="Dept 1")
        self.desig = create_designation(organization=self.org, department=self.dept, code="DES-1", name="Desig 1")

        self.manager = create_employee(
            organization=self.org,
            branch=self.branch,
            department=self.dept,
            designation=self.desig,
            first_name="Leader",
            last_name="Manager",
            official_email="manager@mgrtest.com",
            date_of_joining=datetime.date.today(),
        )

        self.emp1 = create_employee(
            organization=self.org,
            branch=self.branch,
            department=self.dept,
            designation=self.desig,
            first_name="Emp",
            last_name="One",
            official_email="emp1@mgrtest.com",
            date_of_joining=datetime.date.today(),
        )

        self.emp2 = create_employee(
            organization=self.org,
            branch=self.branch,
            department=self.dept,
            designation=self.desig,
            first_name="Emp",
            last_name="Two",
            official_email="emp2@mgrtest.com",
            date_of_joining=datetime.date.today(),
        )

    def test_assign_primary_manager(self):
        today = datetime.date.today()
        assignment = assign_manager(
            employee=self.emp1,
            manager=self.manager,
            manager_type=ManagerType.PRIMARY,
            effective_date=today,
        )

        self.assertIsNotNone(assignment.id)
        self.assertTrue(assignment.is_active)
        self.assertEqual(self.emp1.reporting_manager, self.manager)

    def test_bulk_assign_manager(self):
        count = bulk_assign_manager(
            employee_ids=[self.emp1.id, self.emp2.id],
            manager=self.manager,
            manager_type=ManagerType.PRIMARY,
        )

        self.assertEqual(count, 2)
        self.emp1.refresh_from_db()
        self.emp2.refresh_from_db()
        self.assertEqual(self.emp1.reporting_manager, self.manager)
        self.assertEqual(self.emp2.reporting_manager, self.manager)
