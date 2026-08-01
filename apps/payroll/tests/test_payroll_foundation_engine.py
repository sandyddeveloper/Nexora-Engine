"""Unit tests for Payroll Foundation Engine."""

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
from apps.payroll.enums import CalculationType, ComponentType, PayFrequency, PayrollStatus, TaxRegime
from apps.payroll.exceptions import PayrollValidationError


class PayrollFoundationEngineTestCase(TestCase):
    """Test suite for Salary Components, Templates, Payroll Profiles, Single Active Salary Structure, Policies, and Cycles."""

    @classmethod
    def setUpTestData(cls):
        cls.org = create_organization(name="Payroll Corp")
        cls.branch = create_branch(organization=cls.org, code="PMAIN", name="Payroll Branch")
        cls.dept = create_department(organization=cls.org, branch=cls.branch, code="PDEPT", name="Payroll Dept")
        cls.desg = create_designation(organization=cls.org, department=cls.dept, code="PDESG", name="Payroll Desg")

        cls.user = create_user(email="payrolladmin@payrollcorp.com", password="SecurePassword123!")

        cls.manager = create_employee(
            organization=cls.org,
            branch=cls.branch,
            department=cls.dept,
            designation=cls.desg,
            first_name="Finance",
            last_name="Manager",
            official_email="fmanager@payrollcorp.com",
            date_of_joining=date(2023, 1, 1),
        )

        cls.emp = create_employee(
            organization=cls.org,
            branch=cls.branch,
            department=cls.dept,
            designation=cls.desg,
            first_name="Charlie",
            last_name="Payee",
            official_email="charlie@payrollcorp.com",
            reporting_manager=cls.manager,
            date_of_joining=date(2024, 1, 1),
        )

        cls.comp_basic = services.create_salary_component(
            organization=cls.org,
            name="Basic Salary",
            code="BASIC",
            component_type=ComponentType.EARNING,
            calculation_type=CalculationType.PERCENTAGE_OF_CTC,
            default_amount_percentage=Decimal("40.00"),
            is_taxable=True,
        )

        cls.comp_hra = services.create_salary_component(
            organization=cls.org,
            name="House Rent Allowance",
            code="HRA",
            component_type=ComponentType.EARNING,
            calculation_type=CalculationType.PERCENTAGE_OF_BASIC,
            default_amount_percentage=Decimal("50.00"),
            is_taxable=True,
        )

    def setUp(self):
        self.client = APIClient()
        self.client.force_authenticate(user=self.user)

    def test_create_salary_component_success(self):
        """Create a valid salary component master."""
        comp = services.create_salary_component(
            organization=self.org,
            name="Special Allowance",
            code="SA",
            component_type=ComponentType.EARNING,
            calculation_type=CalculationType.FIXED,
            default_amount_percentage=Decimal("5000.00"),
        )
        self.assertEqual(comp.code, "SA")
        self.assertEqual(comp.name, "Special Allowance")

    def test_duplicate_salary_component_code_raises_error(self):
        """Creating duplicate component code in same org raises PayrollValidationError."""
        with self.assertRaises(PayrollValidationError):
            services.create_salary_component(
                organization=self.org, name="Basic Duplicate", code="BASIC"
            )

    def test_create_salary_template(self):
        """Create a master salary template with line items."""
        tmpl = services.create_salary_template(
            organization=self.org,
            name="Standard Executive Template",
            code="STD_EXEC",
            currency="INR",
            components_data=[
                {"salary_component_id": str(self.comp_basic.id), "amount_percentage": 40.0},
                {"salary_component_id": str(self.comp_hra.id), "amount_percentage": 50.0},
            ],
        )
        self.assertEqual(tmpl.code, "STD_EXEC")
        self.assertEqual(tmpl.components.count(), 2)

    def test_create_employee_payroll_profile(self):
        """Create employee payroll profile mapping tax regime and bank placeholders."""
        prof = services.create_employee_payroll_profile(
            employee=self.emp,
            tax_regime=TaxRegime.NEW_REGIME,
            pf_account_number="PF123456",
            pan_number="ABCDE1234F",
        )
        self.assertEqual(prof.status, PayrollStatus.ACTIVE)
        self.assertEqual(prof.tax_regime, TaxRegime.NEW_REGIME)

    def test_assign_and_revise_salary_structure(self):
        """Assign initial salary structure (v1), then revise (v2) and verify single active rule + revision audit."""
        eff_date_v1 = date(2024, 1, 1)
        struct_v1 = services.assign_employee_salary_structure(
            employee=self.emp,
            annual_ctc=Decimal("1200000.00"),
            effective_date=eff_date_v1,
            components_breakup=[
                {"salary_component_id": str(self.comp_basic.id), "monthly_amount": "40000.00"},
                {"salary_component_id": str(self.comp_hra.id), "monthly_amount": "20000.00"},
            ],
            revision_reason="Initial Offer",
        )

        self.assertEqual(struct_v1.version, 1)
        self.assertTrue(struct_v1.is_active)
        self.assertEqual(struct_v1.monthly_basic, Decimal("40000.00"))

        # Revise salary structure to v2
        eff_date_v2 = date(2025, 1, 1)
        struct_v2 = services.assign_employee_salary_structure(
            employee=self.emp,
            annual_ctc=Decimal("1500000.00"),
            effective_date=eff_date_v2,
            approved_by=self.manager,
            revision_reason="Annual Appraisal Promotion",
        )

        self.assertEqual(struct_v2.version, 2)
        self.assertTrue(struct_v2.is_active)

        # Ensure struct_v1 was deactivated
        struct_v1.refresh_from_db()
        self.assertFalse(struct_v1.is_active)

        # Verify active selector returns v2
        active_struct = selectors.get_active_salary_structure(employee_id=self.emp.id)
        self.assertEqual(active_struct.id, struct_v2.id)

        # Verify revision history log
        revisions = selectors.list_salary_revision_history(employee_id=self.emp.id)
        self.assertEqual(revisions.count(), 1)
        rev = revisions.first()
        self.assertEqual(rev.previous_ctc, Decimal("1200000.00"))
        self.assertEqual(rev.new_ctc, Decimal("1500000.00"))
        self.assertEqual(rev.increment_percentage, Decimal("25.00"))

    def test_payroll_policy_and_effective_hierarchical_lookup(self):
        """Create organization and department policies and verify hierarchical resolution."""
        org_pol = services.create_payroll_policy(
            organization=self.org, name="Org Default Policy", code="POL_ORG", cutoff_day_of_month=25, is_default=True
        )
        dept_pol = services.create_payroll_policy(
            organization=self.org, department=self.dept, name="Dept Override Policy", code="POL_DEPT", cutoff_day_of_month=20
        )

        # Effective lookup for employee in self.dept should return dept_pol
        eff_pol = selectors.get_effective_payroll_policy(
            organization_id=self.org.id, department_id=self.dept.id
        )
        self.assertEqual(eff_pol.id, dept_pol.id)

        # Lookup with no department override should return default org_pol
        eff_pol_default = selectors.get_effective_payroll_policy(organization_id=self.org.id)
        self.assertEqual(eff_pol_default.id, org_pol.id)

    def test_payroll_cycle(self):
        """Create a valid payroll cycle."""
        today = date.today()
        cycle = services.create_payroll_cycle(
            organization=self.org,
            name="August 2026 Payroll Cycle",
            frequency=PayFrequency.MONTHLY,
            start_date=today,
            end_date=today + timedelta(days=30),
            cutoff_date=today + timedelta(days=25),
            processing_date=today + timedelta(days=28),
            payment_date=today + timedelta(days=30),
        )
        self.assertEqual(cycle.frequency, PayFrequency.MONTHLY)
        self.assertFalse(cycle.is_closed)

    def test_payroll_api_views(self):
        """Verify Payroll APIView REST endpoints."""
        res_comp = self.client.get(f"/api/v1/payroll/components/?organization_id={self.org.id}")
        self.assertEqual(res_comp.status_code, 200)

        res_tmpl = self.client.get(f"/api/v1/payroll/templates/?organization_id={self.org.id}")
        self.assertEqual(res_tmpl.status_code, 200)

        res_prof_post = self.client.post(
            "/api/v1/payroll/profiles/",
            {
                "employee": str(self.emp.id),
                "organization": str(self.org.id),
                "status": "ACTIVE",
                "tax_regime": "NEW_REGIME",
            },
            format="json",
        )
        self.assertEqual(res_prof_post.status_code, 201)

        res_prof_get = self.client.get(f"/api/v1/payroll/profiles/?employee_id={self.emp.id}")
        self.assertEqual(res_prof_get.status_code, 200)

        res_assign = self.client.post(
            "/api/v1/payroll/structures/assign/",
            {
                "employee_id": str(self.emp.id),
                "annual_ctc": 1200000.0,
                "effective_date": "2024-01-01",
                "revision_reason": "Initial Assign",
            },
            format="json",
        )
        self.assertEqual(res_assign.status_code, 201)

        res_active = self.client.get(f"/api/v1/payroll/structures/active/?employee_id={self.emp.id}")
        self.assertEqual(res_active.status_code, 200)

        res_rev = self.client.get(f"/api/v1/payroll/structures/revisions/?employee_id={self.emp.id}")
        self.assertEqual(res_rev.status_code, 200)

        res_pol = self.client.get(f"/api/v1/payroll/policies/?organization_id={self.org.id}")
        self.assertEqual(res_pol.status_code, 200)

        res_cycle = self.client.get(f"/api/v1/payroll/cycles/?organization_id={self.org.id}")
        self.assertEqual(res_cycle.status_code, 200)
