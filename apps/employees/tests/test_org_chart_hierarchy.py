"""Unit tests for Org Chart reporting hierarchy tree building."""

import datetime
from django.test import TestCase

from apps.employees.selectors import get_org_chart_hierarchy
from apps.employees.services import create_employee
from apps.organizations.services import (
    create_branch,
    create_department,
    create_designation,
    create_organization,
)


class OrgChartHierarchyTests(TestCase):
    """Test suite for recursive organizational tree building."""

    def setUp(self):
        self.org = create_organization(name="Org Chart Corp")
        self.branch = create_branch(organization=self.org, code="BR-1", name="Branch 1")
        self.dept = create_department(organization=self.org, branch=self.branch, code="DEP-1", name="Dept 1")
        self.desig = create_designation(organization=self.org, department=self.dept, code="DES-1", name="Desig 1")

        self.ceo = create_employee(
            organization=self.org,
            branch=self.branch,
            department=self.dept,
            designation=self.desig,
            first_name="CEO",
            last_name="Executive",
            official_email="ceo@orgchart.com",
            date_of_joining=datetime.date.today(),
        )

        self.vp = create_employee(
            organization=self.org,
            branch=self.branch,
            department=self.dept,
            designation=self.desig,
            first_name="VP",
            last_name="Engineering",
            official_email="vp@orgchart.com",
            date_of_joining=datetime.date.today(),
            reporting_manager=self.ceo,
        )

        self.lead = create_employee(
            organization=self.org,
            branch=self.branch,
            department=self.dept,
            designation=self.desig,
            first_name="Tech",
            last_name="Lead",
            official_email="lead@orgchart.com",
            date_of_joining=datetime.date.today(),
            reporting_manager=self.vp,
        )

    def test_get_org_chart_hierarchy_returns_tree(self):
        tree = get_org_chart_hierarchy(employee_id=self.ceo.id)

        self.assertEqual(tree["employee_id"], self.ceo.employee_id)
        self.assertEqual(len(tree["direct_reports"]), 1)

        vp_node = tree["direct_reports"][0]
        self.assertEqual(vp_node["employee_id"], self.vp.employee_id)
        self.assertEqual(len(vp_node["direct_reports"]), 1)

        lead_node = vp_node["direct_reports"][0]
        self.assertEqual(lead_node["employee_id"], self.lead.employee_id)
        self.assertEqual(len(lead_node["direct_reports"]), 0)
