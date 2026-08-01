"""Unit tests for Enterprise Time Tracking, Timesheet & Worklog Engine."""

from datetime import date, timedelta
from decimal import Decimal
from django.test import TestCase
from rest_framework.test import APIClient

from apps.accounts.services import create_user
from apps.employees.services import create_employee
from apps.organizations.services import (
    create_branch,
    create_department,
    create_designation,
    create_organization,
)

from apps.projects import selectors, services
from apps.projects.enums import BillableType, TimesheetStatus
from apps.projects.exceptions import ProjectValidationError


class TimeTrackingAndTimesheetEngineTestCase(TestCase):
    """Test suite for Timers, Worklogs, Timesheets, Approvals, Validations, and Productivity Metrics."""

    @classmethod
    def setUpTestData(cls):
        cls.org = create_organization(name="Time Tech Enterprise")
        cls.branch = create_branch(organization=cls.org, code="TMHQ", name="Time HQ")
        cls.dept = create_department(organization=cls.org, branch=cls.branch, code="TMENG", name="Engineering")
        cls.desg = create_designation(organization=cls.org, department=cls.dept, code="TMSENG", name="Senior Dev")

        cls.user_dev = create_user(email="devtime@timetech.com", password="SecurePassword123!")
        cls.user_mgr = create_user(email="mgrtime@timetech.com", password="SecurePassword123!")

        cls.owner = create_employee(
            organization=cls.org,
            branch=cls.branch,
            department=cls.dept,
            designation=cls.desg,
            first_name="Terry",
            last_name="Owner",
            official_email="towner@timetech.com",
            date_of_joining=date(2023, 1, 1),
        )

        cls.dev = create_employee(
            organization=cls.org,
            branch=cls.branch,
            department=cls.dept,
            designation=cls.desg,
            user=cls.user_dev,
            first_name="David",
            last_name="Developer",
            official_email="ddev@timetech.com",
            date_of_joining=date(2024, 1, 1),
        )

        cls.manager = create_employee(
            organization=cls.org,
            branch=cls.branch,
            department=cls.dept,
            designation=cls.desg,
            user=cls.user_mgr,
            first_name="Mary",
            last_name="Manager",
            official_email="mmanager@timetech.com",
            date_of_joining=date(2023, 6, 1),
        )

        cls.project = services.create_project(
            organization=cls.org,
            owner=cls.owner,
            manager=cls.manager,
            code="PRJ-TIME-01",
            name="Time Engine Project",
        )
        services.activate_project(project=cls.project)

        cls.task = services.create_task(
            project=cls.project,
            reporter=cls.owner,
            code="TM-101",
            title="Backend Time Module Implementation",
            estimated_hours=Decimal("40.00"),
        )

    def setUp(self):
        self.client = APIClient()
        self.client.force_authenticate(user=self.user_dev)

    def test_live_timer_start_stop_flow(self):
        """Start timer, enforce single running timer, and stop timer."""
        # Start Timer
        entry = services.start_timer(employee=self.dev, task=self.task, notes="Coding timer")
        self.assertTrue(entry.is_timer_running)

        # Verify active timer selector
        active = selectors.get_active_timer(employee_id=self.dev.id)
        self.assertIsNotNone(active)
        self.assertEqual(active.id, entry.id)

        # Enforce single active timer rule
        with self.assertRaises(ProjectValidationError):
            services.start_timer(employee=self.dev, task=self.task, notes="Second timer")

        # Stop Timer
        stopped = services.stop_timer(entry=entry)
        self.assertFalse(stopped.is_timer_running)
        self.assertIsNotNone(stopped.end_time)

    def test_manual_worklog_and_max_daily_hours_validation(self):
        """Log manual worklogs and enforce max 24 hours daily limit."""
        today = date.today()
        log1 = services.create_manual_worklog(
            employee=self.dev,
            task=self.task,
            date_val=today,
            hours=Decimal("10.00"),
            notes="Morning session",
        )
        self.assertEqual(log1.hours, Decimal("10.00"))

        # Verify Task actual hours accumulation
        self.task.refresh_from_db()
        self.assertEqual(self.task.actual_hours, Decimal("10.00"))

        # Log 10 more hours (total 20h - OK)
        services.create_manual_worklog(employee=self.dev, task=self.task, date_val=today, hours=Decimal("10.00"))

        # Attempt to log 5 more hours (total 25h > 24h limit - Should fail)
        with self.assertRaises(ProjectValidationError):
            services.create_manual_worklog(employee=self.dev, task=self.task, date_val=today, hours=Decimal("5.00"))

    def test_timesheet_submission_approval_and_rejection(self):
        """Submit weekly timesheet, approve timesheet, and lock worklogs."""
        today = date.today()
        services.create_manual_worklog(
            employee=self.dev,
            task=self.task,
            date_val=today,
            hours=Decimal("8.00"),
            billable_type=BillableType.BILLABLE,
        )

        # Submit Timesheet
        ts = services.submit_timesheet(
            employee=self.dev,
            period_type="WEEKLY",
            start_date=today - timedelta(days=3),
            end_date=today + timedelta(days=3),
            project=self.project,
            user_id=str(self.user_dev.id),
        )
        self.assertEqual(ts.status, TimesheetStatus.SUBMITTED)
        self.assertEqual(ts.total_hours, Decimal("8.00"))

        # Approve Timesheet
        approved = services.approve_timesheet(timesheet=ts, approver=self.manager, user_id=str(self.user_mgr.id))
        self.assertEqual(approved.status, TimesheetStatus.APPROVED)

        # Check worklog is locked and approved
        entry = selectors.list_employee_time_entries(employee_id=self.dev.id).first()
        self.assertTrue(entry.is_approved)
        self.assertTrue(entry.is_locked)

    def test_productivity_metrics_calculation(self):
        """Calculate employee productivity and utilization rate."""
        today = date.today()
        services.create_manual_worklog(
            employee=self.dev,
            task=self.task,
            date_val=today,
            hours=Decimal("6.00"),
            billable_type=BillableType.BILLABLE,
        )
        services.create_manual_worklog(
            employee=self.dev,
            task=self.task,
            date_val=today,
            hours=Decimal("2.00"),
            billable_type=BillableType.NON_BILLABLE,
        )

        metrics = selectors.calculate_employee_productivity(employee_id=self.dev.id, start_date=today, end_date=today)
        self.assertEqual(metrics["total_hours"], 8.0)
        self.assertEqual(metrics["billable_hours"], 6.0)
        self.assertEqual(metrics["utilization_rate"], 75.0)

    def test_time_tracking_api_endpoints(self):
        """Test REST APIView endpoints for time tracking, worklogs, timesheets, and productivity."""
        today = date.today()

        # Start Timer API
        res_start = self.client.post(
            "/api/v1/projects/time/start/",
            {
                "task_id": str(self.task.id),
                "notes": "API Timer",
            },
            format="json",
        )
        self.assertEqual(res_start.status_code, 201)

        # Stop Timer API
        res_stop = self.client.post("/api/v1/projects/time/stop/")
        self.assertEqual(res_stop.status_code, 200)

        # Manual Worklog API
        res_wl = self.client.post(
            "/api/v1/projects/time/worklogs/",
            {
                "employee_id": str(self.dev.id),
                "task_id": str(self.task.id),
                "date": today.isoformat(),
                "hours": 4.0,
                "notes": "Manual API log",
            },
            format="json",
        )
        self.assertEqual(res_wl.status_code, 201)

        # Timesheet Submit API
        res_ts = self.client.post(
            "/api/v1/projects/timesheets/",
            {
                "employee_id": str(self.dev.id),
                "start_date": (today - timedelta(days=1)).isoformat(),
                "end_date": (today + timedelta(days=1)).isoformat(),
            },
            format="json",
        )
        self.assertEqual(res_ts.status_code, 201)
        ts_id = res_ts.data["data"]["id"]

        # Approve Timesheet API
        res_app = self.client.post(
            f"/api/v1/projects/timesheets/{ts_id}/approve/",
            {
                "approver_id": str(self.manager.id),
                "comments": "Approved via API",
            },
            format="json",
        )
        self.assertEqual(res_app.status_code, 200)

        # Productivity API
        res_prod = self.client.get(f"/api/v1/projects/productivity/?employee_id={self.dev.id}&start_date={today.isoformat()}&end_date={today.isoformat()}")
        self.assertEqual(res_prod.status_code, 200)
