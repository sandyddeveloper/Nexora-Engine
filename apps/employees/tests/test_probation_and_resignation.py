"""Unit tests for Probation Confirmation and Resignation Lifecycle Workflows."""

import datetime
from django.test import TestCase

from apps.employees.models import EmployeeResignation, EmploymentStatus
from apps.employees.services import (
    approve_resignation,
    confirm_employee_probation,
    create_employee,
    submit_resignation,
    withdraw_resignation,
)
from apps.organizations.services import (
    create_branch,
    create_department,
    create_designation,
    create_organization,
)


class ProbationAndResignationTests(TestCase):
    """Test suite for probation confirmation and resignation lifecycle workflows."""

    def setUp(self):
        self.org = create_organization(name="Probation Org")
        self.branch = create_branch(organization=self.org, code="BR-1", name="Branch 1")
        self.dept = create_department(organization=self.org, branch=self.branch, code="DEP-1", name="Dept 1")
        self.desig = create_designation(organization=self.org, department=self.dept, code="DES-1", name="Desig 1")

        self.emp = create_employee(
            organization=self.org,
            branch=self.branch,
            department=self.dept,
            designation=self.desig,
            first_name="Sam",
            last_name="Altman",
            official_email="sam@probation.com",
            date_of_joining=datetime.date.today(),
            employment_status=EmploymentStatus.PROBATION,
        )

    def test_confirm_employee_probation(self):
        today = datetime.date.today()
        emp = confirm_employee_probation(employee=self.emp, confirmation_date=today)
        self.assertEqual(emp.employment_status, EmploymentStatus.CONFIRMED)
        self.assertEqual(emp.confirmation_date, today)

    def test_submit_approve_and_withdraw_resignation(self):
        today = datetime.date.today()
        resignation = submit_resignation(
            employee=self.emp,
            resignation_date=today,
            notice_period_days=30,
            reason="Career growth opportunity",
        )

        self.assertIsNotNone(resignation.id)
        self.assertEqual(resignation.status, EmployeeResignation.ResignationStatus.PENDING)
        self.assertEqual(self.emp.employment_status, EmploymentStatus.RESIGNED)

        # Approve resignation
        resignation = approve_resignation(resignation=resignation, comments="Approved by Manager")
        self.assertEqual(resignation.status, EmployeeResignation.ResignationStatus.APPROVED)
        self.assertEqual(self.emp.employment_status, EmploymentStatus.NOTICE_PERIOD)

        # Withdraw resignation
        resignation = withdraw_resignation(resignation=resignation, remarks="Decided to stay")
        self.assertEqual(resignation.status, EmployeeResignation.ResignationStatus.WITHDRAWN)
        self.assertEqual(self.emp.employment_status, EmploymentStatus.ACTIVE)
