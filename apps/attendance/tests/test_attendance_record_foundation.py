"""Unit tests for Attendance Record Foundation, Audit Events, and Locks."""

import datetime
from decimal import Decimal
from django.test import TestCase

from apps.attendance.exceptions import AttendanceDuplicateError, AttendanceLockedError
from apps.attendance.models import AttendanceStatus
from apps.attendance.services import (
    create_attendance_policy,
    create_attendance_record,
    lock_attendance_records,
    update_attendance_record,
)
from apps.employees.services import create_employee
from apps.organizations.services import (
    create_branch,
    create_department,
    create_designation,
    create_organization,
)


class AttendanceRecordFoundationTests(TestCase):
    """Test suite for core AttendanceRecord creation, duplicate prevention, and lock protection."""

    def setUp(self):
        self.org = create_organization(name="Att Record Org")
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
            first_name="Jane",
            last_name="Doe",
            official_email="jane@attrecord.com",
            date_of_joining=datetime.date.today(),
        )

    def test_create_attendance_record_success(self):
        today = datetime.date.today()
        record = create_attendance_record(
            employee=self.emp,
            attendance_date=today,
            status=AttendanceStatus.PRESENT,
            working_hours=Decimal("8.00"),
        )

        self.assertIsNotNone(record.id)
        self.assertEqual(record.status, AttendanceStatus.PRESENT)
        self.assertEqual(record.policy, self.policy)

    def test_create_duplicate_attendance_record_raises_error(self):
        today = datetime.date.today()
        create_attendance_record(
            employee=self.emp,
            attendance_date=today,
            status=AttendanceStatus.PRESENT,
        )

        with self.assertRaises(AttendanceDuplicateError):
            create_attendance_record(
                employee=self.emp,
                attendance_date=today,
                status=AttendanceStatus.LATE,
            )

    def test_lock_attendance_records_prevents_updates(self):
        today = datetime.date.today()
        record = create_attendance_record(
            employee=self.emp,
            attendance_date=today,
            status=AttendanceStatus.PRESENT,
        )

        lock_attendance_records(organization_id=self.org.id, lock_up_to_date=today)
        record.refresh_from_db()
        self.assertTrue(record.is_locked)

        with self.assertRaises(AttendanceLockedError):
            update_attendance_record(record=record, status=AttendanceStatus.LATE)
