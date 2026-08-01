"""Unit tests for Payroll Processing & Payroll Run Engine."""

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
from apps.payroll.enums import CalculationType, ComponentType, PayFrequency, PayrollRunStatus
from apps.payroll.exceptions import PayrollValidationError


class PayrollProcessingAndRunEngineTestCase(TestCase):
    """Test suite for Payroll Run lifecycle: Draft -> Calculate -> Validate -> Approve -> Finalize -> Lock -> Reopen -> Rollback."""

    @classmethod
    def setUpTestData(cls):
        cls.org = create_organization(name="Processing Corp")
        cls.branch = create_branch(organization=cls.org, code="RMAIN", name="Run Branch")
        cls.dept = create_department(organization=cls.org, branch=cls.branch, code="RDEPT", name="Run Dept")
        cls.desg = create_designation(organization=cls.org, department=cls.dept, code="RDESG", name="Run Desg")

        cls.user = create_user(email="payrollproc@processingcorp.com", password="SecurePassword123!")

        cls.approver = create_employee(
            organization=cls.org,
            branch=cls.branch,
            department=cls.dept,
            designation=cls.desg,
            first_name="Finance",
            last_name="Director",
            official_email="fdirector@processingcorp.com",
            date_of_joining=date(2023, 1, 1),
        )

        cls.emp1 = create_employee(
            organization=cls.org,
            branch=cls.branch,
            department=cls.dept,
            designation=cls.desg,
            first_name="Alice",
            last_name="Worker",
            official_email="alice@processingcorp.com",
            date_of_joining=date(2024, 1, 1),
        )

        cls.emp2 = create_employee(
            organization=cls.org,
            branch=cls.branch,
            department=cls.dept,
            designation=cls.desg,
            first_name="David",
            last_name="Worker",
            official_email="david@processingcorp.com",
            date_of_joining=date(2024, 1, 1),
        )

        # Components
        cls.basic = services.create_salary_component(
            organization=cls.org, name="Basic", code="BASIC", calculation_type=CalculationType.PERCENTAGE_OF_CTC, default_amount_percentage=Decimal("40.00")
        )
        cls.hra = services.create_salary_component(
            organization=cls.org, name="HRA", code="HRA", calculation_type=CalculationType.PERCENTAGE_OF_BASIC, default_amount_percentage=Decimal("50.00")
        )

        # Salary Structures
        services.assign_employee_salary_structure(
            employee=cls.emp1, annual_ctc=Decimal("1200000.00"), effective_date=date(2024, 1, 1), revision_reason="Initial"
        )
        services.assign_employee_salary_structure(
            employee=cls.emp2, annual_ctc=Decimal("600000.00"), effective_date=date(2024, 1, 1), revision_reason="Initial"
        )

        # Cycle
        today = date.today()
        cls.cycle = services.create_payroll_cycle(
            organization=cls.org,
            name="August 2026 Run Cycle",
            frequency=PayFrequency.MONTHLY,
            start_date=today,
            end_date=today + timedelta(days=30),
            cutoff_date=today + timedelta(days=25),
            processing_date=today + timedelta(days=28),
            payment_date=today + timedelta(days=30),
        )

    def setUp(self):
        self.client = APIClient()
        self.client.force_authenticate(user=self.user)

    def test_payroll_run_full_lifecycle(self):
        """Test complete payroll run lifecycle from draft through finalization and locking."""
        run = services.create_payroll_run(
            organization=self.org, payroll_cycle=self.cycle, name="August 2026 Run"
        )
        self.assertEqual(run.status, PayrollRunStatus.DRAFT)

        # Calculate
        calc_run = services.calculate_payroll_run(payroll_run=run)
        self.assertEqual(calc_run.status, PayrollRunStatus.CALCULATED)
        self.assertGreaterEqual(calc_run.total_employees, 2)
        self.assertGreater(calc_run.total_gross, Decimal("0.00"))
        self.assertGreater(calc_run.total_net, Decimal("0.00"))

        # Validate
        val_run = services.validate_payroll_run(payroll_run=calc_run)
        self.assertEqual(val_run.status, PayrollRunStatus.VALIDATED)

        # Approve
        app_run = services.approve_payroll_run(
            payroll_run=val_run, approver=self.approver, level="LEVEL_1_FINANCE", comments="Looks good"
        )
        self.assertEqual(app_run.status, PayrollRunStatus.APPROVED)

        # Finalize & Lock
        fin_run = services.finalize_payroll_run(payroll_run=app_run)
        self.assertEqual(fin_run.status, PayrollRunStatus.FINALIZED)
        self.assertIsNotNone(fin_run.finalized_at)

        lock = services.lock_payroll_period(organization=self.org, payroll_run=fin_run, locked_by_user_id=str(self.user.id))
        self.assertTrue(lock.payroll_locked)
        fin_run.refresh_from_db()
        self.assertTrue(fin_run.is_locked)

    def test_reopen_and_rollback_payroll_run(self):
        """Test reopening and rolling back a payroll run."""
        run = services.create_payroll_run(
            organization=self.org, payroll_cycle=self.cycle, name="Reopen Test Run"
        )
        services.calculate_payroll_run(payroll_run=run)
        services.validate_payroll_run(payroll_run=run)
        services.approve_payroll_run(payroll_run=run, approver=self.approver)
        services.finalize_payroll_run(payroll_run=run)

        # Reopen
        reopened = services.reopen_payroll_run(payroll_run=run, reason="Correction required")
        self.assertEqual(reopened.status, PayrollRunStatus.REOPENED)
        self.assertFalse(reopened.is_locked)

        # Rollback
        rolled_back = services.rollback_payroll_run(payroll_run=reopened, reason="Reset calculation")
        self.assertEqual(rolled_back.status, PayrollRunStatus.ROLLED_BACK)
        self.assertEqual(rolled_back.total_employees, 0)

    def test_payroll_run_api_views(self):
        """Test REST APIView endpoints for payroll runs."""
        # Create
        res_create = self.client.post(
            "/api/v1/payroll/runs/",
            {
                "organization_id": str(self.org.id),
                "payroll_cycle_id": str(self.cycle.id),
                "name": "API Payroll Run",
            },
            format="json",
        )
        self.assertEqual(res_create.status_code, 201)
        run_id = res_create.data["data"]["id"]

        # Calculate
        res_calc = self.client.post(f"/api/v1/payroll/runs/{run_id}/calculate/")
        self.assertEqual(res_calc.status_code, 200)

        # Validate
        res_val = self.client.post(f"/api/v1/payroll/runs/{run_id}/validate/")
        self.assertEqual(res_val.status_code, 200)

        # Approve
        res_app = self.client.post(
            f"/api/v1/payroll/runs/{run_id}/approve/",
            {
                "approver_id": str(self.approver.id),
                "level": "LEVEL_1_FINANCE",
                "comments": "Approved via API",
            },
            format="json",
        )
        self.assertEqual(res_app.status_code, 200)

        # Finalize
        res_fin = self.client.post(f"/api/v1/payroll/runs/{run_id}/finalize/")
        self.assertEqual(res_fin.status_code, 200)

        # Items
        res_items = self.client.get(f"/api/v1/payroll/runs/{run_id}/items/")
        self.assertEqual(res_items.status_code, 200)
        self.assertIn("summary", res_items.data["data"])
        self.assertIn("items", res_items.data["data"])
