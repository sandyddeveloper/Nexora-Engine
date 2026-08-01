"""Unit tests for the Attendance Analytics & KPI Calculation Engine."""

from datetime import date, datetime, timezone
from decimal import Decimal

from django.test import TestCase

from apps.accounts.models import User
from apps.employees.models import Employee, EmploymentStatus
from apps.employees.services import create_employee
from apps.organizations.models import Branch, Department, Designation, Organization, Shift, Team
from apps.organizations.services import (
    create_branch,
    create_department,
    create_designation,
    create_organization,
    create_shift,
    create_team,
)

from apps.attendance.models import AttendancePolicy, AttendanceRecord, AttendanceStatus
from apps.attendance import selectors, services
from apps.attendance.services import create_attendance_policy


class AttendanceAnalyticsEngineTestCase(TestCase):
    """Test hierarchical attendance analytics KPI calculations."""

    @classmethod
    def setUpTestData(cls):
        """Create test fixtures using domain services."""
        cls.org = create_organization(name="Analytics Corp")
        cls.branch = create_branch(organization=cls.org, code="MAIN", name="Main Branch")
        cls.dept = create_department(organization=cls.org, branch=cls.branch, code="ENG", name="Engineering")
        cls.desg = create_designation(organization=cls.org, department=cls.dept, code="ENGR", name="Engineer")
        cls.team = create_team(organization=cls.org, branch=cls.branch, department=cls.dept, code="CORE", name="Core Team")
        cls.shift = create_shift(
            organization=cls.org, code="DAY", name="Day Shift",
            start_time="09:00:00", end_time="18:00:00",
        )
        cls.policy = create_attendance_policy(
            organization=cls.org, name="Standard Policy", code="STD", is_default=True,
        )

        # Create 3 employees
        cls.emp1 = create_employee(
            organization=cls.org, branch=cls.branch, department=cls.dept,
            designation=cls.desg, team=cls.team, shift=cls.shift,
            first_name="Alice", last_name="Smith", official_email="alice@analyticscorp.com",
            official_phone="+919000000001", date_of_birth=date(1995, 6, 15),
            date_of_joining=date(2024, 1, 10),
        )

        cls.emp2 = create_employee(
            organization=cls.org, branch=cls.branch, department=cls.dept,
            designation=cls.desg, team=cls.team, shift=cls.shift,
            first_name="Bob", last_name="Jones", official_email="bob@analyticscorp.com",
            official_phone="+919000000002", date_of_birth=date(1993, 3, 22),
            date_of_joining=date(2024, 2, 1),
        )

        cls.emp3 = create_employee(
            organization=cls.org, branch=cls.branch, department=cls.dept,
            designation=cls.desg, team=cls.team, shift=cls.shift,
            first_name="Carol", last_name="White", official_email="carol@analyticscorp.com",
            official_phone="+919000000003", date_of_birth=date(1990, 11, 5),
            date_of_joining=date(2024, 3, 15),
        )

        # Create attendance records for a 5-day window
        cls.start = date(2026, 7, 21)
        cls.end = date(2026, 7, 25)

        for i in range(5):
            d = date(2026, 7, 21 + i)
            # Alice: all PRESENT
            AttendanceRecord.objects.create(
                employee=cls.emp1, organization=cls.org, branch=cls.branch, department=cls.dept,
                designation=cls.desg, team=cls.team, shift=cls.shift, policy=cls.policy,
                attendance_date=d, status=AttendanceStatus.PRESENT, working_hours=Decimal("8.00"),
                overtime_hours=Decimal("0.50"),
            )
            # Bob: mix of present and late
            status = AttendanceStatus.LATE if i % 2 == 0 else AttendanceStatus.PRESENT
            AttendanceRecord.objects.create(
                employee=cls.emp2, organization=cls.org, branch=cls.branch, department=cls.dept,
                designation=cls.desg, team=cls.team, shift=cls.shift, policy=cls.policy,
                attendance_date=d, status=status, working_hours=Decimal("7.00"),
            )
            # Carol: some absent
            status = AttendanceStatus.ABSENT if i >= 3 else AttendanceStatus.PRESENT
            AttendanceRecord.objects.create(
                employee=cls.emp3, organization=cls.org, branch=cls.branch, department=cls.dept,
                designation=cls.desg, team=cls.team, shift=cls.shift, policy=cls.policy,
                attendance_date=d, status=status,
                working_hours=Decimal("0.00") if i >= 3 else Decimal("8.00"),
            )

    def test_employee_analytics_kpi_structure(self):
        """Employee analytics returns proper KPI structure with correct counts."""
        analytics = selectors.get_employee_attendance_analytics(
            employee_id=self.emp1.id, start_date=self.start, end_date=self.end,
        )
        self.assertEqual(analytics["level"], "EMPLOYEE")
        self.assertEqual(analytics["total_records"], 5)
        self.assertEqual(analytics["present_count"], 5)
        self.assertEqual(analytics["absent_count"], 0)
        self.assertIn("attendance_score", analytics)
        self.assertIn("compliance_score", analytics)
        self.assertGreater(analytics["attendance_score"], 90)

    def test_team_analytics_aggregation(self):
        """Team analytics aggregates all team members' records."""
        analytics = selectors.get_team_attendance_analytics(
            team_id=self.team.id, start_date=self.start, end_date=self.end,
        )
        self.assertEqual(analytics["level"], "TEAM")
        self.assertEqual(analytics["total_records"], 15)  # 3 employees x 5 days
        self.assertIn("attendance_percentage", analytics)

    def test_department_analytics_aggregation(self):
        """Department analytics aggregates all department records."""
        analytics = selectors.get_department_attendance_analytics(
            department_id=self.dept.id, start_date=self.start, end_date=self.end,
        )
        self.assertEqual(analytics["level"], "DEPARTMENT")
        self.assertEqual(analytics["total_records"], 15)

    def test_branch_analytics_aggregation(self):
        """Branch analytics aggregates all branch records."""
        analytics = selectors.get_branch_attendance_analytics(
            branch_id=self.branch.id, start_date=self.start, end_date=self.end,
        )
        self.assertEqual(analytics["level"], "BRANCH")
        self.assertEqual(analytics["total_records"], 15)

    def test_organization_analytics_aggregation(self):
        """Organization analytics aggregates entire org records."""
        analytics = selectors.get_organization_attendance_analytics(
            organization_id=self.org.id, start_date=self.start, end_date=self.end,
        )
        self.assertEqual(analytics["level"], "ORGANIZATION")
        self.assertEqual(analytics["total_records"], 15)
        # Should have 2 absent (Carol) + 3 late (Bob)
        self.assertEqual(analytics["absent_count"], 2)
        self.assertEqual(analytics["late_count"], 3)

    def test_analytics_kpi_score_bounds(self):
        """Attendance and compliance scores are bounded [0, 100]."""
        analytics = selectors.get_organization_attendance_analytics(
            organization_id=self.org.id, start_date=self.start, end_date=self.end,
        )
        self.assertGreaterEqual(analytics["attendance_score"], 0)
        self.assertLessEqual(analytics["attendance_score"], 100)
        self.assertGreaterEqual(analytics["compliance_score"], 0)
        self.assertLessEqual(analytics["compliance_score"], 100)

    def test_analytics_report_service_delegates_correctly(self):
        """Service generate_attendance_analytics_report delegates to correct selector by level."""
        analytics = services.generate_attendance_analytics_report(
            organization=self.org, level="EMPLOYEE", target_id=str(self.emp1.id),
            start_date=self.start, end_date=self.end,
        )
        self.assertEqual(analytics["level"], "EMPLOYEE")
        self.assertEqual(analytics["present_count"], 5)

    def test_analytics_report_invalid_level(self):
        """Service raises AttendanceAnalyticsError for invalid level."""
        from apps.attendance.exceptions import AttendanceAnalyticsError
        with self.assertRaises(AttendanceAnalyticsError):
            services.generate_attendance_analytics_report(
                organization=self.org, level="GALAXY", target_id=str(self.org.id),
                start_date=self.start, end_date=self.end,
            )

    def test_csv_export_returns_flat_rows(self):
        """CSV export returns a list of dictionaries with expected fields."""
        rows = services.export_attendance_report_csv(
            organization_id=self.org.id, start_date=self.start, end_date=self.end,
        )
        self.assertEqual(len(rows), 15)
        first = rows[0]
        self.assertIn("employee_id", first)
        self.assertIn("attendance_date", first)
        self.assertIn("status", first)
        self.assertIn("working_hours", first)
