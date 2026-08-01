"""Unit tests for Leave Request & Approval Workflow Engine."""

from datetime import date, timedelta
from decimal import Decimal
from django.test import TestCase

from apps.attendance.models import AttendanceRecord, AttendanceStatus
from apps.attendance.services import create_attendance_policy
from apps.employees.services import create_employee
from apps.organizations.services import (
    create_branch,
    create_department,
    create_designation,
    create_organization,
)

from apps.leaves import selectors, services
from apps.leaves.enums import LeaveRequestStatus
from apps.leaves.exceptions import LeavePolicyValidationError


def get_next_weekday(start_date: date, offset_weeks: int = 1) -> date:
    """Helper to return a guaranteed Monday date offset by N weeks."""
    d = start_date + timedelta(weeks=offset_weeks)
    while d.weekday() != 0:  # 0 is Monday
        d += timedelta(days=1)
    return d


class LeaveRequestAndWorkflowEngineTestCase(TestCase):
    """Test suite for Leave Request application, multi-level approval, rejection, cancellation, and calendar."""

    @classmethod
    def setUpTestData(cls):
        cls.org = create_organization(name="Workflow Corp")
        cls.att_pol = create_attendance_policy(organization=cls.org, name="Default Attendance Policy", code="ATT_DEF", is_default=True)
        cls.branch = create_branch(organization=cls.org, code="WMAIN", name="Workflow Branch")
        cls.dept = create_department(organization=cls.org, branch=cls.branch, code="WDEPT", name="Workflow Dept")
        cls.desg = create_designation(organization=cls.org, department=cls.dept, code="WDESG", name="Workflow Desg")

        cls.manager = create_employee(
            organization=cls.org, branch=cls.branch, department=cls.dept, designation=cls.desg,
            first_name="Manager", last_name="Boss", official_email="manager@wfcorp.com",
            date_of_joining=date(2023, 1, 1),
        )

        cls.emp = create_employee(
            organization=cls.org, branch=cls.branch, department=cls.dept, designation=cls.desg,
            first_name="Alice", last_name="Worker", official_email="alice@wfcorp.com",
            reporting_manager=cls.manager, date_of_joining=date(2024, 1, 1),
        )

        cls.lt = services.create_leave_type(organization=cls.org, name="Casual Leave", code="CL")
        cls.pol = services.create_leave_policy(
            organization=cls.org, leave_type=cls.lt, name="CL Policy", code="CL_POL",
            max_leave_per_year=Decimal("12.00"), notice_period_days=0, attachment_required_threshold_days=10, is_default=True,
        )

        cls.bal = services.initialize_employee_leave_balance(
            employee=cls.emp, leave_type=cls.lt, policy=cls.pol, opening_balance=Decimal("10.00"),
        )

    def test_apply_leave_request_success(self):
        """Apply for a valid leave request and auto-assign reporting manager as approver."""
        mon = get_next_weekday(date.today(), offset_weeks=1)
        tue = mon + timedelta(days=1)

        req = services.apply_leave_request(
            employee=self.emp,
            leave_type=self.lt,
            start_date=mon,
            end_date=tue,
            reason="Personal work",
        )
        self.assertEqual(req.status, LeaveRequestStatus.SUBMITTED)
        self.assertEqual(req.approver, self.manager)

    def test_apply_overlapping_leave_request_raises_error(self):
        """Applying for overlapping leave dates raises LeavePolicyValidationError."""
        mon = get_next_weekday(date.today(), offset_weeks=2)
        tue = mon + timedelta(days=1)

        services.apply_leave_request(
            employee=self.emp, leave_type=self.lt, start_date=mon, end_date=tue, reason="Vacation",
        )

        with self.assertRaises(LeavePolicyValidationError):
            services.apply_leave_request(
                employee=self.emp, leave_type=self.lt, start_date=mon, end_date=tue, reason="Overlap",
            )

    def test_approve_leave_request_deducts_balance_and_syncs_attendance(self):
        """Approving leave request deducts LeaveBalance and marks AttendanceRecord as LEAVE."""
        mon = get_next_weekday(date.today(), offset_weeks=3)

        req = services.apply_leave_request(
            employee=self.emp, leave_type=self.lt, start_date=mon, end_date=mon, reason="Dentist appointment",
        )

        approved_req = services.approve_leave_request(leave_request=req, approver=self.manager, comments="Approved")
        self.assertEqual(approved_req.status, LeaveRequestStatus.APPROVED)

        self.bal.refresh_from_db()
        self.assertEqual(self.bal.used_balance, Decimal("1.00"))
        self.assertEqual(self.bal.available_balance, Decimal("9.00"))

        att = AttendanceRecord.objects.get(employee=self.emp, attendance_date=mon)
        self.assertEqual(att.status, AttendanceStatus.LEAVE)

    def test_cancel_approved_leave_restores_balance(self):
        """Cancelling an approved leave request restores LeaveBalance and updates attendance."""
        mon = get_next_weekday(date.today(), offset_weeks=4)

        req = services.apply_leave_request(
            employee=self.emp, leave_type=self.lt, start_date=mon, end_date=mon, reason="Trip",
        )
        services.approve_leave_request(leave_request=req, approver=self.manager)

        self.bal.refresh_from_db()
        self.assertEqual(self.bal.available_balance, Decimal("9.00"))

        cancelled_req = services.cancel_leave_request(leave_request=req, cancellation_reason="Trip cancelled")
        self.assertEqual(cancelled_req.status, LeaveRequestStatus.CANCELLED)

        self.bal.refresh_from_db()
        self.assertEqual(self.bal.available_balance, Decimal("10.00"))

    def test_reject_leave_request(self):
        """Rejecting a leave request sets status to REJECTED with rejection reason."""
        mon = get_next_weekday(date.today(), offset_weeks=5)

        req = services.apply_leave_request(
            employee=self.emp, leave_type=self.lt, start_date=mon, end_date=mon, reason="Conference",
        )
        rejected_req = services.reject_leave_request(leave_request=req, approver=self.manager, rejection_reason="Critical project deadline")
        self.assertEqual(rejected_req.status, LeaveRequestStatus.REJECTED)
        self.assertEqual(rejected_req.rejection_reason, "Critical project deadline")

    def test_withdraw_leave_request(self):
        """Applicant can withdraw a submitted request before approval."""
        mon = get_next_weekday(date.today(), offset_weeks=6)

        req = services.apply_leave_request(
            employee=self.emp, leave_type=self.lt, start_date=mon, end_date=mon, reason="Personal",
        )
        withdrawn_req = services.withdraw_leave_request(leave_request=req)
        self.assertEqual(withdrawn_req.status, LeaveRequestStatus.WITHDRAWN)

    def test_approval_delegation(self):
        """Creating an approval delegation routes new requests to delegatee approver."""
        backup_manager = create_employee(
            organization=self.org, branch=self.branch, department=self.dept, designation=self.desg,
            first_name="Backup", last_name="Manager", official_email="backup@wfcorp.com",
            date_of_joining=date(2023, 5, 1),
        )

        mon = get_next_weekday(date.today(), offset_weeks=7)
        fri = mon + timedelta(days=4)

        services.create_approval_delegation(
            organization=self.org,
            delegator=self.manager,
            delegatee=backup_manager,
            start_date=mon,
            end_date=fri,
            reason="Manager on vacation",
        )

        req = services.apply_leave_request(
            employee=self.emp, leave_type=self.lt, start_date=mon, end_date=mon, reason="Project break",
        )
        self.assertEqual(req.approver, backup_manager)
