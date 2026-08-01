"""Unit tests for Leave Eligibility, Carry Forward, Expiry, and Holiday Integration Engine."""

from datetime import date
from decimal import Decimal
from django.test import TestCase

from apps.employees.services import create_employee
from apps.organizations.models import HolidayCalendar
from apps.organizations.services import (
    create_branch,
    create_department,
    create_designation,
    create_organization,
)

from apps.leaves import selectors, services
from apps.leaves.enums import LeaveCategory
from apps.leaves.models import GenderSuitability


class LeaveEligibilityCarryForwardExpiryTestCase(TestCase):
    """Test suite for Leave Eligibility, Carry Forward Engine, Expiry Engine, and Holiday Integration."""

    @classmethod
    def setUpTestData(cls):
        cls.org = create_organization(name="CF Corp")
        cls.branch = create_branch(organization=cls.org, code="CFMAIN", name="CF Branch")
        cls.dept = create_department(organization=cls.org, branch=cls.branch, code="CFDEPT", name="CF Dept")
        cls.desg = create_designation(organization=cls.org, department=cls.dept, code="CFDESG", name="CF Desg")

        cls.emp_female = create_employee(
            organization=cls.org, branch=cls.branch, department=cls.dept, designation=cls.desg,
            first_name="Fiona", last_name="Female", official_email="fiona@cfcorp.com",
            gender="FEMALE", date_of_joining=date(2024, 1, 1),
        )

        cls.emp_male = create_employee(
            organization=cls.org, branch=cls.branch, department=cls.dept, designation=cls.desg,
            first_name="Mark", last_name="Male", official_email="mark@cfcorp.com",
            gender="MALE", date_of_joining=date(2024, 1, 1),
        )

        # Maternity Leave (Female Only)
        cls.lt_mat = services.create_leave_type(
            organization=cls.org, name="Maternity Leave", code="ML", category=LeaveCategory.MATERNITY,
            gender_suitability=GenderSuitability.FEMALE_ONLY,
        )
        cls.pol_mat = services.create_leave_policy(
            organization=cls.org, leave_type=cls.lt_mat, name="Mat Policy", code="MAT_POL",
            max_leave_per_year=Decimal("180.00"), is_default=True,
        )

        # Annual Leave (Carry Forward allowed, max 10 days)
        cls.lt_al = services.create_leave_type(organization=cls.org, name="Annual Leave", code="AL")
        cls.pol_al = services.create_leave_policy(
            organization=cls.org, leave_type=cls.lt_al, name="AL Policy", code="AL_POL",
            max_leave_per_year=Decimal("20.00"), carry_forward_allowed=True,
            max_carry_forward_days=Decimal("10.00"), is_default=True,
        )

    def test_gender_eligibility_restriction(self):
        """Female employee is eligible for Maternity Leave; Male employee is ineligible."""
        # Initialize balances
        bal_f = services.initialize_employee_leave_balance(
            employee=self.emp_female, leave_type=self.lt_mat, policy=self.pol_mat, opening_balance=Decimal("180.00"),
        )
        is_f_eligible, reason_f = selectors.check_leave_eligibility(employee=self.emp_female, leave_type=self.lt_mat)
        self.assertTrue(is_f_eligible)

        is_m_eligible, reason_m = selectors.check_leave_eligibility(employee=self.emp_male, leave_type=self.lt_mat)
        self.assertFalse(is_m_eligible)
        self.assertIn("Female", reason_m)

    def test_carry_forward_processing_applies_cap(self):
        """Year-end carry forward carries forward up to max cap and lapses excess balance."""
        bal = services.initialize_employee_leave_balance(
            employee=self.emp_female, leave_type=self.lt_al, policy=self.pol_al, opening_balance=Decimal("15.00"),
        )
        # 15 days available -> max carry forward is 10 days -> 5 days lapse
        res = services.process_carry_forward(organization=self.org, from_year=2025, to_year=2026)
        self.assertEqual(res["processed_count"], 1)

        bal.refresh_from_db()
        self.assertEqual(bal.carry_forward_balance, Decimal("10.00"))
        self.assertEqual(bal.expired_balance, Decimal("5.00"))

    def test_holiday_integration_working_days_calculation(self):
        """Holiday Integration Engine excludes public holidays and weekly offs when calculating working days."""
        # Create a public holiday on Monday, July 27, 2026
        HolidayCalendar.objects.create(
            organization=self.org, name="Company Holiday", holiday_date=date(2026, 7, 27),
        )

        # Window: Friday July 24 to Monday July 27 (4 calendar days: Fri, Sat, Sun, Mon)
        # Fri: Working (1)
        # Sat: Working (1)
        # Sun: Weekly Off (1)
        # Mon: Holiday (1)
        # Total Working Days = 2
        res = selectors.calculate_working_days_between(
            organization_id=self.org.id,
            start_date=date(2026, 7, 24),
            end_date=date(2026, 7, 27),
        )
        self.assertEqual(res["total_calendar_days"], 4)
        self.assertEqual(res["weekly_off_days"], 1)
        self.assertEqual(res["holiday_days"], 1)
        self.assertEqual(res["working_days"], 2)
