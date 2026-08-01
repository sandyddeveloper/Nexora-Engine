"""Unit tests for Check-In and Check-Out Engines."""

import datetime
from django.test import TestCase

from apps.attendance.exceptions import AttendanceCheckInError, AttendanceCheckOutError
from apps.attendance.models import AttendanceStatus
from apps.attendance.services import (
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


class CheckInCheckOutEngineTests(TestCase):
    """Test suite for operational Check-In and Check-Out workflows."""

    def setUp(self):
        self.org = create_organization(name="Punch Test Org")
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
            first_name="John",
            last_name="Punc",
            official_email="john@punchtest.com",
            date_of_joining=datetime.date.today(),
        )

    def test_check_in_and_check_out_success(self):
        check_in_dt = datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(hours=8)
        session = check_in_employee(
            employee=self.emp,
            check_in_time=check_in_dt,
            source="WEB",
        )

        self.assertIsNotNone(session.id)
        self.assertIsNone(session.check_out)

        check_out_dt = datetime.datetime.now(datetime.timezone.utc)
        completed_session = check_out_employee(
            employee=self.emp,
            check_out_time=check_out_dt,
        )

        self.assertEqual(completed_session.check_out, check_out_dt)
        self.assertGreater(completed_session.session_duration_minutes, 0)

        record = completed_session.attendance_record
        record.refresh_from_db()
        self.assertEqual(record.status, AttendanceStatus.PRESENT)

    def test_duplicate_check_in_raises_error(self):
        check_in_employee(employee=self.emp)
        with self.assertRaises(AttendanceCheckInError):
            check_in_employee(employee=self.emp)

    def test_check_out_without_check_in_raises_error(self):
        with self.assertRaises(AttendanceCheckOutError):
            check_out_employee(employee=self.emp)
