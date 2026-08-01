"""Unit tests for Organization Onboarding Engine single-transaction workflow."""

from django.test import TestCase

from apps.organizations.models import (
    Branch,
    Department,
    HolidayCalendar,
    Organization,
    OrganizationFeatureFlag,
    OrganizationLimit,
    OrganizationSetting,
    OrganizationStatus,
    Shift,
)
from apps.organizations.services import onboard_organization


class OrganizationOnboardingEngineTests(TestCase):
    """Test suite verifying automated single-transaction onboarding workflow."""

    def test_complete_organization_onboarding(self):
        org = onboard_organization(
            name="Global Retail",
            legal_name="Global Retail Corporation",
            email="admin@globalretail.com",
            country="United States",
            city="New York",
        )

        self.assertIsNotNone(org.id)
        self.assertEqual(org.status, OrganizationStatus.ACTIVE)
        self.assertTrue(org.code.startswith("ORG-"))

        # Verify HQ Branch
        hq = Branch.objects.filter(organization=org, is_headquarters=True).first()
        self.assertIsNotNone(hq)
        self.assertEqual(hq.code, "HQ-01")

        # Verify 6 Default Departments
        depts = Department.objects.filter(organization=org)
        self.assertEqual(depts.count(), 6)
        dept_codes = set(depts.values_list("code", flat=True))
        self.assertIn("ENG", dept_codes)
        self.assertIn("HR", dept_codes)
        self.assertIn("FIN", dept_codes)

        # Verify Shift Template
        shift = Shift.objects.filter(organization=org).first()
        self.assertIsNotNone(shift)
        self.assertEqual(shift.code, "SHIFT-STD")

        # Verify Settings & Default Shift link
        setting = OrganizationSetting.objects.get(organization=org)
        self.assertEqual(setting.default_shift, shift)

        # Verify Limits & Feature Flags
        limit = OrganizationLimit.objects.get(organization=org)
        self.assertEqual(limit.max_branches, 10)

        flag = OrganizationFeatureFlag.objects.get(organization=org)
        self.assertTrue(flag.attendance_enabled)
        self.assertTrue(flag.payroll_enabled)
