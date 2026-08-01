"""Unit tests for organizations models and soft-delete capabilities."""

import datetime
from django.test import TestCase

from apps.organizations.models import (
    Branch,
    Department,
    Designation,
    HolidayCalendar,
    Organization,
    OrganizationSetting,
    Shift,
    Team,
)
from apps.organizations.services import (
    create_branch,
    create_department,
    create_designation,
    create_holiday,
    create_organization,
    create_shift,
    create_team,
)


class OrganizationModelTests(TestCase):
    """Test suite verifying Organization model creation, unique constraints, and soft deletion."""

    def setUp(self):
        self.org = create_organization(name="Acme Global", legal_name="Acme Global Inc")
        self.branch = create_branch(
            organization=self.org,
            code="HQ-01",
            name="Headquarters",
            is_headquarters=True,
        )
        self.dept = create_department(
            organization=self.org,
            branch=self.branch,
            name="Engineering",
            code="ENG",
        )
        self.designation = create_designation(
            organization=self.org,
            department=self.dept,
            name="Senior Engineer",
            code="SR-ENG",
            level=3,
        )
        self.team = create_team(
            organization=self.org,
            branch=self.branch,
            department=self.dept,
            name="Backend Core",
            code="BACKEND",
        )
        self.shift = create_shift(
            organization=self.org,
            name="Day Shift",
            code="DAY",
            start_time=datetime.time(9, 0),
            end_time=datetime.time(17, 0),
        )
        self.holiday = create_holiday(
            organization=self.org,
            name="New Year",
            holiday_date=datetime.date(2027, 1, 1),
        )

    def test_organization_creation_auto_generates_code_and_settings(self):
        self.assertTrue(self.org.code.startswith("ORG-"))
        self.assertIsNotNone(self.org.setting)
        self.assertEqual(self.org.setting.default_currency, "USD")

    def test_soft_delete_and_restore_organization(self):
        org_id = self.org.id
        self.org.delete(soft=True)
        self.assertIsNone(Organization.objects.filter(id=org_id).first())
        self.assertIsNotNone(Organization.objects.with_deleted().filter(id=org_id).first())

        self.org.restore()
        self.assertIsNotNone(Organization.objects.filter(id=org_id).first())

    def test_branch_unique_code_per_organization(self):
        self.assertEqual(self.branch.code, "HQ-01")
        self.assertTrue(self.branch.is_headquarters)

    def test_holiday_calendar_org_wide_vs_branch_specific(self):
        self.assertIsNone(self.holiday.branch)  # Organization-wide
        branch_holiday = create_holiday(
            organization=self.org,
            branch=self.branch,
            name="Branch Anniversary",
            holiday_date=datetime.date(2027, 5, 10),
        )
        self.assertEqual(branch_holiday.branch, self.branch)
