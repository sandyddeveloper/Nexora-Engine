"""Unit tests for Compliance Violation detection, Executive Dashboard, and AI Foundation data engine."""

from datetime import date
from decimal import Decimal

from django.test import TestCase

from apps.employees.services import create_employee
from apps.organizations.services import (
    create_branch,
    create_department,
    create_designation,
    create_organization,
    create_shift,
    create_team,
)

from apps.attendance.models import AttendancePolicy, AttendanceRecord, AttendanceStatus
from apps.attendance import selectors
from apps.attendance.services import create_attendance_policy


class ComplianceAndDashboardEngineTestCase(TestCase):
    """Test compliance violation report, executive dashboard, and AI analytics foundation queries."""

    @classmethod
    def setUpTestData(cls):
        """Create test fixtures for compliance & dashboard testing using domain services."""
        cls.org = create_organization(name="Compliance Corp")
        cls.branch = create_branch(organization=cls.org, code="CMAIN", name="Compliance Branch")
        cls.dept = create_department(organization=cls.org, branch=cls.branch, code="OPS", name="Operations")
        cls.desg = create_designation(organization=cls.org, department=cls.dept, code="OPR", name="Operator")
        cls.team = create_team(organization=cls.org, branch=cls.branch, department=cls.dept, code="STEAM", name="Shift Team")
        cls.shift = create_shift(
            organization=cls.org, code="DAY", name="Day Shift",
            start_time="09:00:00", end_time="18:00:00",
        )
        cls.policy = create_attendance_policy(
            organization=cls.org, name="Standard Policy", code="STD", is_default=True,
        )

        cls.emp = create_employee(
            organization=cls.org, branch=cls.branch, department=cls.dept,
            designation=cls.desg, team=cls.team, shift=cls.shift,
            first_name="Dave", last_name="Miller", official_email="dave@compliancecorp.com",
            official_phone="+919000000004", date_of_birth=date(1992, 8, 10),
            date_of_joining=date(2024, 1, 1),
        )

        # Create violations: LATE, EARLY_EXIT, Excessive overtime (>4 hrs), Excessive hours (>12 hrs)
        cls.d1 = date(2026, 7, 20)
        cls.d2 = date(2026, 7, 21)
        cls.d3 = date(2026, 7, 22)

        # Record 1: Late violation
        AttendanceRecord.objects.create(
            employee=cls.emp, organization=cls.org, branch=cls.branch, department=cls.dept,
            designation=cls.desg, team=cls.team, shift=cls.shift, policy=cls.policy,
            attendance_date=cls.d1, status=AttendanceStatus.LATE, working_hours=Decimal("7.50"),
        )
        # Record 2: Early Exit violation
        AttendanceRecord.objects.create(
            employee=cls.emp, organization=cls.org, branch=cls.branch, department=cls.dept,
            designation=cls.desg, team=cls.team, shift=cls.shift, policy=cls.policy,
            attendance_date=cls.d2, status=AttendanceStatus.EARLY_EXIT, working_hours=Decimal("6.00"),
        )
        # Record 3: Excessive Overtime & Excessive Hours violation
        AttendanceRecord.objects.create(
            employee=cls.emp, organization=cls.org, branch=cls.branch, department=cls.dept,
            designation=cls.desg, team=cls.team, shift=cls.shift, policy=cls.policy,
            attendance_date=cls.d3, status=AttendanceStatus.PRESENT, working_hours=Decimal("13.00"),
            overtime_hours=Decimal("5.00"),
        )

    def test_compliance_violations_detection(self):
        """Compliance violations selector correctly categorizes late, early exit, overtime, and excessive hours."""
        report = selectors.get_compliance_violations(
            organization_id=self.org.id, start_date=self.d1, end_date=self.d3,
        )
        self.assertEqual(report["organization_id"], str(self.org.id))
        self.assertEqual(report["total_records"], 3)
        self.assertGreater(report["total_violations"], 0)
        self.assertEqual(report["late_arrival_violations"]["count"], 1)
        self.assertEqual(report["early_exit_violations"]["count"], 1)
        self.assertEqual(report["excessive_overtime_violations"]["count"], 1)
        self.assertEqual(report["excessive_hours_violations"]["count"], 1)
        self.assertIn("compliance_rate", report)

    def test_executive_dashboard_payload_structure(self):
        """Executive dashboard selector returns today snapshot, monthly, weekly, and daily trend components."""
        dashboard = selectors.get_dashboard_analytics(
            organization_id=self.org.id, user_role="EXECUTIVE",
        )
        self.assertEqual(dashboard["organization_id"], str(self.org.id))
        self.assertEqual(dashboard["dashboard_role"], "EXECUTIVE")
        self.assertIn("today_snapshot", dashboard)
        self.assertIn("monthly_kpis", dashboard)
        self.assertIn("weekly_kpis", dashboard)
        self.assertIn("daily_trend", dashboard)
        self.assertEqual(len(dashboard["daily_trend"]), 7)

    def test_ai_analytics_foundation_vectors(self):
        """AI analytics foundation data returns structured employee behavioral vectors and anomaly signals."""
        ai_data = selectors.get_ai_analytics_foundation_data(
            organization_id=self.org.id, start_date=self.d1, end_date=self.d3,
        )
        self.assertEqual(ai_data["organization_id"], str(self.org.id))
        self.assertIn("employee_behavioral_vectors", ai_data)
        self.assertIn("burnout_risk_signals", ai_data)
        self.assertIn("absenteeism_patterns", ai_data)
        self.assertGreaterEqual(ai_data["total_employees_analyzed"], 1)
