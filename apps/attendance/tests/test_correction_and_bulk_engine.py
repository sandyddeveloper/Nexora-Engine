"""Unit tests for Attendance Correction Request and Bulk Import Engines."""

import datetime
from decimal import Decimal
from django.test import TestCase

from apps.attendance.models import AttendanceStatus, CorrectionStatus
from apps.attendance.services import (
    bulk_import_attendance,
    create_attendance_policy,
    create_attendance_record,
    process_attendance_correction,
    submit_attendance_correction,
)
from apps.employees.services import create_employee
from apps.organizations.services import (
    create_branch,
    create_department,
    create_designation,
    create_organization,
)


class CorrectionAndBulkEngineTests(TestCase):
    """Test suite for attendance correction submission/approval and bulk import."""

    def setUp(self):
        self.org = create_organization(name="Bulk Correction Org")
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
            first_name="Corr",
            last_name="Worker",
            official_email="corr@corrtest.com",
            date_of_joining=datetime.date.today(),
        )

    def test_submit_and_approve_attendance_correction(self):
        today = datetime.date.today()
        record = create_attendance_record(
            employee=self.emp,
            attendance_date=today,
            status=AttendanceStatus.ABSENT,
        )

        correction = submit_attendance_correction(
            record=record,
            requested_by=self.emp,
            requested_status=AttendanceStatus.PRESENT,
            reason="System punch missing on client site.",
        )

        self.assertEqual(correction.status, CorrectionStatus.PENDING)

        processed = process_attendance_correction(
            correction_request=correction,
            approve=True,
            processed_by_id="mgr-123",
        )

        self.assertEqual(processed.status, CorrectionStatus.APPROVED)
        record.refresh_from_db()
        self.assertEqual(record.status, AttendanceStatus.PRESENT)

    def test_bulk_import_attendance_records(self):
        today = datetime.date.today() - datetime.timedelta(days=1)
        res = bulk_import_attendance(
            organization=self.org,
            records_data=[
                {
                    "employee_id": str(self.emp.id),
                    "attendance_date": today,
                    "status": AttendanceStatus.PRESENT,
                    "working_hours": Decimal("8.00"),
                }
            ],
        )

        self.assertEqual(res["created_count"], 1)
        self.assertEqual(len(res["errors"]), 0)
