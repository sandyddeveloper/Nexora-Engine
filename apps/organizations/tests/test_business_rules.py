"""Unit tests for Organization Business Rules validation guards."""

from django.test import TestCase

from apps.organizations.exceptions import (
    BusinessRuleValidationError,
    CircularDependencyError,
)
from apps.organizations.services import (
    create_branch,
    create_department,
    create_organization,
    create_team,
    soft_delete_branch,
    soft_delete_department,
    soft_delete_organization,
)


class BusinessRulesEngineTests(TestCase):
    """Test suite for domain hierarchy guards and business constraints."""

    def setUp(self):
        self.org = create_organization(name="Guard Corp")
        self.branch = create_branch(organization=self.org, code="BR-1", name="Branch 1")
        self.dept = create_department(
            organization=self.org, branch=self.branch, code="DEP-1", name="Department 1"
        )

    def test_cannot_delete_active_organization(self):
        with self.assertRaises(BusinessRuleValidationError):
            soft_delete_organization(organization=self.org)

    def test_cannot_delete_branch_containing_departments(self):
        with self.assertRaises(BusinessRuleValidationError):
            soft_delete_branch(branch=self.branch)

    def test_cannot_delete_department_containing_teams(self):
        create_team(
            organization=self.org,
            branch=self.branch,
            department=self.dept,
            code="TEAM-1",
            name="Team Alpha",
        )
        with self.assertRaises(BusinessRuleValidationError):
            soft_delete_department(department=self.dept)

    def test_circular_department_hierarchy_rejected(self):
        sub_dept = create_department(
            organization=self.org,
            branch=self.branch,
            code="SUB-1",
            name="Sub Department",
            parent_department=self.dept,
        )
        with self.assertRaises(CircularDependencyError):
            # Attempt to set parent of parent to child (creating a loop)
            from apps.organizations.services import update_department
            update_department(department=self.dept, parent_department=sub_dept)
