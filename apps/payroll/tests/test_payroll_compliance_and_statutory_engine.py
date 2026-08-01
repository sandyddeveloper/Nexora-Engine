"""Unit tests for Payroll Compliance & Statutory Engine."""

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
from apps.payroll.enums import CalculationType, ComplianceReportType, ComplianceStatus, PayFrequency, StatutoryFilingType


class PayrollComplianceAndStatutoryEngineTestCase(TestCase):
    """Test suite for Statutory Compliance Rules, Validation, Exceptions, Overrides, Reports, and Government Filings."""

    @classmethod
    def setUpTestData(cls):
        cls.org = create_organization(name="Statutory Compliance Corp")
        cls.branch = create_branch(organization=cls.org, code="SMAIN", name="Stat Branch")
        cls.dept = create_department(organization=cls.org, branch=cls.branch, code="SDEPT", name="Stat Dept")
        cls.desg = create_designation(organization=cls.org, department=cls.dept, code="SDESG", name="Stat Desg")

        cls.user = create_user(email="complianceadmin@statcorp.com", password="SecurePassword123!")

        cls.approver = create_employee(
            organization=cls.org,
            branch=cls.branch,
            department=cls.dept,
            designation=cls.desg,
            first_name="Compliance",
            last_name="Officer",
            official_email="cofficer@statcorp.com",
            date_of_joining=date(2023, 1, 1),
        )

        cls.emp = create_employee(
            organization=cls.org,
            branch=cls.branch,
            department=cls.dept,
            designation=cls.desg,
            first_name="Frank",
            last_name="Worker",
            official_email="frank@statcorp.com",
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
            name="August 2026 Stat Cycle",
            frequency=PayFrequency.MONTHLY,
            start_date=today,
            end_date=today + timedelta(days=30),
            cutoff_date=today + timedelta(days=25),
            processing_date=today + timedelta(days=28),
            payment_date=today + timedelta(days=30),
        )

        cls.payroll_run = services.create_payroll_run(organization=cls.org, payroll_cycle=cls.cycle, name="August 2026 Stat Run")
        services.calculate_payroll_run(payroll_run=cls.payroll_run)
        services.validate_payroll_run(payroll_run=cls.payroll_run)

    def setUp(self):
        self.client = APIClient()
        self.client.force_authenticate(user=self.user)

    def test_compliance_rule_config(self):
        """Create pluggable statutory compliance rule configuration."""
        rule = selectors.ComplianceRuleConfig.objects.create(
            organization=self.org,
            country_code="IN",
            state_code="KA",
            rule_code="MIN_WAGE_KA",
            name="Karnataka Minimum Wage Baseline",
            min_wage_limit=Decimal("15000.00"),
            effective_date=date.today(),
        )
        self.assertEqual(rule.country_code, "IN")
        self.assertTrue(rule.is_active)

    def test_validate_payroll_compliance(self):
        """Execute statutory compliance checks on calculated payroll run."""
        exceptions = services.validate_payroll_compliance(payroll_run=self.payroll_run)
        self.assertIsInstance(exceptions, list)

    def test_override_compliance_exception(self):
        """Perform authorized manual override of compliance exception."""
        ex = services.record_compliance_exception(
            organization=self.org,
            payroll_run=self.payroll_run,
            employee=self.emp,
            severity="WARNING",
            rule_code="TEST_CAP_WARN",
            description="Contribution cap advisory warning",
        )
        overridden = services.override_compliance_exception(
            exception=ex,
            user_id=str(self.user.id),
            override_reason="Approved waiver by Compliance Officer",
        )
        self.assertTrue(overridden.is_overridden)

    def test_generate_compliance_report(self):
        """Generate statutory compliance report aggregation."""
        today = date.today()
        report = services.generate_compliance_report(
            organization=self.org,
            report_type=ComplianceReportType.TAX_SUMMARY,
            title="Q3 Statutory Tax Summary Report",
            start_date=today,
            end_date=today + timedelta(days=30),
        )
        self.assertEqual(report.report_type, ComplianceReportType.TAX_SUMMARY)
        self.assertIn("total_runs", report.summary_json)

    def test_create_government_filing_record(self):
        """Create government statutory filing batch tracking record."""
        filing = services.create_government_filing_record(
            organization=self.org,
            filing_type=StatutoryFilingType.MONTHLY_TAX_RETURN,
            period_name="2026-08",
            total_tax_amount=Decimal("150000.00"),
            total_contribution_amount=Decimal("35000.00"),
            filing_reference_number="ACK-IN-2026-08-9921",
        )
        self.assertEqual(filing.status, ComplianceStatus.COMPLIANT)
        self.assertEqual(filing.filing_reference_number, "ACK-IN-2026-08-9921")

    def test_compliance_api_views(self):
        """Test REST APIView endpoints for compliance rules, validation, exceptions, reports, and filings."""
        res_rule = self.client.post(
            "/api/v1/payroll/compliance/rules/",
            {
                "organization": str(self.org.id),
                "country_code": "IN",
                "state_code": "MH",
                "rule_code": "PT_SLAB_MH",
                "name": "Maharashtra Professional Tax Rule",
                "min_wage_limit": "12000.00",
                "max_contribution_cap": "200.00",
                "effective_date": date.today().isoformat(),
            },
            format="json",
        )
        self.assertEqual(res_rule.status_code, 201)

        res_val = self.client.post(
            "/api/v1/payroll/compliance/validate/",
            {"payroll_run_id": str(self.payroll_run.id)},
            format="json",
        )
        self.assertEqual(res_val.status_code, 200)

        res_ex_list = self.client.get(f"/api/v1/payroll/compliance/exceptions/?payroll_run_id={self.payroll_run.id}")
        self.assertEqual(res_ex_list.status_code, 200)

        res_rep = self.client.post(
            "/api/v1/payroll/compliance/reports/",
            {
                "organization_id": str(self.org.id),
                "report_type": "TAX_SUMMARY",
                "title": "API Tax Report",
                "start_date": date.today().isoformat(),
                "end_date": (date.today() + timedelta(days=30)).isoformat(),
            },
            format="json",
        )
        self.assertEqual(res_rep.status_code, 201)

        res_filing = self.client.post(
            "/api/v1/payroll/compliance/filings/",
            {
                "organization_id": str(self.org.id),
                "filing_type": "MONTHLY_TAX_RETURN",
                "period_name": "2026-08",
                "total_tax_amount": 50000.0,
                "total_contribution_amount": 12000.0,
                "filing_reference_number": "API-FILING-REF-001",
            },
            format="json",
        )
        self.assertEqual(res_filing.status_code, 201)
