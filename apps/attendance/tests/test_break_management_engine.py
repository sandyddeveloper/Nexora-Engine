"""Unit tests for Break Management Engine."""

import datetime
from django.test import TestCase

from apps.attendance.exceptions import AttendanceBreakError
from apps.attendance.models import BreakType
from apps.attendance.services import (
    check_in_employee,
    create_attendance_policy,
    end_break,
    start_break,
)
from apps.employees.services import create_employee
from apps.organizations.services import (
    create_branch,
    create_department,
    create_designation,
    create_organization,
)


class BreakManagementEngineTests(TestCase):
    """Test suite for break start, break end, and interval duration tracking."""

    def setUp(self):
        self.org = create_organization(name="Break Test Org")
        self.branch = create_branch(organization=self.org, code="BR-1", name="Branch 1")
        self.dept = create_department(organization=self.org, branch=self.branch, code="DEP-1", name="Dept 1")
        self.desig = create_designation(organization=self.org, department=self.dept, code="DES-1", name="Desig 1")

        self.policy = create_attendance_policy(
            organization=self.org,
            name="Default Policy",
            code="DEF-POL",
            is_default=True,
        )

        self.emp = create_employee(
            organization=self.org,
            branch=self.branch,
            department=self.dept,
            designation=self.desig,
            first_name="Break",
            last_name="Worker",
            official_email="break@breaktest.com",
            date_of_joining=datetime.date.today(),
        )

    def test_start_and_end_break_success(self):
        check_in_employee(employee=self.emp)

        brk_start = datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(minutes=45)
        brk = start_break(
            employee=self.emp,
            break_type=BreakType.LUNCH,
            start_time=brk_start,
        )

        self.assertIsNotNone(brk.id)
        self.assertIsNone(brk.end_time)

        brk_end = datetime.datetime.now(datetime.timezone.utc)
        completed_brk = end_break(employee=self.emp, end_time=brk_end)

        self.assertEqual(completed_brk.end_time, brk_end)
        self.assertGreater(completed_brk.duration_minutes, 0)

    def test_start_break_without_checkin_raises_error(self):
        with self.assertRaises(AttendanceBreakError):
            start_break(employee=self.emp)
