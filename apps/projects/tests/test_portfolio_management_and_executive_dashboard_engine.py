"""Unit tests for Enterprise Portfolio Management, Program Management & Executive Dashboard Engine."""

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

from apps.projects import selectors, services
from apps.projects.enums import HealthStatus, PortfolioType, RiskLevel
from apps.projects.exceptions import ProjectValidationError


class PortfolioManagementAndExecutiveDashboardEngineTestCase(TestCase):
    """Test suite for Portfolios, Programs, Health Scoring, Executive Dashboards, Risks, and Milestones."""

    @classmethod
    def setUpTestData(cls):
        cls.org = create_organization(name="Portfolio Global Enterprise")
        cls.branch = create_branch(organization=cls.org, code="PORTHQ", name="PMO HQ")
        cls.dept = create_department(organization=cls.org, branch=cls.branch, code="PORTPMO", name="PMO Department")
        cls.desg = create_designation(organization=cls.org, department=cls.dept, code="PORTDIR", name="PMO Director")

        cls.user_exec = create_user(email="execpmo@portglobal.com", password="SecurePassword123!")

        cls.owner = create_employee(
            organization=cls.org,
            branch=cls.branch,
            department=cls.dept,
            designation=cls.desg,
            user=cls.user_exec,
            first_name="Patricia",
            last_name="PortfolioOwner",
            official_email="patricia@portglobal.com",
            date_of_joining=date(2022, 1, 1),
        )

        cls.sponsor = create_employee(
            organization=cls.org,
            branch=cls.branch,
            department=cls.dept,
            designation=cls.desg,
            first_name="Steve",
            last_name="Sponsor",
            official_email="steve@portglobal.com",
            date_of_joining=date(2021, 1, 1),
        )

        cls.project1 = services.create_project(
            organization=cls.org,
            owner=cls.owner,
            manager=cls.owner,
            code="PRJ-PORT-01",
            name="Strategic Digital Platform",
        )
        services.activate_project(project=cls.project1)

        cls.project2 = services.create_project(
            organization=cls.org,
            owner=cls.owner,
            manager=cls.owner,
            code="PRJ-PORT-02",
            name="Cloud Infrastructure Migration",
        )
        services.activate_project(project=cls.project2)

    def setUp(self):
        self.client = APIClient()
        self.client.force_authenticate(user=self.user_exec)

    def test_portfolio_and_program_creation_and_mapping(self):
        """Create strategic portfolio and program, mapping projects."""
        portfolio = services.create_portfolio(
            organization=self.org,
            owner=self.owner,
            executive_sponsor=self.sponsor,
            code="PORT-STRAT-2026",
            name="2026 Digital Transformation Portfolio",
            portfolio_type=PortfolioType.STRATEGIC,
            budget=Decimal("5000000.00"),
        )
        self.assertEqual(portfolio.code, "PORT-STRAT-2026")

        program = services.create_program(
            organization=self.org,
            program_manager=self.owner,
            portfolio=portfolio,
            code="PRG-CLOUD-INIT",
            name="Cloud Migration Program",
            budget=Decimal("2000000.00"),
        )
        self.assertEqual(program.code, "PRG-CLOUD-INIT")

        # Map projects to portfolio
        services.map_projects_to_portfolio(portfolio=portfolio, project_ids=[self.project1.id, self.project2.id])
        self.assertEqual(portfolio.project_mappings.count(), 2)

    def test_automated_project_rag_health_scoring(self):
        """Calculate automated RAG status score for projects."""
        # Create completed task (GREEN health)
        t1 = services.create_task(project=self.project1, reporter=self.owner, code="P1-T1", title="Task 1")
        services.update_task_status(task=t1, status="DONE")
        health1 = selectors.calculate_project_health_score(project_id=self.project1.id)
        self.assertEqual(health1["overall_health"], "GREEN")

        # Create multiple blocked tasks on project 2 (RED health)
        for i in range(4):
            t = services.create_task(project=self.project2, reporter=self.owner, code=f"P2-BLK-{i}", title=f"Blocked {i}")
            services.update_task_status(task=t, status="BLOCKED")

        health2 = selectors.calculate_project_health_score(project_id=self.project2.id)
        self.assertEqual(health2["overall_health"], "RED")
        self.assertEqual(health2["blocked_tasks_count"], 4)

    def test_executive_dashboard_metrics_generation(self):
        """Generate high-level CEO/CTO executive dashboard metrics."""
        dashboard = selectors.get_executive_dashboard_metrics(organization_id=self.org.id, dashboard_type="CEO")
        self.assertEqual(dashboard["total_projects"], 2)
        self.assertEqual(dashboard["active_projects"], 2)

    def test_portfolio_risk_scoring_and_escalation(self):
        """Log portfolio risk and verify risk score calculation (Probability * Impact)."""
        risk = services.create_portfolio_risk(
            organization=self.org,
            title="Cloud Data Center Outage Risk",
            probability=4,
            impact=4,
            risk_owner=self.owner,
            mitigation_plan="Multi-region failover",
        )

        self.assertEqual(risk.risk_score, 16)
        self.assertEqual(risk.risk_level, RiskLevel.CRITICAL)

    def test_strategic_milestones_tracking(self):
        """Create and complete strategic milestones."""
        today = date.today()
        ms = services.create_portfolio_milestone(
            organization=self.org,
            title="Phase 1 Cloud Cutover Milestone",
            target_date=today + timedelta(days=30),
        )
        self.assertFalse(ms.is_completed)

        completed = services.complete_milestone(milestone=ms)
        self.assertTrue(completed.is_completed)
        self.assertEqual(completed.achieved_date, today)

    def test_portfolio_and_pmo_api_endpoints(self):
        """Test REST APIView endpoints for portfolios, programs, health, and executive dashboards."""
        # Create Portfolio API
        res_port = self.client.post(
            "/api/v1/projects/portfolios/",
            {
                "organization_id": str(self.org.id),
                "owner_id": str(self.owner.id),
                "code": "PORT-API-001",
                "name": "API Portfolio",
                "budget": 1000000.0,
            },
            format="json",
        )
        self.assertEqual(res_port.status_code, 201)

        # List Portfolios API
        res_list = self.client.get(f"/api/v1/projects/portfolios/?organization_id={self.org.id}")
        self.assertEqual(res_list.status_code, 200)

        # Create Program API
        res_prg = self.client.post(
            "/api/v1/projects/programs/",
            {
                "organization_id": str(self.org.id),
                "program_manager_id": str(self.owner.id),
                "code": "PRG-API-001",
                "name": "API Program",
                "budget": 500000.0,
            },
            format="json",
        )
        self.assertEqual(res_prg.status_code, 201)

        # Executive Dashboard API
        res_dash = self.client.get("/api/v1/projects/dashboards/executive/?dashboard_type=CEO")
        self.assertEqual(res_dash.status_code, 200)

        # Health API
        res_health = self.client.get(f"/api/v1/projects/{self.project1.id}/health/")
        self.assertEqual(res_health.status_code, 200)
