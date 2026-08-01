"""Unit tests for Employee Lifecycle FSM state transitions."""

import datetime
from django.test import TestCase

from apps.employees.exceptions import InvalidEmployeeLifecycleTransitionError
from apps.employees.models import EmploymentStatus
from apps.employees.services import (
    create_employee,
    transition_employee_lifecycle_status,
)
from apps.organizations.services import (
    create_branch,
    create_department,
    create_designation,
    create_organization,
)


class EmployeeLifecycleFSMTests(TestCase):
    """Test suite for 14-state lifecycle FSM state machine validation."""

    def setUp(self):
        self.org = create_organization(name="FSM Org")
        self.branch = create_branch(organization=self.org, code="BR-1", name="Branch 1")
        self.dept = create_department(organization=self.org, branch=self.branch, code="DEP-1", name="Dept 1")
        self.desig = create_designation(organization=self.org, department=self.dept, code="DES-1", name="Desig 1")

        self.emp = create_employee(
            organization=self.org,
            branch=self.branch,
            department=self.dept,
            designation=self.desig,
            first_name="FSM",
            last_name="Test",
            official_email="fsm@test.com",
            date_of_joining=datetime.date.today(),
            employment_status=EmploymentStatus.PROBATION,
        )

    def test_valid_lifecycle_fsm_transitions(self):
        # PROBATION -> CONFIRMED
        self.emp = transition_employee_lifecycle_status(
            employee=self.emp, target_status=EmploymentStatus.CONFIRMED
        )
        self.assertEqual(self.emp.employment_status, EmploymentStatus.CONFIRMED)

        # CONFIRMED -> ACTIVE
        self.emp = transition_employee_lifecycle_status(
            employee=self.emp, target_status=EmploymentStatus.ACTIVE
        )
        self.assertEqual(self.emp.employment_status, EmploymentStatus.ACTIVE)

        # ACTIVE -> SUSPENDED
        self.emp = transition_employee_lifecycle_status(
            employee=self.emp, target_status=EmploymentStatus.SUSPENDED, reason="Investigation"
        )
        self.assertEqual(self.emp.employment_status, EmploymentStatus.SUSPENDED)

    def test_invalid_lifecycle_transition_raises_error(self):
        # PROBATION -> ARCHIVED should fail
        with self.assertRaises(InvalidEmployeeLifecycleTransitionError):
            transition_employee_lifecycle_status(
                employee=self.emp, target_status=EmploymentStatus.ARCHIVED
            )
