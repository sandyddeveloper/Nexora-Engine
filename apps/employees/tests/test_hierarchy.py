"""Unit tests for reporting manager hierarchy and organization boundary validation."""

import datetime
from django.test import TestCase

from apps.employees.exceptions import CircularReportingError, EmployeeHierarchyError
from apps.employees.services import (
    create_employee,
    update_employee,
    validate_organization_hierarchy,
    validate_reporting_hierarchy,
)
from apps.organizations.services import (
    create_branch,
    create_department,
    create_designation,
    create_organization,
)


class EmployeeHierarchyTests(TestCase):
    """Test suite for reporting hierarchy loop prevention and organization boundary enforcement."""

    def setUp(self):
        self.org1 = create_organization(name="Org 1")
        self.org2 = create_organization(name="Org 2")

        self.branch1 = create_branch(organization=self.org1, code="BR-1", name="Branch 1")
        self.branch2 = create_branch(organization=self.org2, code="BR-2", name="Branch 2")

        self.dept1 = create_department(
            organization=self.org1, branch=self.branch1, code="DEP-1", name="Dept 1"
        )

        self.desig1 = create_designation(
            organization=self.org1, department=self.dept1, code="DES-1", name="Desig 1"
        )

    def test_self_reporting_rejected(self):
        emp = create_employee(
            organization=self.org1,
            branch=self.branch1,
            department=self.dept1,
            designation=self.desig1,
            first_name="Emp",
            last_name="One",
            official_email="emp1@org1.com",
            date_of_joining=datetime.date.today(),
        )

        with self.assertRaises(CircularReportingError):
            validate_reporting_hierarchy(employee=emp, reporting_manager=emp)

        with self.assertRaises(CircularReportingError):
            update_employee(employee=emp, reporting_manager=emp)

    def test_cross_organization_hierarchy_rejected(self):
        with self.assertRaises(EmployeeHierarchyError):
            validate_organization_hierarchy(
                organization=self.org1, branch=self.branch2, department=self.dept1
            )
