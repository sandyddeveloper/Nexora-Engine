"""Unit tests for Attendance Policy Engine and Configuration Hierarchy."""

from decimal import Decimal
from django.test import TestCase

from apps.attendance.models import AttendancePolicy
from apps.attendance.services import (
    create_attendance_policy,
    set_attendance_configuration,
)
from apps.organizations.services import (
    create_branch,
    create_department,
    create_organization,
)


class AttendancePolicyTests(TestCase):
    """Test suite for Attendance Policy creation and Configuration Hierarchy resolution."""

    def setUp(self):
        self.org = create_organization(name="Policy Test Org")
        self.branch = create_branch(organization=self.org, code="BR-1", name="Branch 1")
        self.dept = create_department(organization=self.org, branch=self.branch, code="DEP-1", name="Dept 1")

    def test_create_attendance_policy(self):
        policy = create_attendance_policy(
            organization=self.org,
            name="Standard Shift Policy",
            code="STD95",
            grace_time_minutes=15,
            late_threshold_minutes=30,
            minimum_working_hours=Decimal("4.00"),
            full_day_working_hours=Decimal("8.00"),
            is_default=True,
        )

        self.assertIsNotNone(policy.id)
        self.assertTrue(policy.is_default)
        self.assertEqual(policy.code, "STD95")

    def test_set_attendance_configuration(self):
        policy = create_attendance_policy(
            organization=self.org,
            name="Branch Specific Policy",
            code="BR-POL",
            is_default=False,
        )

        cfg = set_attendance_configuration(
            organization=self.org,
            branch=self.branch,
            default_policy=policy,
            allow_future_attendance=False,
        )

        self.assertIsNotNone(cfg.id)
        self.assertEqual(cfg.default_policy, policy)
        self.assertEqual(cfg.branch, self.branch)
