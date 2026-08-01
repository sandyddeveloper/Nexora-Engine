"""Unit tests for Payslip, Salary Distribution & Employee Compensation Engine."""

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
from apps.payroll.enums import AdjustmentCategory, CalculationType, DistributionMethod, PayFrequency, PayslipStatus
from apps.payroll.exceptions import PayrollValidationError


class PayslipAndCompensationEngineTestCase(TestCase):
    """Test suite for Payslips, Salary Distribution, Retroactive Adjustments, and Compensation History."""

    @classmethod
    def setUpTestData(cls):
        cls.org = create_organization(name="Compensation Corp")
        cls.branch = create_branch(organization=cls.org, code="CMAIN", name="Comp Branch")
        cls.dept = create_department(organization=cls.org, branch=cls.branch, code="CDEPT", name="Comp Dept")
        cls.desg = create_designation(organization=cls.org, department=cls.dept, code="CDESG", name="Comp Desg")

        cls.user = create_user(email="compadmin@compensationcorp.com", password="SecurePassword123!")

        cls.approver = create_employee(
            organization=cls.org,
            branch=cls.branch,
            department=cls.dept,
            designation=cls.desg,
            first_name="Finance",
            last_name="Head",
            official_email="fhead@compensationcorp.com",
            date_of_joining=date(2023, 1, 1),
        )

        cls.emp = create_employee(
            organization=cls.org,
            branch=cls.branch,
            department=cls.dept,
            designation=cls.desg,
            first_name="Emma",
            last_name="Payee",
            official_email="emma@compensationcorp.com",
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
            name="August 2026 Comp Cycle",
            frequency=PayFrequency.MONTHLY,
            start_date=today,
            end_date=today + timedelta(days=30),
            cutoff_date=today + timedelta(days=25),
            processing_date=today + timedelta(days=28),
            payment_date=today + timedelta(days=30),
        )

        # Run & Finalize
        cls.payroll_run = services.create_payroll_run(organization=cls.org, payroll_cycle=cls.cycle, name="August 2026 Comp Run")
        services.calculate_payroll_run(payroll_run=cls.payroll_run)
        services.validate_payroll_run(payroll_run=cls.payroll_run)
        services.approve_payroll_run(payroll_run=cls.payroll_run, approver=cls.approver)
        services.finalize_payroll_run(payroll_run=cls.payroll_run)

    def setUp(self):
        self.client = APIClient()
        self.client.force_authenticate(user=self.user)

    def test_generate_and_regenerate_payslips(self):
        """Generate payslips from finalized run and test versioned regeneration."""
        payslips = services.generate_payslips_for_run(payroll_run=self.payroll_run)
        self.assertGreaterEqual(len(payslips), 1)

        ps = payslips[0]
        self.assertEqual(ps.version, 1)
        self.assertEqual(ps.status, PayslipStatus.PUBLISHED)
        self.assertGreater(ps.net_salary, Decimal("0.00"))

        # Component breakup
        self.assertGreaterEqual(ps.components.count(), 1)

        # Regenerate
        regen = services.regenerate_payslip(payslip=ps, reason="Adjustment correction")
        self.assertEqual(regen.version, 2)

    def test_create_salary_distribution(self):
        """Schedule salary disbursement batch for finalized run."""
        dist = services.create_salary_distribution(
            payroll_run=self.payroll_run, method=DistributionMethod.BANK_TRANSFER, scheduled_date=date.today()
        )
        self.assertEqual(dist.method, DistributionMethod.BANK_TRANSFER)
        self.assertEqual(dist.total_amount, self.payroll_run.total_net)

    def test_retroactive_adjustment(self):
        """Create arrears and recovery adjustment records."""
        adj = services.create_retroactive_adjustment(
            employee=self.emp,
            category=AdjustmentCategory.ARREARS,
            amount=Decimal("5000.00"),
            effective_date=date.today(),
            reason="Performance Incentive Arrears",
        )
        self.assertEqual(adj.category, AdjustmentCategory.ARREARS)
        self.assertFalse(adj.is_processed)

    def test_compensation_history(self):
        """Verify compensation history snapshot recording."""
        history = selectors.get_employee_compensation_history(employee_id=self.emp.id)
        self.assertGreaterEqual(history.count(), 1)
        first_entry = history.first()
        self.assertEqual(first_entry.annual_ctc, Decimal("1200000.00"))

    def test_export_payslip_csv(self):
        """Generate CSV export content string for a payslip."""
        payslips = services.generate_payslips_for_run(payroll_run=self.payroll_run)
        csv_text = services.export_payslip_csv(payslip=payslips[0])
        self.assertIn("PAYSLIP REPORT", csv_text)
        self.assertIn(self.emp.employee_id, csv_text)

    def test_payslip_api_views(self):
        """Test REST APIView endpoints for payslips, distributions, adjustments, and compensation."""
        res_gen = self.client.post(
            "/api/v1/payroll/payslips/generate/",
            {"payroll_run_id": str(self.payroll_run.id)},
            format="json",
        )
        self.assertEqual(res_gen.status_code, 201)

        ps_id = res_gen.data["data"][0]["id"]

        res_ess = self.client.get(f"/api/v1/payroll/payslips/ess/?employee_id={self.emp.id}")
        self.assertEqual(res_ess.status_code, 200)

        res_detail = self.client.get(f"/api/v1/payroll/payslips/{ps_id}/")
        self.assertEqual(res_detail.status_code, 200)

        res_dl = self.client.get(f"/api/v1/payroll/payslips/{ps_id}/download/")
        self.assertEqual(res_dl.status_code, 200)
        self.assertEqual(res_dl["Content-Type"], "text/csv")

        res_dist = self.client.post(
            "/api/v1/payroll/distributions/",
            {
                "payroll_run_id": str(self.payroll_run.id),
                "method": "BANK_TRANSFER",
                "scheduled_date": date.today().isoformat(),
            },
            format="json",
        )
        self.assertEqual(res_dist.status_code, 201)

        res_retro = self.client.post(
            "/api/v1/payroll/retroactive-adjustments/",
            {
                "employee_id": str(self.emp.id),
                "category": "ARREARS",
                "amount": 2500.0,
                "effective_date": date.today().isoformat(),
                "reason": "Overtime Arrears",
            },
            format="json",
        )
        self.assertEqual(res_retro.status_code, 201)

        res_comp = self.client.get(f"/api/v1/payroll/compensation/history/?employee_id={self.emp.id}")
        self.assertEqual(res_comp.status_code, 200)
