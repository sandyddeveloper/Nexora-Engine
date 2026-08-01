"""Unit tests for Payroll Analytics, Executive Reporting & Workforce Cost Intelligence Engine."""

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

from apps.payroll import selectors, services
from apps.payroll.enums import AnalyticsGranularity, CalculationType, DashboardType, PayFrequency


class PayrollAnalyticsAndReportingEngineTestCase(TestCase):
    """Test suite for Payroll Analytics, Workforce Cost Intelligence, KPIs, Dashboards, and Reports."""

    @classmethod
    def setUpTestData(cls):
        cls.org = create_organization(name="Analytics Corp")
        cls.branch = create_branch(organization=cls.org, code="AMAIN", name="Analytics Branch")
        cls.dept = create_department(organization=cls.org, branch=cls.branch, code="ADEPT", name="Analytics Dept")
        cls.desg = create_designation(organization=cls.org, department=cls.dept, code="ADESG", name="Analytics Desg")

        cls.user = create_user(email="analyticsadmin@analyticscorp.com", password="SecurePassword123!")

        cls.approver = create_employee(
            organization=cls.org,
            branch=cls.branch,
            department=cls.dept,
            designation=cls.desg,
            first_name="Analytics",
            last_name="Director",
            official_email="adirector@analyticscorp.com",
            date_of_joining=date(2023, 1, 1),
        )

        cls.emp = create_employee(
            organization=cls.org,
            branch=cls.branch,
            department=cls.dept,
            designation=cls.desg,
            first_name="Grace",
            last_name="Analyst",
            official_email="grace@analyticscorp.com",
            date_of_joining=date(2024, 1, 1),
        )

        cls.basic = services.create_salary_component(
            organization=cls.org, name="Basic", code="BASIC", calculation_type=CalculationType.PERCENTAGE_OF_CTC, default_amount_percentage=Decimal("40.00")
        )

        services.assign_employee_salary_structure(
            employee=cls.emp, annual_ctc=Decimal("1200000.00"), effective_date=date(2024, 1, 1), revision_reason="Initial Offer"
        )

        today = date.today()
        cls.cycle = services.create_payroll_cycle(
            organization=cls.org,
            name="August 2026 Analytics Cycle",
            frequency=PayFrequency.MONTHLY,
            start_date=today,
            end_date=today + timedelta(days=30),
            cutoff_date=today + timedelta(days=25),
            processing_date=today + timedelta(days=28),
            payment_date=today + timedelta(days=30),
        )

        cls.payroll_run = services.create_payroll_run(organization=cls.org, payroll_cycle=cls.cycle, name="August 2026 Analytics Run")
        services.calculate_payroll_run(payroll_run=cls.payroll_run)
        services.validate_payroll_run(payroll_run=cls.payroll_run)
        services.approve_payroll_run(payroll_run=cls.payroll_run, approver=cls.approver, comments="Approved for analytics")
        services.finalize_payroll_run(payroll_run=cls.payroll_run)

    def setUp(self):
        self.client = APIClient()
        self.client.force_authenticate(user=self.user)

    def test_get_payroll_summary_analytics(self):
        """Aggregate gross, net, deductions across finalized payroll runs."""
        analytics = selectors.get_payroll_summary_analytics(organization_id=self.org.id, period_name="2026-08")
        self.assertEqual(analytics["total_runs"], 1)
        self.assertGreater(analytics["total_gross"], 0)

    def test_get_workforce_cost_intelligence(self):
        """Compute departmental headcount and cost per employee."""
        cost_data = selectors.get_workforce_cost_intelligence(organization_id=self.org.id)
        self.assertIsInstance(cost_data, list)
        self.assertGreater(len(cost_data), 0)
        self.assertEqual(cost_data[0]["department_name"], "Analytics Dept")

    def test_get_executive_kpis(self):
        """Compute executive KPIs (total cost, average salary, deduction ratio)."""
        kpis = selectors.get_executive_kpis(organization_id=self.org.id)
        self.assertIn("total_payroll_cost", kpis)
        self.assertIn("average_salary", kpis)
        self.assertEqual(kpis["payroll_completion_rate"], 100.0)

    def test_generate_payroll_analytics_snapshot(self):
        """Generate and persist periodic analytics metrics snapshot record."""
        snapshot = services.generate_payroll_analytics_snapshot(
            organization=self.org,
            period_name="2026-08",
            granularity=AnalyticsGranularity.MONTHLY,
        )
        self.assertEqual(snapshot.period_name, "2026-08")
        self.assertGreater(snapshot.total_gross, Decimal("0.00"))

    def test_generate_executive_dashboard(self):
        """Generate pre-compiled executive dashboard payload."""
        dash = services.generate_executive_dashboard(organization=self.org, dashboard_type=DashboardType.CEO)
        self.assertEqual(dash.dashboard_type, DashboardType.CEO)
        self.assertIn("kpis", dash.metrics_json)

    def test_export_payroll_register_report(self):
        """Compile CSV payroll register report export."""
        csv_output = services.export_payroll_register_report(organization=self.org, period_name="2026-08")
        self.assertIn("Organization Payroll Register Report", csv_output)
        self.assertIn(self.org.name, csv_output)

    def test_analytics_api_views(self):
        """Test REST APIView endpoints for summary, cost intelligence, KPIs, dashboards, forecast datasets, and exports."""
        res_summary = self.client.get(f"/api/v1/payroll/analytics/summary/?organization_id={self.org.id}")
        self.assertEqual(res_summary.status_code, 200)

        res_cost = self.client.get(f"/api/v1/payroll/analytics/cost-intelligence/?organization_id={self.org.id}")
        self.assertEqual(res_cost.status_code, 200)

        res_kpis = self.client.get(f"/api/v1/payroll/analytics/kpis/?organization_id={self.org.id}")
        self.assertEqual(res_kpis.status_code, 200)

        res_dash = self.client.get(f"/api/v1/payroll/analytics/dashboards/?organization_id={self.org.id}&dashboard_type=CEO")
        self.assertEqual(res_dash.status_code, 200)

        res_forecast = self.client.get(f"/api/v1/payroll/analytics/forecast-data/?organization_id={self.org.id}")
        self.assertEqual(res_forecast.status_code, 200)

        res_export = self.client.get(f"/api/v1/payroll/analytics/export/?organization_id={self.org.id}")
        self.assertEqual(res_export.status_code, 200)
        self.assertEqual(res_export["Content-Type"], "text/csv")
