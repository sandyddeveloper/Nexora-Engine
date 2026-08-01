"""Unit tests for Leave Balance Ledger and Accrual Engine."""

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
)

from apps.leaves import selectors, services
from apps.leaves.enums import BalanceAdjustmentType, LeaveCategory
from apps.leaves.exceptions import LeaveBalanceError


class LeaveBalanceAndAccrualEngineTestCase(TestCase):
    """Test suite for LeaveBalance tracking, ledger audit history, and periodic accruals."""

    @classmethod
    def setUpTestData(cls):
        cls.org = create_organization(name="Accrual Corp")
        cls.branch = create_branch(organization=cls.org, code="AMAIN", name="Accrual Branch")
        cls.dept = create_department(organization=cls.org, branch=cls.branch, code="ADEPT", name="Accrual Dept")
        cls.desg = create_designation(organization=cls.org, department=cls.dept, code="ADESG", name="Accrual Desg")

        cls.emp = create_employee(
            organization=cls.org, branch=cls.branch, department=cls.dept, designation=cls.desg,
            first_name="Evan", last_name="Leave", official_email="evan@accrualcorp.com",
            date_of_joining=date(2024, 1, 1),
        )

        cls.lt = services.create_leave_type(organization=cls.org, name="Casual Leave", code="CL")
        cls.pol = services.create_leave_policy(
            organization=cls.org, leave_type=cls.lt, name="CL Policy", code="CL_POL",
            max_leave_per_year=Decimal("12.00"), is_default=True,
        )

    def test_initialize_leave_balance_success(self):
        """Initialize employee leave balance with opening balance and audit ledger entry."""
        bal = services.initialize_employee_leave_balance(
            employee=self.emp, leave_type=self.lt, policy=self.pol, opening_balance=Decimal("6.00"),
        )
        self.assertEqual(bal.opening_balance, Decimal("6.00"))
        self.assertEqual(bal.available_balance, Decimal("6.00"))

        history = selectors.get_leave_balance_history(leave_balance_id=bal.id)
        self.assertEqual(history.count(), 1)
        self.assertEqual(history.first().adjustment_type, BalanceAdjustmentType.INITIALIZATION)

    def test_initialize_duplicate_leave_balance_raises_error(self):
        """Duplicate balance initialization for same employee and leave type raises LeaveBalanceError."""
        services.initialize_employee_leave_balance(employee=self.emp, leave_type=self.lt, policy=self.pol)
        with self.assertRaises(LeaveBalanceError):
            services.initialize_employee_leave_balance(employee=self.emp, leave_type=self.lt, policy=self.pol)

    def test_adjust_leave_balance_credit_and_debit(self):
        """Adjusting balance updates mathematical available balance and ledger correctly."""
        bal = services.initialize_employee_leave_balance(
            employee=self.emp, leave_type=self.lt, policy=self.pol, opening_balance=Decimal("5.00"),
        )

        # Credit 2 days
        services.adjust_leave_balance(
            leave_balance=bal, adjustment_type=BalanceAdjustmentType.CREDIT, delta=Decimal("2.00"), reason="Bonus credit",
        )
        bal.refresh_from_db()
        self.assertEqual(bal.available_balance, Decimal("7.00"))

        # Debit 1.5 days
        services.adjust_leave_balance(
            leave_balance=bal, adjustment_type=BalanceAdjustmentType.DEBIT, delta=Decimal("1.50"), reason="Used leave",
        )
        bal.refresh_from_db()
        self.assertEqual(bal.available_balance, Decimal("5.50"))

    def test_process_scheduled_accruals_monthly(self):
        """Monthly scheduled accrual engine credits monthly quota to active balances."""
        bal = services.initialize_employee_leave_balance(
            employee=self.emp, leave_type=self.lt, policy=self.pol, opening_balance=Decimal("0.00"),
        )
        res = services.process_scheduled_accruals(
            organization=self.org, accrual_frequency="MONTHLY", accrual_date=date(2026, 8, 1),
        )
        self.assertEqual(res["accrued_count"], 1)
        bal.refresh_from_db()
        self.assertEqual(bal.allocated_accrued, Decimal("1.00"))  # 12 / 12 = 1.00
        self.assertEqual(bal.available_balance, Decimal("1.00"))
