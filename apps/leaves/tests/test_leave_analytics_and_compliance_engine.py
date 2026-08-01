"""Unit tests for Leave Analytics & Compliance Engine."""

from datetime import date, timedelta
from decimal import Decimal
from django.test import TestCase
from rest_framework.test import APIClient

from apps.accounts.services import create_user
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


def get_next_weekday(start_date: date, offset_weeks: int = 1) -> date:
    """Helper to return a guaranteed Monday date offset by N weeks."""
    d = start_date + timedelta(weeks=offset_weeks)
    while d.weekday() != 0:
        d += timedelta(days=1)
    return d


class LeaveAnalyticsAndComplianceEngineTestCase(TestCase):
    """Test suite for Leave Analytics, Compliance Risk Audits, Dashboards, and CSV Export Engine."""

    @classmethod
    def setUpTestData(cls):
        cls.org = create_organization(name="Analytics Corp")
        cls.att_pol = create_attendance_policy(
            organization=cls.org, name="Default Attendance Policy", code="ATT_DEF", is_default=True
        )
        cls.branch = create_branch(organization=cls.org, code="AMAIN", name="Analytics Branch")
        cls.dept = create_department(organization=cls.org, branch=cls.branch, code="ADEPT", name="Analytics Dept")
        cls.desg = create_designation(organization=cls.org, department=cls.dept, code="ADESG", name="Analytics Desg")

        cls.user = create_user(email="hradmin@analyticscorp.com", password="SecurePassword123!")

        cls.manager = create_employee(
            organization=cls.org,
            branch=cls.branch,
            department=cls.dept,
            designation=cls.desg,
            first_name="Manager",
            last_name="Boss",
            official_email="mboss@analyticscorp.com",
            date_of_joining=date(2023, 1, 1),
        )

        cls.emp = create_employee(
            organization=cls.org,
            branch=cls.branch,
            department=cls.dept,
            designation=cls.desg,
            first_name="Bob",
            last_name="Analyst",
            official_email="bob@analyticscorp.com",
            reporting_manager=cls.manager,
            date_of_joining=date(2024, 1, 1),
        )

        cls.lt = services.create_leave_type(organization=cls.org, name="Casual Leave", code="CL")
        cls.pol = services.create_leave_policy(
            organization=cls.org,
            leave_type=cls.lt,
            name="CL Policy",
            code="CL_POL",
            max_leave_per_year=Decimal("12.00"),
            notice_period_days=0,
            attachment_required_threshold_days=10,
            is_default=True,
        )

        cls.bal = services.initialize_employee_leave_balance(
            employee=cls.emp, leave_type=cls.lt, policy=cls.pol, opening_balance=Decimal("10.00")
        )

    def setUp(self):
        self.client = APIClient()
        self.client.force_authenticate(user=self.user)

    def test_employee_leave_analytics(self):
        """Verify employee-level leave analytics calculation."""
        mon = get_next_weekday(date.today(), offset_weeks=1)
        req = services.apply_leave_request(
            employee=self.emp, leave_type=self.lt, start_date=mon, end_date=mon, reason="Personal"
        )
        services.approve_leave_request(leave_request=req, approver=self.manager)

        data = selectors.get_employee_leave_analytics(employee_id=self.emp.id)
        self.assertEqual(data["employee_id"], str(self.emp.id))
        self.assertEqual(data["total_requests_applied"], 1)
        self.assertEqual(data["approved_requests_count"], 1)
        self.assertEqual(data["total_days_approved"], 1.0)
        self.assertEqual(len(data["balances"]), 1)

    def test_organization_leave_analytics_and_kpis(self):
        """Verify organization-wide leave analytics and KPI calculations."""
        mon = get_next_weekday(date.today(), offset_weeks=2)
        req = services.apply_leave_request(
            employee=self.emp, leave_type=self.lt, start_date=mon, end_date=mon, reason="Personal"
        )
        services.approve_leave_request(leave_request=req, approver=self.manager)

        start = date(date.today().year, 1, 1)
        end = date(date.today().year, 12, 31)

        org_data = selectors.get_organization_leave_analytics(
            organization_id=self.org.id, start_date=start, end_date=end
        )
        self.assertEqual(org_data["organization_id"], str(self.org.id))
        self.assertGreaterEqual(org_data["total_active_employees"], 2)

        kpis = selectors.calculate_leave_kpis(organization_id=self.org.id, start_date=start, end_date=end)
        self.assertIn("utilization_percentage", kpis)
        self.assertIn("rejection_percentage", kpis)
        self.assertIn("organization_availability_percentage", kpis)

    def test_leave_compliance_audit(self):
        """Verify compliance audit calculation and risk level score."""
        start = date(date.today().year, 1, 1)
        end = date(date.today().year, 12, 31)

        comp = selectors.get_leave_compliance_audit(organization_id=self.org.id, start_date=start, end_date=end)
        self.assertEqual(comp["organization_id"], str(self.org.id))
        self.assertEqual(comp["compliance_score"], 100.0)
        self.assertEqual(comp["risk_level"], "LOW")
        self.assertEqual(comp["total_policy_violations"], 0)

    def test_executive_and_manager_dashboards(self):
        """Verify Executive and Manager Dashboard payload structures."""
        exec_dash = selectors.get_executive_leave_dashboard(organization_id=self.org.id)
        self.assertEqual(exec_dash["organization_id"], str(self.org.id))
        self.assertIn("kpis", exec_dash)
        self.assertIn("compliance", exec_dash)

        mgr_dash = selectors.get_manager_leave_dashboard(manager_id=self.manager.id)
        self.assertEqual(mgr_dash["manager_id"], str(self.manager.id))
        self.assertGreaterEqual(mgr_dash["total_direct_reports"], 1)

    def test_forecast_foundation_data(self):
        """Verify AI forecast foundation data structure."""
        forecast = selectors.get_leave_forecast_data(organization_id=self.org.id)
        self.assertEqual(forecast["forecast_model"], "SEASONAL_TIME_SERIES_V1")
        self.assertIn("predicted_high_demand_months", forecast)

    def test_generate_csv_export(self):
        """Verify CSV report generation service."""
        start = date(date.today().year, 1, 1)
        end = date(date.today().year, 12, 31)

        csv_text = services.generate_leave_export_csv(
            organization=self.org, report_type="UTILIZATION", start_date=start, end_date=end
        )
        self.assertIn("KPI Metric", csv_text)
        self.assertIn("Utilization %", csv_text)

    def test_analytics_api_views(self):
        """Verify APIView endpoints for leave analytics and dashboards."""
        res_emp = self.client.get(f"/api/v1/leaves/analytics/employee/?employee_id={self.emp.id}")
        self.assertEqual(res_emp.status_code, 200)

        start = date(date.today().year, 1, 1).isoformat()
        end = date(date.today().year, 12, 31).isoformat()

        res_org = self.client.get(
            f"/api/v1/leaves/analytics/organization/?organization_id={self.org.id}&start_date={start}&end_date={end}"
        )
        self.assertEqual(res_org.status_code, 200)

        res_comp = self.client.get(
            f"/api/v1/leaves/analytics/compliance/?organization_id={self.org.id}&start_date={start}&end_date={end}"
        )
        self.assertEqual(res_comp.status_code, 200)

        res_kpi = self.client.get(
            f"/api/v1/leaves/analytics/kpis/?organization_id={self.org.id}&start_date={start}&end_date={end}"
        )
        self.assertEqual(res_kpi.status_code, 200)

        res_forecast = self.client.get(f"/api/v1/leaves/analytics/forecast/?organization_id={self.org.id}")
        self.assertEqual(res_forecast.status_code, 200)

        res_exec = self.client.get(f"/api/v1/leaves/dashboards/executive/?organization_id={self.org.id}")
        self.assertEqual(res_exec.status_code, 200)

        res_mgr = self.client.get(f"/api/v1/leaves/dashboards/manager/?manager_id={self.manager.id}")
        self.assertEqual(res_mgr.status_code, 200)

        res_export = self.client.post(
            "/api/v1/leaves/reports/export/",
            {
                "organization_id": str(self.org.id),
                "report_type": "UTILIZATION",
                "start_date": start,
                "end_date": end,
            },
            format="json",
        )
        self.assertEqual(res_export.status_code, 200)
        self.assertEqual(res_export["Content-Type"], "text/csv")
