"""Unit tests for Employee Domain models."""

import datetime
from django.test import TestCase

from apps.employees.models import (
    Employee,
    EmployeeProfile,
    EmploymentStatus,
    EmploymentType,
)
from apps.organizations.services import (
    create_branch,
    create_department,
    create_designation,
    create_organization,
)


class EmployeeModelTests(TestCase):
    """Test suite for Employee model auto-generated IDs and profile linking."""

    def setUp(self):
        self.org = create_organization(name="Emp Test Org")
        self.branch = create_branch(organization=self.org, code="BR-1", name="Branch 1")
        self.dept = create_department(
            organization=self.org, branch=self.branch, code="DEP-1", name="Dept 1"
        )
        self.desig = create_designation(
            organization=self.org, department=self.dept, code="DES-1", name="Desig 1"
        )

    def test_employee_creation_generates_employee_id(self):
        emp = Employee.objects.create(
            organization=self.org,
            branch=self.branch,
            department=self.dept,
            designation=self.desig,
            first_name="Jane",
            last_name="Doe",
            official_email="jane.doe@emptest.com",
            date_of_joining=datetime.date.today(),
        )

        self.assertIsNotNone(emp.id)
        self.assertTrue(emp.employee_id.startswith("EMP-"))
        self.assertEqual(emp.display_name, "Jane Doe")
        self.assertEqual(emp.employment_status, EmploymentStatus.PROBATION)
        self.assertEqual(emp.employment_type, EmploymentType.FULL_TIME)

    def test_employee_profile_creation(self):
        emp = Employee.objects.create(
            organization=self.org,
            branch=self.branch,
            department=self.dept,
            designation=self.desig,
            first_name="John",
            last_name="Smith",
            official_email="john.smith@emptest.com",
            date_of_joining=datetime.date.today(),
        )

        profile = EmployeeProfile.objects.create(
            employee=emp,
            personal_email="john.smith.personal@example.com",
            city="San Francisco",
            country="United States",
        )

        self.assertEqual(profile.employee, emp)
        self.assertEqual(emp.profile.city, "San Francisco")
