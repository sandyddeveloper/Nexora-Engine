"""Unit tests for Shift Rostering Engine."""

import datetime
from django.test import TestCase

from apps.employees.services import create_employee
from apps.organizations.models import RosterStatus
from apps.organizations.services import (
    assign_employee_roster_shift,
    bulk_assign_team_roster_shift,
    create_branch,
    create_department,
    create_designation,
    create_organization,
    create_shift,
    create_shift_roster,
    create_team,
    publish_shift_roster,
)


class ShiftRosterEngineTests(TestCase):
    """Test suite for shift roster planning, assignments, and publishing."""

    def setUp(self):
        self.org = create_organization(name="Roster Test Org")
        self.branch = create_branch(organization=self.org, code="BR-1", name="Branch 1")
        self.dept = create_department(organization=self.org, branch=self.branch, code="DEP-1", name="Dept 1")
        self.desig = create_designation(organization=self.org, department=self.dept, code="DES-1", name="Desig 1")
        self.team = create_team(organization=self.org, branch=self.branch, department=self.dept, code="TEAM-1", name="Team 1")

        self.shift_morn = create_shift(
            organization=self.org,
            name="Morning Shift",
            code="MORN",
            start_time=datetime.time(6, 0),
            end_time=datetime.time(14, 0),
        )

        self.emp = create_employee(
            organization=self.org,
            branch=self.branch,
            department=self.dept,
            designation=self.desig,
            team=self.team,
            first_name="Roster",
            last_name="Worker",
            official_email="roster@rostertest.com",
            date_of_joining=datetime.date.today(),
        )

    def test_create_and_publish_shift_roster(self):
        start_date = datetime.date.today()
        end_date = start_date + datetime.timedelta(days=6)

        roster = create_shift_roster(
            organization=self.org,
            name="Weekly Schedule W1",
            code="W1-SCHED",
            period_type="WEEKLY",
            start_date=start_date,
            end_date=end_date,
        )

        self.assertEqual(roster.status, RosterStatus.DRAFT)

        assignment = assign_employee_roster_shift(
            roster=roster,
            employee=self.emp,
            shift=self.shift_morn,
            date=start_date,
        )

        self.assertIsNotNone(assignment.id)

        published_roster = publish_shift_roster(roster=roster)
        self.assertEqual(published_roster.status, RosterStatus.PUBLISHED)
        self.assertEqual(published_roster.version, 2)

    def test_bulk_assign_team_roster_shift(self):
        start_date = datetime.date.today()
        end_date = start_date + datetime.timedelta(days=2)

        roster = create_shift_roster(
            organization=self.org,
            name="Team Roster Plan",
            code="TEAM-ROSTER",
            start_date=start_date,
            end_date=end_date,
        )

        count = bulk_assign_team_roster_shift(
            roster=roster,
            team_id=self.team.id,
            shift=self.shift_morn,
            start_date=start_date,
            end_date=end_date,
        )

        self.assertEqual(count, 3)
