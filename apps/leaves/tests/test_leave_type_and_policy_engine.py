"""Unit tests for Leave Type, Policy, and Configuration Engine."""

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

from apps.leaves import selectors, services
from apps.leaves.enums import LeaveCategory, ResetPeriod
from apps.leaves.exceptions import LeavePolicyValidationError


class LeaveTypeAndPolicyEngineTestCase(TestCase):
    """Test suite for LeaveType, LeavePolicy, and hierarchical LeaveConfiguration resolution."""

    @classmethod
    def setUpTestData(cls):
        cls.org = create_organization(name="Leave Corp")
        cls.branch = create_branch(organization=cls.org, code="LMAIN", name="Leave Main Branch")
        cls.dept = create_department(organization=cls.org, branch=cls.branch, code="LENG", name="Leave Engineering")
        cls.desg = create_designation(organization=cls.org, department=cls.dept, code="LENGR", name="Leave Engineer")

    def test_create_leave_type_success(self):
        """Create a valid LeaveType with enterprise properties."""
        lt = services.create_leave_type(
            organization=self.org,
            name="Casual Leave",
            code="CL",
            category=LeaveCategory.CASUAL,
            description="Paid casual leave for personal work",
            is_paid=True,
        )
        self.assertEqual(lt.code, "CL")
        self.assertEqual(lt.organization, self.org)
        self.assertTrue(lt.is_paid)

    def test_create_duplicate_leave_type_code_raises_error(self):
        """Creating duplicate leave type code in same org raises LeavePolicyValidationError."""
        services.create_leave_type(organization=self.org, name="Sick Leave", code="SL")
        with self.assertRaises(LeavePolicyValidationError):
            services.create_leave_type(organization=self.org, name="Sick Leave Duplicate", code="SL")

    def test_create_leave_policy_success(self):
        """Create a valid LeavePolicy governing leave accrual and constraints."""
        lt = services.create_leave_type(organization=self.org, name="Annual Leave", code="AL")
        pol = services.create_leave_policy(
            organization=self.org,
            leave_type=lt,
            name="Standard Annual Policy",
            code="STD_AL",
            max_leave_per_year=Decimal("18.00"),
            notice_period_days=5,
            is_default=True,
        )
        self.assertEqual(pol.code, "STD_AL")
        self.assertEqual(pol.max_leave_per_year, Decimal("18.00"))
        self.assertTrue(pol.is_default)

    def test_set_leave_configuration_hierarchical_resolution(self):
        """Hierarchical leave configuration resolves Designation -> Department -> Branch -> Organization."""
        lt = services.create_leave_type(organization=self.org, name="Privilege Leave", code="PL")
        pol = services.create_leave_policy(
            organization=self.org, leave_type=lt, name="Default Policy", code="DEF_PL", is_default=True,
        )

        # Set org-level config
        services.set_leave_configuration(organization=self.org, default_policy=pol)

        resolved = selectors.get_effective_leave_configuration(
            organization_id=self.org.id,
            branch_id=self.branch.id,
            department_id=self.dept.id,
            designation_id=self.desg.id,
        )
        self.assertIsNotNone(resolved)
        self.assertEqual(resolved.default_policy, pol)
