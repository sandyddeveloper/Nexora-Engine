"""Unit tests for Shift Rotation, Shift Override, and Swap Foundation Engines."""

import datetime
from django.test import TestCase

from apps.employees.services import create_employee
from apps.organizations.models import SwapStatus
from apps.organizations.services import (
    create_branch,
    create_department,
    create_designation,
    create_organization,
    create_shift,
    create_shift_roster,
    override_employee_shift,
    submit_shift_swap_request,
)


class ShiftRotationAndOverrideEngineTests(TestCase):
    """Test suite for manual shift overrides and peer-to-peer swap foundation."""

    def setUp(self):
        self.org = create_organization(name="Rotation Test Org")
        self.branch = create_branch(organization=self.org, code="BR-1", name="Branch 1")
        self.dept = create_department(organization=self.org, branch=self.branch, code="DEP-1", name="Dept 1")
        self.desig = create_designation(organization=self.org, department=self.dept, code="DES-1", name="Desig 1")

        self.shift_morn = create_shift(
            organization=self.org,
            name="Morning Shift",
            code="MORN",
            start_time=datetime.time(6, 0),
            end_time=datetime.time(14, 0),
        )
        self.shift_night = create_shift(
            organization=self.org,
            name="Night Shift",
            code="NIGHT",
            start_time=datetime.time(22, 0),
            end_time=datetime.time(6, 0),
            is_night_shift=True,
        )

        self.emp1 = create_employee(
            organization=self.org,
            branch=self.branch,
            department=self.dept,
            designation=self.desig,
            first_name="Emp",
            last_name="One",
            official_email="emp1@rot.com",
            date_of_joining=datetime.date.today(),
        )
        self.emp2 = create_employee(
            organization=self.org,
            branch=self.branch,
            department=self.dept,
            designation=self.desig,
            first_name="Emp",
            last_name="Two",
            official_email="emp2@rot.com",
            date_of_joining=datetime.date.today(),
        )

    def test_emergency_shift_override(self):
        today = datetime.date.today()
        roster = create_shift_roster(
            organization=self.org,
            name="Emergency Override Roster",
            code="EMERG-ROST",
            start_date=today,
            end_date=today + datetime.timedelta(days=7),
        )

        override = override_employee_shift(
            roster=roster,
            employee=self.emp1,
            shift=self.shift_night,
            date=today,
            reason="Emergency night coverage",
        )

        self.assertTrue(override.is_override)
        self.assertEqual(override.override_reason, "Emergency night coverage")
        self.assertEqual(override.shift, self.shift_night)

    def test_submit_shift_swap_request(self):
        d1 = datetime.date.today()
        d2 = d1 + datetime.timedelta(days=1)

        swap_req = submit_shift_swap_request(
            requester=self.emp1,
            target_employee=self.emp2,
            requester_date=d1,
            target_date=d2,
            reason="Family commitment",
        )

        self.assertIsNotNone(swap_req.id)
        self.assertEqual(swap_req.status, SwapStatus.PENDING)
