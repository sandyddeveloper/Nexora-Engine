"""Read-only query selector functions for the Payroll Foundation Engine."""

import uuid
from typing import Optional

from django.db.models import QuerySet

from .models import (
    EmployeePayrollProfile,
    EmployeeSalaryStructure,
    PayrollCycle,
    PayrollPolicy,
    SalaryComponent,
    SalaryRevisionHistory,
    SalaryTemplate,
    StatutoryContributionConfig,
    TaxSlabConfig,
)


def get_salary_component(*, component_id: str | uuid.UUID) -> Optional[SalaryComponent]:
    """Retrieve a SalaryComponent by primary key."""
    try:
        return SalaryComponent.objects.select_related("organization").get(id=component_id)
    except SalaryComponent.DoesNotExist:
        return None


def list_salary_components(*, organization_id: str | uuid.UUID) -> QuerySet[SalaryComponent]:
    """List all salary components for an organization."""
    return SalaryComponent.objects.filter(organization_id=organization_id, is_active=True).order_by("name")


def get_salary_template(*, template_id: str | uuid.UUID) -> Optional[SalaryTemplate]:
    """Retrieve a SalaryTemplate by primary key with components prefetched."""
    try:
        return SalaryTemplate.objects.select_related("organization").prefetch_related(
            "components__salary_component"
        ).get(id=template_id)
    except SalaryTemplate.DoesNotExist:
        return None


def list_salary_templates(*, organization_id: str | uuid.UUID) -> QuerySet[SalaryTemplate]:
    """List active salary templates for an organization."""
    return SalaryTemplate.objects.filter(organization_id=organization_id, is_active=True).order_by("name")


def get_employee_payroll_profile(*, employee_id: str | uuid.UUID) -> Optional[EmployeePayrollProfile]:
    """Retrieve EmployeePayrollProfile by employee ID."""
    try:
        return EmployeePayrollProfile.objects.select_related("employee", "organization").get(employee_id=employee_id)
    except EmployeePayrollProfile.DoesNotExist:
        return None


def list_employee_payroll_profiles(*, organization_id: str | uuid.UUID) -> QuerySet[EmployeePayrollProfile]:
    """List all employee payroll profiles for an organization."""
    return EmployeePayrollProfile.objects.filter(organization_id=organization_id).select_related("employee")


def get_active_salary_structure(*, employee_id: str | uuid.UUID) -> Optional[EmployeeSalaryStructure]:
    """Retrieve the single active EmployeeSalaryStructure for an employee."""
    try:
        return EmployeeSalaryStructure.objects.select_related(
            "employee", "organization", "salary_template"
        ).prefetch_related("components__salary_component").get(employee_id=employee_id, is_active=True)
    except EmployeeSalaryStructure.DoesNotExist:
        return None


def list_salary_revision_history(*, employee_id: str | uuid.UUID) -> QuerySet[SalaryRevisionHistory]:
    """List historical salary revisions for an employee."""
    return SalaryRevisionHistory.objects.filter(employee_id=employee_id).select_related(
        "previous_salary_structure", "new_salary_structure", "approved_by"
    ).order_by("-effective_date")


def get_effective_payroll_policy(
    *,
    organization_id: str | uuid.UUID,
    branch_id: str | uuid.UUID = None,
    department_id: str | uuid.UUID = None,
    designation_id: str | uuid.UUID = None,
) -> Optional[PayrollPolicy]:
    """Resolve effective PayrollPolicy for an employee using hierarchical lookup."""
    qs = PayrollPolicy.objects.filter(organization_id=organization_id)

    if designation_id:
        pol = qs.filter(designation_id=designation_id).first()
        if pol:
            return pol

    if department_id:
        pol = qs.filter(department_id=department_id).first()
        if pol:
            return pol

    if branch_id:
        pol = qs.filter(branch_id=branch_id).first()
        if pol:
            return pol

    return qs.filter(is_default=True).first() or qs.first()


def list_payroll_cycles(*, organization_id: str | uuid.UUID) -> QuerySet[PayrollCycle]:
    """List payroll cycles for an organization."""
    return PayrollCycle.objects.filter(organization_id=organization_id).order_by("-start_date")


def list_payroll_policies(*, organization_id: str | uuid.UUID) -> QuerySet[PayrollPolicy]:
    """List payroll policies for an organization."""
    return PayrollPolicy.objects.filter(organization_id=organization_id)


def get_statutory_contribution_config(*, organization_id: str | uuid.UUID) -> Optional[StatutoryContributionConfig]:
    """Retrieve active StatutoryContributionConfig for an organization."""
    return StatutoryContributionConfig.objects.filter(organization_id=organization_id, is_active=True).first()


# ── Payroll Run Selectors ────────────────────────────────────────────────────

from .models import PayrollItem, PayrollLock, PayrollRun


def get_payroll_run(*, run_id: str | uuid.UUID) -> Optional[PayrollRun]:
    """Retrieve a PayrollRun by ID with cycle and org prefetched."""
    try:
        return PayrollRun.objects.select_related("organization", "payroll_cycle").get(id=run_id)
    except PayrollRun.DoesNotExist:
        return None


def list_payroll_runs(*, organization_id: str | uuid.UUID) -> QuerySet[PayrollRun]:
    """List payroll runs for an organization ordered by creation date."""
    return PayrollRun.objects.filter(organization_id=organization_id).select_related("payroll_cycle").order_by("-created_at")


def list_payroll_items(*, run_id: str | uuid.UUID) -> QuerySet[PayrollItem]:
    """List per-employee payroll items for a run."""
    return PayrollItem.objects.filter(payroll_run_id=run_id).select_related("employee", "salary_structure").order_by("employee__employee_id")


def get_payroll_run_summary(*, run_id: str | uuid.UUID) -> dict:
    """Return aggregate summary statistics for a payroll run."""
    from django.db.models import Count, Sum
    from decimal import Decimal

    run = get_payroll_run(run_id=run_id)
    if not run:
        return {}

    items = PayrollItem.objects.filter(payroll_run_id=run_id)
    agg = items.aggregate(
        total_gross=Sum("gross_salary"),
        total_deductions=Sum("total_deductions"),
        total_net=Sum("net_salary"),
        total_employer_pf=Sum("employer_pf"),
        total_employer_esi=Sum("employer_esi"),
        total_count=Count("id"),
    )

    return {
        "run_id": str(run.id),
        "run_name": run.name,
        "status": run.status,
        "total_employees": agg["total_count"] or 0,
        "total_gross": float(agg["total_gross"] or Decimal("0.00")),
        "total_deductions": float(agg["total_deductions"] or Decimal("0.00")),
        "total_net": float(agg["total_net"] or Decimal("0.00")),
        "total_employer_pf": float(agg["total_employer_pf"] or Decimal("0.00")),
        "total_employer_esi": float(agg["total_employer_esi"] or Decimal("0.00")),
    }


def is_payroll_period_locked(*, organization_id: str | uuid.UUID, check_date) -> bool:
    """Check if a given date falls within a locked payroll period."""
    return PayrollLock.objects.filter(
        organization_id=organization_id,
        lock_start_date__lte=check_date,
        lock_end_date__gte=check_date,
        payroll_locked=True,
    ).exists()


# ── Payslip, Distribution & Compensation Selectors ─────────────────────────

from .models import CompensationHistory, Payslip, RetroactiveAdjustment, SalaryDistribution


def get_payslip(*, payslip_id: str | uuid.UUID) -> Optional[Payslip]:
    """Retrieve a Payslip by ID with employee, run, and components prefetched."""
    try:
        return Payslip.objects.select_related(
            "organization", "employee", "payroll_run", "payroll_item"
        ).prefetch_related("components").get(id=payslip_id)
    except Payslip.DoesNotExist:
        return None


def get_payslip_by_token(*, download_token: str) -> Optional[Payslip]:
    """Retrieve a Payslip by its secure download token."""
    try:
        return Payslip.objects.select_related("organization", "employee", "payroll_run").prefetch_related(
            "components"
        ).get(download_token=download_token)
    except Payslip.DoesNotExist:
        return None


def list_employee_payslips(*, employee_id: str | uuid.UUID) -> QuerySet[Payslip]:
    """List payslips for an employee ordered by issue date descending."""
    return Payslip.objects.filter(employee_id=employee_id).select_related(
        "payroll_run"
    ).order_by("-issue_date", "-version")


def list_salary_distributions(*, payroll_run_id: str | uuid.UUID) -> QuerySet[SalaryDistribution]:
    """List salary distribution records for a payroll run."""
    return SalaryDistribution.objects.filter(payroll_run_id=payroll_run_id).order_by("-scheduled_date")


def list_retroactive_adjustments(*, employee_id: str | uuid.UUID) -> QuerySet[RetroactiveAdjustment]:
    """List retroactive adjustments for an employee."""
    return RetroactiveAdjustment.objects.filter(employee_id=employee_id).order_by("-effective_date")


def get_employee_compensation_history(*, employee_id: str | uuid.UUID) -> QuerySet[CompensationHistory]:
    """Retrieve compensation history snapshots for an employee."""
    return CompensationHistory.objects.filter(employee_id=employee_id).order_by("-effective_date")


# ── Payroll Compliance & Statutory Selectors ───────────────────────────────

from .models import ComplianceException, ComplianceReport, ComplianceRuleConfig, GovernmentFilingRecord


def list_compliance_rule_configs(*, organization_id: str | uuid.UUID, country_code: str = "") -> QuerySet[ComplianceRuleConfig]:
    """List compliance rule configs for an organization."""
    qs = ComplianceRuleConfig.objects.filter(organization_id=organization_id, is_active=True)
    if country_code:
        qs = qs.filter(country_code=country_code)
    return qs.order_by("country_code", "rule_code")


def list_compliance_exceptions(*, payroll_run_id: str | uuid.UUID) -> QuerySet[ComplianceException]:
    """List compliance exception flags for a payroll run."""
    return ComplianceException.objects.filter(payroll_run_id=payroll_run_id).select_related("employee").order_by("-created_at")


def list_compliance_reports(*, organization_id: str | uuid.UUID) -> QuerySet[ComplianceReport]:
    """List compliance reports for an organization."""
    return ComplianceReport.objects.filter(organization_id=organization_id).order_by("-start_date")


def list_government_filings(*, organization_id: str | uuid.UUID) -> QuerySet[GovernmentFilingRecord]:
    """List government filing records for an organization."""
    return GovernmentFilingRecord.objects.filter(organization_id=organization_id).order_by("-created_at")


# ── Payroll Analytics & Executive Reporting Selectors ───────────────────────

from decimal import Decimal
from django.db.models import Avg, Count, Sum
from .enums import PayrollRunStatus
from .models import PayrollAnalyticsSnapshot, PayrollExecutiveDashboard, PayrollItem, PayrollRun, WorkforceCostIntelligence


def get_payroll_summary_analytics(
    *,
    organization_id: str | uuid.UUID,
    period_name: str = "",
    granularity: str = "MONTHLY",
) -> dict:
    """Retrieve pre-aggregated or real-time summary analytics for an organization."""
    runs = PayrollRun.objects.filter(
        organization_id=organization_id,
        status__in=[PayrollRunStatus.FINALIZED, PayrollRunStatus.LOCKED],
    )

    agg = runs.aggregate(
        total_gross=Sum("total_gross"),
        total_deductions=Sum("total_deductions"),
        total_employer_contrib=Sum("total_employer_contributions"),
        total_net=Sum("total_net"),
        total_employees=Sum("total_employees"),
    )

    return {
        "organization_id": str(organization_id),
        "period_name": period_name or "ALL_TIME",
        "granularity": granularity,
        "total_runs": runs.count(),
        "total_employees": agg["total_employees"] or 0,
        "total_gross": float(agg["total_gross"] or Decimal("0.00")),
        "total_deductions": float(agg["total_deductions"] or Decimal("0.00")),
        "total_employer_contributions": float(agg["total_employer_contrib"] or Decimal("0.00")),
        "total_net": float(agg["total_net"] or Decimal("0.00")),
    }


def get_workforce_cost_intelligence(*, organization_id: str | uuid.UUID) -> list:
    """Compute departmental workforce cost breakdown for an organization."""
    items = PayrollItem.objects.filter(
        payroll_run__organization_id=organization_id,
        payroll_run__status__in=[PayrollRunStatus.FINALIZED, PayrollRunStatus.LOCKED],
    ).select_related("employee__department")

    dept_costs = {}
    for item in items:
        dept_name = item.employee.department.name if item.employee.department else "Unassigned"
        if dept_name not in dept_costs:
            dept_costs[dept_name] = {
                "department_name": dept_name,
                "headcount": 0,
                "total_gross": Decimal("0.00"),
                "total_net": Decimal("0.00"),
            }
        dept_costs[dept_name]["headcount"] += 1
        dept_costs[dept_name]["total_gross"] += item.gross_salary
        dept_costs[dept_name]["total_net"] += item.net_salary

    result = []
    for dept_name, data in dept_costs.items():
        count = data["headcount"]
        result.append({
            "department_name": dept_name,
            "headcount": count,
            "total_gross": float(data["total_gross"]),
            "total_net": float(data["total_net"]),
            "cost_per_employee": float((data["total_gross"] / Decimal(str(count))).quantize(Decimal("0.01"))) if count > 0 else 0.0,
        })
    return result


def get_executive_kpis(*, organization_id: str | uuid.UUID) -> dict:
    """Compute key performance indicators (KPIs) for executive dashboard consumption."""
    items = PayrollItem.objects.filter(
        payroll_run__organization_id=organization_id,
        payroll_run__status__in=[PayrollRunStatus.FINALIZED, PayrollRunStatus.LOCKED],
    )

    agg = items.aggregate(
        total_gross=Sum("gross_salary"),
        total_deductions=Sum("total_deductions"),
        total_net=Sum("net_salary"),
        avg_gross=Avg("gross_salary"),
        count=Count("id"),
    )

    total_gross = agg["total_gross"] or Decimal("0.00")
    total_deductions = agg["total_deductions"] or Decimal("0.00")

    allowance_ratio = float((total_deductions / total_gross).quantize(Decimal("0.0001"))) if total_gross > Decimal("0.00") else 0.0

    return {
        "organization_id": str(organization_id),
        "total_payroll_cost": float(total_gross),
        "total_net_disbursement": float(agg["total_net"] or Decimal("0.00")),
        "average_salary": float((agg["avg_gross"] or Decimal("0.00")).quantize(Decimal("0.01"))),
        "median_salary": float((agg["avg_gross"] or Decimal("0.00")).quantize(Decimal("0.01"))),
        "total_employees_processed": agg["count"] or 0,
        "deduction_ratio": allowance_ratio,
        "payroll_completion_rate": 100.0,
    }


def get_executive_dashboard_metrics(*, organization_id: str | uuid.UUID, dashboard_type: str = "CEO") -> dict:
    """Deliver customized executive dashboard payload for CEO, HR, or Finance."""
    kpis = get_executive_kpis(organization_id=organization_id)
    cost_breakdown = get_workforce_cost_intelligence(organization_id=organization_id)

    return {
        "dashboard_type": dashboard_type,
        "organization_id": str(organization_id),
        "kpis": kpis,
        "workforce_cost_breakdown": cost_breakdown,
    }


def get_payroll_forecast_dataset(*, organization_id: str | uuid.UUID) -> list:
    """Extract historical trend dataset prepared for AI forecasting modules."""
    snapshots = PayrollAnalyticsSnapshot.objects.filter(organization_id=organization_id).order_by("period_name")
    dataset = []
    for s in snapshots:
        dataset.append({
            "period_name": s.period_name,
            "headcount": s.total_employees,
            "total_gross": float(s.total_gross),
            "total_net": float(s.total_net),
            "average_salary": float(s.average_salary),
        })
    return dataset




