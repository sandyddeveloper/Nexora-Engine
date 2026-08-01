"""Unit tests for Shift and Work Location Assignment Engines."""

import datetime
from django.test import TestCase

from apps.employees.models import WorkforceAssignment
from apps.employees.services import (
    assign_shift,
    assign_work_location,
    create_employee,
)
from apps.organizations.services import (
    create_branch,
    create_department,
    create_designation,
    create_organization,
    create_shift,
)


class ShiftAndLocationEngineTests(TestCase):
    """Test suite for shift and work location assignment workflows."""

    def setUp(self):
        self.org = create_organization(name="Shift Location Org")
        self.branch = create_branch(organization=self.org, code="BR-1", name="Branch 1")
        self.dept = create_department(organization=self.org, branch=self.branch, code="DEP-1", name="Dept 1")
        self.desig = create_designation(organization=self.org, department=self.dept, code="DES-1", name="Desig 1")

        self.shift = create_shift(
            organization=self.org,
            name="Night Shift",
            code="NIGHT",
            start_time=datetime.time(22, 0),
            end_time=datetime.time(6, 0),
            is_night_shift=True,
        )

        self.emp = create_employee(
            organization=self.org,
            branch=self.branch,
            department=self.dept,
            designation=self.desig,
            first_name="Worker",
            last_name="One",
            official_email="worker@shiftloc.com",
            date_of_joining=datetime.date.today(),
        )

    def test_assign_shift_creates_assignment_history(self):
        today = datetime.date.today()
        assignment = assign_shift(
            employee=self.emp,
            shift=self.shift,
            effective_date=today,
            reason="Project night shift allocation",
        )

        self.assertIsNotNone(assignment.id)
        self.assertEqual(self.emp.shift, self.shift)
        self.assertEqual(assignment.new_value["shift_code"], "NIGHT")

    def test_assign_work_location(self):
        today = datetime.date.today()
        assignment = assign_work_location(
            employee=self.emp,
            work_location="Full Remote - California",
            location_type="REMOTE",
            effective_date=today,
        )

        self.assertIsNotNone(assignment.id)
        self.assertEqual(self.emp.work_location, "Full Remote - California")
        self.assertEqual(assignment.new_value["location_type"], "REMOTE")
