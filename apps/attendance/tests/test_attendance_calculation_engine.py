"""Unit tests for Attendance Calculation & Status Engine."""

import datetime
from decimal import Decimal
from django.test import TestCase

from apps.attendance.models import AttendanceStatus
from apps.attendance.services import (
    calculate_daily_attendance,
    check_in_employee,
    check_out_employee,
    create_attendance_policy,
)
from apps.employees.services import create_employee
from apps.organizations.services import (
    create_branch,
    create_department,
    create_designation,
    create_organization,
)


class AttendanceCalculationEngineTests(TestCase):
    """Test suite for automated net working hours, overtime, and status calculation."""

    def setUp(self):
        self.org = create_organization(name="Calc Test Org")
        self.branch = create_branch(organization=self.org, code="BR-1", name="Branch 1")
        self.dept = create_department(organization=self.org, branch=self.branch, code="DEP-1", name="Dept 1")
        self.desig = create_designation(organization=self.org, department=self.dept, code="DES-1", name="Desig 1")

        self.policy = create_attendance_policy(
            organization=self.org,
            name="Standard 8 Hour Policy",
            code="STD-8H",
            full_day_working_hours=Decimal("8.00"),
            minimum_working_hours=Decimal("4.00"),
            is_default=True,
        )

        self.emp = create_employee(
            organization=self.org,
            branch=self.branch,
            department=self.dept,
            designation=self.desig,
            first_name="Calc",
            last_name="Employee",
            official_email="calc@calctest.com",
            date_of_joining=datetime.date.today(),
        )

    def test_full_day_attendance_calculation(self):
        now = datetime.datetime.now(datetime.timezone.utc)
        check_in_dt = now - datetime.timedelta(hours=9)
        check_out_dt = now

        session = check_in_employee(employee=self.emp, check_in_time=check_in_dt)
        check_out_employee(employee=self.emp, check_out_time=check_out_dt)

        record = session.attendance_record
        record.refresh_from_db()

        self.assertEqual(record.status, AttendanceStatus.PRESENT)
        self.assertGreaterEqual(record.working_hours, Decimal("8.00"))
        self.assertGreater(record.overtime_hours, Decimal("0.00"))

    def test_half_day_attendance_calculation(self):
        now = datetime.datetime.now(datetime.timezone.utc)
        check_in_dt = now - datetime.timedelta(hours=5)
        check_out_dt = now

        session = check_in_employee(employee=self.emp, check_in_time=check_in_dt)
        check_out_employee(employee=self.emp, check_out_time=check_out_dt)

        record = session.attendance_record
        record.refresh_from_db()

        self.assertEqual(record.status, AttendanceStatus.HALF_DAY)
