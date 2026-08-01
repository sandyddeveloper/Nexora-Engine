"""Unit tests for Employee Domain atomic services."""

import datetime
from django.test import TestCase

from apps.employees.models import EmploymentHistory
from apps.employees.services import (
    create_employee,
    promote_employee,
    transfer_employee,
)
from apps.organizations.services import (
    create_branch,
    create_department,
    create_designation,
    create_organization,
)


class EmployeeServiceTests(TestCase):
    """Test suite for atomic employee services and employment history auditing."""

    def setUp(self):
        self.org = create_organization(name="Service Test Org")
        self.branch1 = create_branch(organization=self.org, code="BR-1", name="Branch 1")
        self.branch2 = create_branch(organization=self.org, code="BR-2", name="Branch 2")
        self.dept1 = create_department(
            organization=self.org, branch=self.branch1, code="DEP-1", name="Dept 1"
        )
        self.dept2 = create_department(
            organization=self.org, branch=self.branch2, code="DEP-2", name="Dept 2"
        )
        self.desig1 = create_designation(
            organization=self.org, department=self.dept1, code="DES-1", name="Engineer"
        )
        self.desig2 = create_designation(
            organization=self.org, department=self.dept1, code="DES-2", name="Lead Engineer"
        )

    def test_create_employee_with_profile(self):
        emp = create_employee(
            organization=self.org,
            branch=self.branch1,
            department=self.dept1,
            designation=self.desig1,
            first_name="Alice",
            last_name="Wonderland",
            official_email="alice@servicetest.com",
            date_of_joining=datetime.date.today(),
            city="New York",
            country="United States",
        )

        self.assertIsNotNone(emp.id)
        self.assertIsNotNone(emp.profile)
        self.assertEqual(emp.profile.city, "New York")

    def test_transfer_employee_records_history(self):
        emp = create_employee(
            organization=self.org,
            branch=self.branch1,
            department=self.dept1,
            designation=self.desig1,
            first_name="Bob",
            last_name="Builder",
            official_email="bob@servicetest.com",
            date_of_joining=datetime.date.today(),
        )

        today = datetime.date.today()
        emp = transfer_employee(
            employee=emp,
            new_branch=self.branch2,
            new_department=self.dept2,
            effective_date=today,
            remarks="Relocation to Branch 2",
        )

        self.assertEqual(emp.branch, self.branch2)
        self.assertEqual(emp.department, self.dept2)

        history = EmploymentHistory.objects.filter(employee=emp, change_type="TRANSFER").first()
        self.assertIsNotNone(history)
        self.assertEqual(history.new_data["branch_name"], "Branch 2")

    def test_promote_employee_records_history(self):
        emp = create_employee(
            organization=self.org,
            branch=self.branch1,
            department=self.dept1,
            designation=self.desig1,
            first_name="Charlie",
            last_name="Brown",
            official_email="charlie@servicetest.com",
            date_of_joining=datetime.date.today(),
        )

        today = datetime.date.today()
        emp = promote_employee(
            employee=emp,
            new_designation=self.desig2,
            effective_date=today,
            remarks="Annual performance promotion",
        )

        self.assertEqual(emp.designation, self.desig2)

        history = EmploymentHistory.objects.filter(employee=emp, change_type="PROMOTION").first()
        self.assertIsNotNone(history)
        self.assertEqual(history.new_data["designation_name"], "Lead Engineer")
