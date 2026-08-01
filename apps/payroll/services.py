"""Domain state mutation service functions for the Payroll Foundation Engine."""

import csv
import io
import logging
import uuid
from datetime import date
from decimal import Decimal
from typing import List, Optional

from django.db import transaction

from . import selectors

from apps.employees.models import Employee, EmploymentStatus
from apps.organizations.models import Branch, Department, Designation, Organization

from .enums import CalculationType, ComponentType, PayFrequency, PayrollStatus, TaxRegime
from .events import (
    PayrollConfigurationChanged,
    PayrollPolicyCreated,
    PayrollProfileCreated,
    SalaryRevisionCreated,
    SalaryStructureCreated,
    SalaryStructureUpdated,
    publish_payroll_event,
)
from .exceptions import (
    PayrollProfileNotFoundError,
    PayrollValidationError,
    SalaryStructureError,
)
from .models import (
    EmployeePayrollProfile,
    EmployeeSalaryComponent,
    EmployeeSalaryStructure,
    PayrollCycle,
    PayrollPolicy,
    SalaryComponent,
    SalaryRevisionHistory,
    SalaryTemplate,
    SalaryTemplateComponent,
    StatutoryContributionConfig,
    TaxSlabConfig,
)

logger = logging.getLogger("nexora.payroll.services")


@transaction.atomic
def create_salary_component(
    *,
    organization: Organization,
    name: str,
    code: str,
    component_type: str = ComponentType.EARNING,
    calculation_type: str = CalculationType.FIXED,
    default_amount_percentage: Decimal = Decimal("0.00"),
    formula_expression: str = "",
    is_taxable: bool = True,
    is_recurring: bool = True,
    is_statutory: bool = False,
) -> SalaryComponent:
    """Create a new master SalaryComponent definition."""
    code_upper = code.upper().strip()
    if SalaryComponent.objects.filter(organization=organization, code=code_upper).exists():
        raise PayrollValidationError(f"SalaryComponent with code '{code_upper}' already exists in organization.")

    component = SalaryComponent.objects.create(
        organization=organization,
        name=name,
        code=code_upper,
        component_type=component_type,
        calculation_type=calculation_type,
        default_amount_percentage=default_amount_percentage,
        formula_expression=formula_expression,
        is_taxable=is_taxable,
        is_recurring=is_recurring,
        is_statutory=is_statutory,
    )

    logger.info("SalaryComponent created: %s (%s) for Org %s", name, code_upper, organization.code)
    return component


@transaction.atomic
def create_salary_template(
    *,
    organization: Organization,
    name: str,
    code: str,
    description: str = "",
    currency: str = "INR",
    components_data: Optional[List[dict]] = None,
) -> SalaryTemplate:
    """Create a reusable SalaryTemplate with mapped SalaryTemplateComponents."""
    code_upper = code.upper().strip()
    if SalaryTemplate.objects.filter(organization=organization, code=code_upper).exists():
        raise PayrollValidationError(f"SalaryTemplate with code '{code_upper}' already exists.")

    template = SalaryTemplate.objects.create(
        organization=organization,
        name=name,
        code=code_upper,
        description=description,
        currency=currency,
    )

    if components_data:
        for item in components_data:
            comp_id = item.get("salary_component_id")
            comp = SalaryComponent.objects.get(id=comp_id, organization=organization)
            SalaryTemplateComponent.objects.create(
                salary_template=template,
                salary_component=comp,
                calculation_type=item.get("calculation_type", comp.calculation_type),
                amount_percentage=item.get("amount_percentage", comp.default_amount_percentage),
            )

    publish_payroll_event(
        SalaryStructureCreated(
            event_id=str(uuid.uuid4()),
            event_type="SALARY_TEMPLATE_CREATED",
            organization_id=str(organization.id),
            structure_id=str(template.id),
        )
    )

    logger.info("SalaryTemplate created: %s (%s)", name, code_upper)
    return template


@transaction.atomic
def create_employee_payroll_profile(
    *,
    employee: Employee,
    status: str = PayrollStatus.ACTIVE,
    tax_regime: str = TaxRegime.NEW_REGIME,
    pf_account_number: str = "",
    esi_account_number: str = "",
    pan_number: str = "",
    bank_account_number_placeholder: str = "",
    bank_ifsc_placeholder: str = "",
    is_pf_eligible: bool = True,
    is_esi_eligible: bool = True,
) -> EmployeePayrollProfile:
    """Create or initialize EmployeePayrollProfile."""
    if employee.employment_status == EmploymentStatus.EXITED:
        raise PayrollValidationError("Cannot create payroll profile for exited employee.")

    profile, created = EmployeePayrollProfile.objects.get_or_create(
        employee=employee,
        defaults={
            "organization": employee.organization,
            "status": status,
            "tax_regime": tax_regime,
            "pf_account_number": pf_account_number,
            "esi_account_number": esi_account_number,
            "pan_number": pan_number,
            "bank_account_number_placeholder": bank_account_number_placeholder,
            "bank_ifsc_placeholder": bank_ifsc_placeholder,
            "is_pf_eligible": is_pf_eligible,
            "is_esi_eligible": is_esi_eligible,
        },
    )

    if created:
        publish_payroll_event(
            PayrollProfileCreated(
                event_id=str(uuid.uuid4()),
                event_type="PAYROLL_PROFILE_CREATED",
                organization_id=str(employee.organization_id),
                profile_id=str(profile.id),
                employee_id=str(employee.id),
            )
        )
        logger.info("EmployeePayrollProfile created for employee %s", employee.employee_id)

    return profile


@transaction.atomic
def assign_employee_salary_structure(
    *,
    employee: Employee,
    annual_ctc: Decimal,
    effective_date: date,
    salary_template: Optional[SalaryTemplate] = None,
    components_breakup: Optional[List[dict]] = None,
    currency: str = "INR",
    approved_by: Optional[Employee] = None,
    revision_reason: str = "Initial Salary Assignment",
) -> EmployeeSalaryStructure:
    """Assign an EmployeeSalaryStructure enforcing single active structure and version tracking."""
    if employee.employment_status == EmploymentStatus.EXITED:
        raise PayrollValidationError("Cannot assign salary structure to an exited employee.")

    # Find current active structure if any
    active_prev = EmployeeSalaryStructure.objects.filter(employee=employee, is_active=True).first()
    next_version = (active_prev.version + 1) if active_prev else 1

    # Deactivate previous active structure
    if active_prev:
        active_prev.is_active = False
        active_prev.save(update_fields=["is_active", "updated_at"])

    # Calculate monthly basic (approx 40% of CTC monthly if not specified)
    monthly_ctc = annual_ctc / Decimal("12.00")
    monthly_basic = monthly_ctc * Decimal("0.40")

    structure = EmployeeSalaryStructure.objects.create(
        employee=employee,
        organization=employee.organization,
        salary_template=salary_template,
        version=next_version,
        annual_ctc=annual_ctc,
        monthly_basic=monthly_basic,
        gross_salary_placeholder=monthly_ctc,
        net_salary_placeholder=monthly_ctc * Decimal("0.85"),
        currency=currency,
        effective_date=effective_date,
        is_active=True,
    )

    # Attach components
    if components_breakup:
        for item in components_breakup:
            comp_id = item.get("salary_component_id")
            comp = SalaryComponent.objects.get(id=comp_id, organization=employee.organization)
            mo_amt = Decimal(str(item.get("monthly_amount", "0.00")))
            ann_amt = mo_amt * Decimal("12.00")
            EmployeeSalaryComponent.objects.create(
                salary_structure=structure,
                salary_component=comp,
                monthly_amount=mo_amt,
                annual_amount=ann_amt,
            )

    # Record SalaryRevisionHistory if this is a revision/update
    if active_prev:
        prev_ctc = active_prev.annual_ctc
        inc_pct = Decimal("0.00")
        if prev_ctc > Decimal("0.00"):
            inc_pct = ((annual_ctc - prev_ctc) / prev_ctc) * Decimal("100.00")

        rev = SalaryRevisionHistory.objects.create(
            employee=employee,
            organization=employee.organization,
            previous_salary_structure=active_prev,
            new_salary_structure=structure,
            previous_ctc=prev_ctc,
            new_ctc=annual_ctc,
            increment_percentage=inc_pct,
            effective_date=effective_date,
            revision_reason=revision_reason,
            approved_by=approved_by,
        )

        publish_payroll_event(
            SalaryRevisionCreated(
                event_id=str(uuid.uuid4()),
                event_type="SALARY_REVISION_CREATED",
                organization_id=str(employee.organization_id),
                revision_id=str(rev.id),
                employee_id=str(employee.id),
                previous_ctc=float(prev_ctc),
                new_ctc=float(annual_ctc),
            )
        )

    CompensationHistory.objects.create(
        organization=employee.organization,
        employee=employee,
        annual_ctc=annual_ctc,
        monthly_basic=monthly_basic,
        effective_date=effective_date,
        revision_reason=revision_reason,
    )

    publish_payroll_event(
        SalaryStructureCreated(
            event_id=str(uuid.uuid4()),
            event_type="SALARY_STRUCTURE_ASSIGNED",
            organization_id=str(employee.organization_id),
            structure_id=str(structure.id),
            employee_id=str(employee.id),
            ctc_amount=float(annual_ctc),
        )
    )

    logger.info("SalaryStructure v%d assigned to %s (CTC: %s)", next_version, employee.employee_id, annual_ctc)
    return structure


@transaction.atomic
def create_payroll_policy(
    *,
    organization: Organization,
    name: str,
    code: str,
    branch: Optional[Branch] = None,
    department: Optional[Department] = None,
    designation: Optional[Designation] = None,
    cutoff_day_of_month: int = 25,
    pay_day_of_month: int = 30,
    is_default: bool = False,
) -> PayrollPolicy:
    """Create a PayrollPolicy for organization or specific entity scope."""
    code_upper = code.upper().strip()
    if is_default:
        PayrollPolicy.objects.filter(organization=organization, is_default=True).update(is_default=False)

    policy = PayrollPolicy.objects.create(
        organization=organization,
        branch=branch,
        department=department,
        designation=designation,
        name=name,
        code=code_upper,
        cutoff_day_of_month=cutoff_day_of_month,
        pay_day_of_month=pay_day_of_month,
        is_default=is_default,
    )

    publish_payroll_event(
        PayrollPolicyCreated(
            event_id=str(uuid.uuid4()),
            event_type="PAYROLL_POLICY_CREATED",
            organization_id=str(organization.id),
            policy_id=str(policy.id),
            policy_name=name,
        )
    )

    logger.info("PayrollPolicy created: %s (%s)", name, code_upper)
    return policy


@transaction.atomic
def create_payroll_cycle(
    *,
    organization: Organization,
    name: str,
    start_date: date,
    end_date: date,
    cutoff_date: date,
    processing_date: date,
    payment_date: date,
    frequency: str = PayFrequency.MONTHLY,
) -> PayrollCycle:
    """Create a PayrollCycle execution schedule."""
    if start_date > end_date:
        raise PayrollValidationError("PayrollCycle start_date cannot be after end_date.")

    cycle = PayrollCycle.objects.create(
        organization=organization,
        name=name,
        frequency=frequency,
        start_date=start_date,
        end_date=end_date,
        cutoff_date=cutoff_date,
        processing_date=processing_date,
        payment_date=payment_date,
    )

    logger.info("PayrollCycle created: %s (%s to %s)", name, start_date, end_date)
    return cycle


# ── Payroll Processing & Run Engine Services ─────────────────────────────────

from .enums import PayrollApprovalLevel, PayrollItemStatus, PayrollRunStatus
from .events import (
    PayrollApproved as PayrollApprovedEvent,
    PayrollCalculated,
    PayrollFinalized,
    PayrollLocked as PayrollLockedEvent,
    PayrollReopened,
    PayrollRolledBack,
    PayrollRunCreated,
    PayrollValidated,
)
from .models import (
    PayrollApproval,
    PayrollItem,
    PayrollItemComponent,
    PayrollLock,
    PayrollRun,
)


@transaction.atomic
def create_payroll_run(
    *,
    organization: Organization,
    payroll_cycle: PayrollCycle,
    name: str,
) -> PayrollRun:
    """Create a new DRAFT PayrollRun container for payroll execution."""
    existing = PayrollRun.objects.filter(
        payroll_cycle=payroll_cycle,
        status__in=[PayrollRunStatus.CALCULATED, PayrollRunStatus.VALIDATED, PayrollRunStatus.APPROVED, PayrollRunStatus.FINALIZED, PayrollRunStatus.LOCKED],
    ).exists()
    if existing:
        raise PayrollValidationError("A payroll run already exists for this cycle in a non-draft state.")

    run = PayrollRun.objects.create(
        organization=organization,
        payroll_cycle=payroll_cycle,
        name=name,
        status=PayrollRunStatus.DRAFT,
    )

    publish_payroll_event(
        PayrollRunCreated(
            event_id=str(uuid.uuid4()),
            event_type="PAYROLL_RUN_CREATED",
            organization_id=str(organization.id),
            run_id=str(run.id),
            cycle_id=str(payroll_cycle.id),
        )
    )

    logger.info("PayrollRun created: %s [DRAFT]", name)
    return run


@transaction.atomic
def calculate_payroll_run(*, payroll_run: PayrollRun) -> PayrollRun:
    """Calculate salaries for all active employees and produce PayrollItems."""
    if payroll_run.status not in [PayrollRunStatus.DRAFT, PayrollRunStatus.REOPENED]:
        raise PayrollValidationError(f"Cannot calculate payroll run in status '{payroll_run.status}'.")

    # Clear previous items if recalculating
    PayrollItem.objects.filter(payroll_run=payroll_run).delete()

    org = payroll_run.organization
    cycle = payroll_run.payroll_cycle

    # Get all active employees with active salary structures
    active_employees = Employee.objects.filter(
        organization=org,
        is_active=True,
    ).select_related("organization")

    total_working_days = max((cycle.end_date - cycle.start_date).days + 1, 1)

    agg_gross = Decimal("0.00")
    agg_deductions = Decimal("0.00")
    agg_employer_contrib = Decimal("0.00")
    agg_net = Decimal("0.00")
    processed_count = 0

    # Fetch statutory config once
    stat_config = StatutoryContributionConfig.objects.filter(organization=org, is_active=True).first()
    emp_pf_rate = stat_config.employee_pf_rate_pct / Decimal("100.00") if stat_config else Decimal("0.12")
    er_pf_rate = stat_config.employer_pf_rate_pct / Decimal("100.00") if stat_config else Decimal("0.12")
    pf_cap = stat_config.pf_wage_cap if stat_config else Decimal("15000.00")
    emp_esi_rate = stat_config.employee_esi_rate_pct / Decimal("100.00") if stat_config else Decimal("0.0075")
    er_esi_rate = stat_config.employer_esi_rate_pct / Decimal("100.00") if stat_config else Decimal("0.0325")

    for emp in active_employees:
        salary_struct = EmployeeSalaryStructure.objects.filter(employee=emp, is_active=True).first()
        if not salary_struct:
            continue

        monthly_basic = salary_struct.monthly_basic
        monthly_gross = salary_struct.gross_salary_placeholder

        # Attendance integration: count present days (simplified — real integration hooks here)
        days_present = total_working_days
        days_absent = 0
        paid_leave = 0
        unpaid_leave = 0
        overtime_hours = Decimal("0.00")

        # Prorate basic by attendance
        effective_days = max(days_present + paid_leave, 0)
        proration_factor = Decimal(str(effective_days)) / Decimal(str(total_working_days))
        earned_basic = (monthly_basic * proration_factor).quantize(Decimal("0.01"))

        # Earnings = earned_basic + allowances (proportional to gross minus basic)
        allowances = ((monthly_gross - monthly_basic) * proration_factor).quantize(Decimal("0.01"))
        total_earnings = earned_basic + allowances

        # LOP deduction
        lop_deduction = Decimal("0.00")
        if unpaid_leave > 0:
            lop_deduction = (monthly_gross / Decimal(str(total_working_days)) * Decimal(str(unpaid_leave))).quantize(Decimal("0.01"))
            total_earnings = total_earnings - lop_deduction

        gross_salary = total_earnings

        # Statutory deductions
        pf_base = min(earned_basic, pf_cap)
        employee_pf = (pf_base * emp_pf_rate).quantize(Decimal("0.01"))
        employer_pf = (pf_base * er_pf_rate).quantize(Decimal("0.01"))
        employee_esi = (gross_salary * emp_esi_rate).quantize(Decimal("0.01"))
        employer_esi = (gross_salary * er_esi_rate).quantize(Decimal("0.01"))

        # Professional tax (fixed standard ₹200)
        professional_tax = Decimal("200.00")

        total_deductions_val = employee_pf + employee_esi + professional_tax
        net_salary = (gross_salary - total_deductions_val).quantize(Decimal("0.01"))

        item = PayrollItem.objects.create(
            payroll_run=payroll_run,
            employee=emp,
            salary_structure=salary_struct,
            status=PayrollItemStatus.CALCULATED,
            total_working_days=total_working_days,
            days_present=days_present,
            days_absent=days_absent,
            paid_leave_days=paid_leave,
            unpaid_leave_days=unpaid_leave,
            overtime_hours=overtime_hours,
            earned_basic=earned_basic,
            total_earnings=total_earnings,
            total_deductions=total_deductions_val,
            employer_pf=employer_pf,
            employer_esi=employer_esi,
            gross_salary=gross_salary,
            net_salary=net_salary,
        )

        agg_gross += gross_salary
        agg_deductions += total_deductions_val
        agg_employer_contrib += employer_pf + employer_esi
        agg_net += net_salary
        processed_count += 1

    from django.utils import timezone
    payroll_run.status = PayrollRunStatus.CALCULATED
    payroll_run.total_employees = processed_count
    payroll_run.total_gross = agg_gross
    payroll_run.total_deductions = agg_deductions
    payroll_run.total_employer_contributions = agg_employer_contrib
    payroll_run.total_net = agg_net
    payroll_run.calculated_at = timezone.now()
    payroll_run.save(update_fields=[
        "status", "total_employees", "total_gross", "total_deductions",
        "total_employer_contributions", "total_net", "calculated_at", "updated_at",
    ])

    publish_payroll_event(
        PayrollCalculated(
            event_id=str(uuid.uuid4()),
            event_type="PAYROLL_CALCULATED",
            organization_id=str(payroll_run.organization_id),
            run_id=str(payroll_run.id),
            total_employees=processed_count,
            total_gross=float(agg_gross),
            total_net=float(agg_net),
        )
    )

    logger.info("PayrollRun %s calculated: %d employees, Gross=%s, Net=%s", payroll_run.name, processed_count, agg_gross, agg_net)
    return payroll_run


@transaction.atomic
def validate_payroll_run(*, payroll_run: PayrollRun) -> PayrollRun:
    """Mark a calculated payroll run as VALIDATED after integrity checks."""
    if payroll_run.status != PayrollRunStatus.CALCULATED:
        raise PayrollValidationError(f"Cannot validate payroll run in status '{payroll_run.status}'.")

    error_items = PayrollItem.objects.filter(payroll_run=payroll_run, status=PayrollItemStatus.ERROR).count()
    if error_items > 0:
        raise PayrollValidationError(f"Cannot validate: {error_items} payroll items have errors.")

    payroll_run.status = PayrollRunStatus.VALIDATED
    payroll_run.save(update_fields=["status", "updated_at"])

    publish_payroll_event(
        PayrollValidated(
            event_id=str(uuid.uuid4()),
            event_type="PAYROLL_VALIDATED",
            organization_id=str(payroll_run.organization_id),
            run_id=str(payroll_run.id),
        )
    )

    logger.info("PayrollRun %s validated.", payroll_run.name)
    return payroll_run


@transaction.atomic
def approve_payroll_run(
    *,
    payroll_run: PayrollRun,
    approver: Employee,
    level: str = PayrollApprovalLevel.LEVEL_1_FINANCE,
    comments: str = "",
) -> PayrollRun:
    """Record approval at a specific level for a payroll run."""
    if payroll_run.status not in [PayrollRunStatus.VALIDATED, PayrollRunStatus.APPROVED]:
        raise PayrollValidationError(f"Cannot approve payroll run in status '{payroll_run.status}'.")

    PayrollApproval.objects.update_or_create(
        payroll_run=payroll_run,
        level=level,
        defaults={
            "decision": "APPROVED",
            "approver": approver,
            "comments": comments,
        },
    )

    payroll_run.status = PayrollRunStatus.APPROVED
    payroll_run.save(update_fields=["status", "updated_at"])

    publish_payroll_event(
        PayrollApprovedEvent(
            event_id=str(uuid.uuid4()),
            event_type="PAYROLL_APPROVED",
            organization_id=str(payroll_run.organization_id),
            run_id=str(payroll_run.id),
            approval_level=level,
            approver_id=str(approver.id),
        )
    )

    logger.info("PayrollRun %s approved at %s by %s.", payroll_run.name, level, approver.display_name)
    return payroll_run


@transaction.atomic
def finalize_payroll_run(*, payroll_run: PayrollRun) -> PayrollRun:
    """Finalize the payroll run: sets FINALIZED status and timestamps."""
    if payroll_run.status != PayrollRunStatus.APPROVED:
        raise PayrollValidationError(f"Cannot finalize payroll run in status '{payroll_run.status}'.")

    from django.utils import timezone
    payroll_run.status = PayrollRunStatus.FINALIZED
    payroll_run.finalized_at = timezone.now()
    payroll_run.save(update_fields=["status", "finalized_at", "updated_at"])

    # Mark all items as APPROVED
    PayrollItem.objects.filter(payroll_run=payroll_run).update(status=PayrollItemStatus.APPROVED)

    publish_payroll_event(
        PayrollFinalized(
            event_id=str(uuid.uuid4()),
            event_type="PAYROLL_FINALIZED",
            organization_id=str(payroll_run.organization_id),
            run_id=str(payroll_run.id),
            total_net_disbursement=float(payroll_run.total_net),
        )
    )

    logger.info("PayrollRun %s finalized.", payroll_run.name)
    return payroll_run


@transaction.atomic
def lock_payroll_period(
    *,
    organization: Organization,
    payroll_run: PayrollRun,
    locked_by_user_id: str = "",
) -> PayrollLock:
    """Lock payroll period for attendance, leave, and payroll modifications."""
    if payroll_run.status not in [PayrollRunStatus.FINALIZED, PayrollRunStatus.LOCKED]:
        raise PayrollValidationError("Can only lock period after payroll is finalized.")

    cycle = payroll_run.payroll_cycle
    lock = PayrollLock.objects.create(
        organization=organization,
        payroll_run=payroll_run,
        lock_start_date=cycle.start_date,
        lock_end_date=cycle.end_date,
        attendance_locked=True,
        leave_locked=True,
        payroll_locked=True,
        locked_by_user_id=locked_by_user_id,
    )

    payroll_run.status = PayrollRunStatus.LOCKED
    payroll_run.is_locked = True
    payroll_run.save(update_fields=["status", "is_locked", "updated_at"])

    publish_payroll_event(
        PayrollLockedEvent(
            event_id=str(uuid.uuid4()),
            event_type="PAYROLL_LOCKED",
            organization_id=str(organization.id),
            run_id=str(payroll_run.id),
        )
    )

    logger.info("Payroll period locked: %s to %s.", cycle.start_date, cycle.end_date)
    return lock


@transaction.atomic
def reopen_payroll_run(*, payroll_run: PayrollRun, reason: str) -> PayrollRun:
    """Reopen a finalized or locked payroll run for corrections."""
    if payroll_run.status not in [PayrollRunStatus.FINALIZED, PayrollRunStatus.LOCKED, PayrollRunStatus.APPROVED]:
        raise PayrollValidationError(f"Cannot reopen payroll run in status '{payroll_run.status}'.")

    # Remove locks
    PayrollLock.objects.filter(payroll_run=payroll_run).delete()

    payroll_run.status = PayrollRunStatus.REOPENED
    payroll_run.is_locked = False
    payroll_run.save(update_fields=["status", "is_locked", "updated_at"])

    publish_payroll_event(
        PayrollReopened(
            event_id=str(uuid.uuid4()),
            event_type="PAYROLL_REOPENED",
            organization_id=str(payroll_run.organization_id),
            run_id=str(payroll_run.id),
            reason=reason,
        )
    )

    logger.info("PayrollRun %s reopened: %s", payroll_run.name, reason)
    return payroll_run


@transaction.atomic
def rollback_payroll_run(*, payroll_run: PayrollRun, reason: str) -> PayrollRun:
    """Roll back a payroll run: deletes items and sets ROLLED_BACK status."""
    if payroll_run.status in [PayrollRunStatus.LOCKED]:
        raise PayrollValidationError("Cannot rollback a locked payroll run. Reopen it first.")

    PayrollItem.objects.filter(payroll_run=payroll_run).delete()
    PayrollLock.objects.filter(payroll_run=payroll_run).delete()
    PayrollApproval.objects.filter(payroll_run=payroll_run).delete()

    payroll_run.status = PayrollRunStatus.ROLLED_BACK
    payroll_run.total_employees = 0
    payroll_run.total_gross = Decimal("0.00")
    payroll_run.total_deductions = Decimal("0.00")
    payroll_run.total_employer_contributions = Decimal("0.00")
    payroll_run.total_net = Decimal("0.00")
    payroll_run.is_locked = False
    payroll_run.save(update_fields=[
        "status", "total_employees", "total_gross", "total_deductions",
        "total_employer_contributions", "total_net", "is_locked", "updated_at",
    ])

    publish_payroll_event(
        PayrollRolledBack(
            event_id=str(uuid.uuid4()),
            event_type="PAYROLL_ROLLED_BACK",
            organization_id=str(payroll_run.organization_id),
            run_id=str(payroll_run.id),
            reason=reason,
        )
    )

    logger.info("PayrollRun %s rolled back: %s", payroll_run.name, reason)
    return payroll_run


# ── Payslip, Distribution & Compensation Services ───────────────────────────

import secrets
from .enums import DistributionMethod, DistributionStatus, PayslipStatus, PayslipType
from .events import (
    CompensationUpdated,
    PayrollDistributed,
    PayslipDownloaded,
    PayslipGenerated as PayslipGeneratedEvent,
    RetroAdjustmentCreated,
)
from .models import (
    CompensationHistory,
    Payslip,
    PayslipComponentDetail,
    RetroactiveAdjustment,
    SalaryDistribution,
)


@transaction.atomic
def generate_payslips_for_run(*, payroll_run: PayrollRun) -> List[Payslip]:
    """Bulk generate immutable payslips for all calculated items in a finalized payroll run."""
    if payroll_run.status not in [PayrollRunStatus.FINALIZED, PayrollRunStatus.LOCKED]:
        raise PayrollValidationError("Payslips can only be generated for FINALIZED or LOCKED payroll runs.")

    items = PayrollItem.objects.filter(payroll_run=payroll_run).select_related("employee", "salary_structure")
    payslips = []

    today = date.today()

    for item in items:
        # Check if payslip already exists for this item
        existing = Payslip.objects.filter(payroll_run=payroll_run, employee=item.employee).first()
        if existing:
            payslips.append(existing)
            continue

        token = secrets.token_urlsafe(32)
        ps_number = f"PS-{payroll_run.organization.code}-{item.employee.employee_id}-{today.strftime('%Y%m')}"

        payslip = Payslip.objects.create(
            organization=payroll_run.organization,
            employee=item.employee,
            payroll_run=payroll_run,
            payroll_item=item,
            payslip_number=ps_number,
            payslip_type=PayslipType.MONTHLY,
            status=PayslipStatus.PUBLISHED,
            version=1,
            issue_date=today,
            gross_salary=item.gross_salary,
            total_deductions=item.total_deductions,
            net_salary=item.net_salary,
            download_token=token,
        )

        # Create component details
        PayslipComponentDetail.objects.create(
            payslip=payslip,
            component_name="Earned Basic Salary",
            component_code="BASIC",
            component_type=ComponentType.EARNING,
            amount=item.earned_basic,
        )
        if item.gross_salary > item.earned_basic:
            PayslipComponentDetail.objects.create(
                payslip=payslip,
                component_name="Allowances",
                component_code="ALLOWANCES",
                component_type=ComponentType.EARNING,
                amount=item.gross_salary - item.earned_basic,
            )

        # Record compensation history snapshot
        CompensationHistory.objects.create(
            organization=payroll_run.organization,
            employee=item.employee,
            annual_ctc=item.salary_structure.annual_ctc,
            monthly_basic=item.salary_structure.monthly_basic,
            effective_date=today,
            revision_reason=f"Payroll Run {payroll_run.name}",
        )

        publish_payroll_event(
            PayslipGeneratedEvent(
                event_id=str(uuid.uuid4()),
                event_type="PAYSLIP_GENERATED",
                organization_id=str(payroll_run.organization_id),
                payslip_id=str(payslip.id),
                employee_id=str(item.employee_id),
                run_id=str(payroll_run.id),
                net_salary=float(item.net_salary),
            )
        )

        payslips.append(payslip)

    logger.info("Generated %d payslips for PayrollRun %s.", len(payslips), payroll_run.name)
    return payslips


@transaction.atomic
def regenerate_payslip(*, payslip: Payslip, reason: str) -> Payslip:
    """Regenerate a payslip creating an incremented version."""
    payslip.version += 1
    payslip.download_token = secrets.token_urlsafe(32)
    payslip.status = PayslipStatus.PUBLISHED
    payslip.save(update_fields=["version", "download_token", "status", "updated_at"])

    publish_payroll_event(
        PayslipGeneratedEvent(
            event_id=str(uuid.uuid4()),
            event_type="PAYSLIP_REGENERATED",
            organization_id=str(payslip.organization_id),
            payslip_id=str(payslip.id),
            employee_id=str(payslip.employee_id),
            run_id=str(payslip.payroll_run_id),
            net_salary=float(payslip.net_salary),
        )
    )

    logger.info("Payslip %s regenerated to v%d.", payslip.payslip_number, payslip.version)
    return payslip


@transaction.atomic
def create_salary_distribution(
    *,
    payroll_run: PayrollRun,
    method: str = DistributionMethod.BANK_TRANSFER,
    scheduled_date: date,
) -> SalaryDistribution:
    """Schedule salary distribution for a finalized payroll run."""
    dist = SalaryDistribution.objects.create(
        organization=payroll_run.organization,
        payroll_run=payroll_run,
        method=method,
        status=DistributionStatus.SCHEDULED,
        total_amount=payroll_run.total_net,
        scheduled_date=scheduled_date,
    )

    publish_payroll_event(
        PayrollDistributed(
            event_id=str(uuid.uuid4()),
            event_type="PAYROLL_DISTRIBUTED",
            organization_id=str(payroll_run.organization_id),
            run_id=str(payroll_run.id),
            distribution_method=method,
            status=DistributionStatus.SCHEDULED,
        )
    )

    logger.info("SalaryDistribution scheduled for Run %s (Amount: %s)", payroll_run.name, payroll_run.total_net)
    return dist


@transaction.atomic
def create_retroactive_adjustment(
    *,
    employee: Employee,
    category: str,
    amount: Decimal,
    effective_date: date,
    reason: str,
) -> RetroactiveAdjustment:
    """Create a retroactive arrears or recovery adjustment record."""
    adj = RetroactiveAdjustment.objects.create(
        organization=employee.organization,
        employee=employee,
        category=category,
        amount=amount,
        effective_date=effective_date,
        reason=reason,
        is_processed=False,
    )

    publish_payroll_event(
        RetroAdjustmentCreated(
            event_id=str(uuid.uuid4()),
            event_type="RETRO_ADJUSTMENT_CREATED",
            organization_id=str(employee.organization_id),
            adjustment_id=str(adj.id),
            employee_id=str(employee.id),
            category=category,
            amount=float(amount),
        )
    )

    logger.info("RetroactiveAdjustment created for %s: %s (%s)", employee.employee_id, category, amount)
    return adj


def export_payslip_csv(*, payslip: Payslip) -> str:
    """Export payslip details as CSV content string."""
    import csv
    import io

    output = io.StringIO()
    writer = csv.writer(output)

    writer.writerow(["PAYSLIP REPORT", payslip.payslip_number])
    writer.writerow(["Employee ID", payslip.employee.employee_id])
    writer.writerow(["Employee Name", payslip.employee.display_name])
    writer.writerow(["Issue Date", payslip.issue_date])
    writer.writerow(["Version", payslip.version])
    writer.writerow([])
    writer.writerow(["Gross Salary", payslip.gross_salary])
    writer.writerow(["Total Deductions", payslip.total_deductions])
    writer.writerow(["Net Salary", payslip.net_salary])
    writer.writerow([])
    writer.writerow(["Component Name", "Code", "Type", "Amount"])

    for comp in payslip.components.all():
        writer.writerow([comp.component_name, comp.component_code, comp.component_type, comp.amount])

    return output.getvalue()


def record_payslip_download_audit(*, payslip: Payslip, user_id: str) -> None:
    """Publish audit event when a payslip is accessed/downloaded."""
    publish_payroll_event(
        PayslipDownloaded(
            event_id=str(uuid.uuid4()),
            event_type="PAYSLIP_DOWNLOADED",
            organization_id=str(payslip.organization_id),
            payslip_id=str(payslip.id),
            employee_id=str(payslip.employee_id),
            downloaded_by_user_id=user_id,
        )
    )


# ── Payroll Compliance & Statutory Services ─────────────────────────────────

from .enums import ComplianceExceptionSeverity, ComplianceReportType, ComplianceStatus, StatutoryFilingType
from .events import (
    ComplianceCalculated,
    ComplianceReportGenerated,
    ComplianceValidated as ComplianceValidatedEvent,
    TaxRuleCreated,
)
from .models import (
    ComplianceException,
    ComplianceReport,
    ComplianceRuleConfig,
    GovernmentFilingRecord,
)


@transaction.atomic
def validate_payroll_compliance(*, payroll_run: PayrollRun) -> List[ComplianceException]:
    """Validate a calculated payroll run for statutory compliance violations."""
    items = PayrollItem.objects.filter(payroll_run=payroll_run).select_related("employee")
    exceptions = []

    for item in items:
        # Check 1: Negative net salary
        if item.net_salary < Decimal("0.00"):
            ex = ComplianceException.objects.create(
                organization=payroll_run.organization,
                payroll_run=payroll_run,
                employee=item.employee,
                severity=ComplianceExceptionSeverity.ERROR,
                rule_code="NEG_SALARY",
                description=f"Employee {item.employee.employee_id} has negative net salary ({item.net_salary}).",
            )
            exceptions.append(ex)

        # Check 2: Minimum basic wage limit check (e.g. ₹5,000 threshold)
        if item.earned_basic < Decimal("5000.00"):
            ex = ComplianceException.objects.create(
                organization=payroll_run.organization,
                payroll_run=payroll_run,
                employee=item.employee,
                severity=ComplianceExceptionSeverity.WARNING,
                rule_code="MIN_WAGE_WARN",
                description=f"Employee {item.employee.employee_id} earned basic ({item.earned_basic}) is below recommended statutory baseline.",
            )
            exceptions.append(ex)

    publish_payroll_event(
        ComplianceCalculated(
            event_id=str(uuid.uuid4()),
            event_type="COMPLIANCE_CALCULATED",
            organization_id=str(payroll_run.organization_id),
            run_id=str(payroll_run.id),
            compliance_status=ComplianceStatus.COMPLIANT if len(exceptions) == 0 else ComplianceStatus.FLAGGED,
            total_exceptions=len(exceptions),
        )
    )

    logger.info("Compliance validation executed for Run %s: %d exceptions recorded.", payroll_run.name, len(exceptions))
    return exceptions


@transaction.atomic
def record_compliance_exception(
    *,
    organization: Organization,
    payroll_run: Optional[PayrollRun] = None,
    employee: Optional[Employee] = None,
    severity: str = ComplianceExceptionSeverity.WARNING,
    rule_code: str,
    description: str,
) -> ComplianceException:
    """Record a statutory compliance exception or flag."""
    return ComplianceException.objects.create(
        organization=organization,
        payroll_run=payroll_run,
        employee=employee,
        severity=severity,
        rule_code=rule_code,
        description=description,
    )


@transaction.atomic
def override_compliance_exception(
    *,
    exception: ComplianceException,
    user_id: str,
    override_reason: str,
) -> ComplianceException:
    """Perform authorized manual override for a compliance exception."""
    exception.is_overridden = True
    exception.overridden_by_user_id = user_id
    exception.override_reason = override_reason
    exception.save(update_fields=["is_overridden", "overridden_by_user_id", "override_reason", "updated_at"])

    logger.info("ComplianceException %s overridden by user %s.", exception.id, user_id)
    return exception


@transaction.atomic
def generate_compliance_report(
    *,
    organization: Organization,
    report_type: str = ComplianceReportType.TAX_SUMMARY,
    title: str,
    start_date: date,
    end_date: date,
) -> ComplianceReport:
    """Generate statutory compliance report aggregation."""
    # Compute aggregate totals from finalized runs in period
    runs = PayrollRun.objects.filter(
        organization=organization,
        created_at__date__gte=start_date,
        created_at__date__lte=end_date,
        status__in=[PayrollRunStatus.FINALIZED, PayrollRunStatus.LOCKED],
    )

    from django.db.models import Sum
    agg = runs.aggregate(
        total_gross=Sum("total_gross"),
        total_deductions=Sum("total_deductions"),
        total_employer_contrib=Sum("total_employer_contributions"),
        total_net=Sum("total_net"),
    )

    summary_data = {
        "report_type": report_type,
        "total_runs": runs.count(),
        "total_gross": float(agg["total_gross"] or Decimal("0.00")),
        "total_deductions": float(agg["total_deductions"] or Decimal("0.00")),
        "total_employer_contributions": float(agg["total_employer_contrib"] or Decimal("0.00")),
        "total_net": float(agg["total_net"] or Decimal("0.00")),
    }

    report = ComplianceReport.objects.create(
        organization=organization,
        report_type=report_type,
        title=title,
        start_date=start_date,
        end_date=end_date,
        summary_json=summary_data,
    )

    publish_payroll_event(
        ComplianceReportGenerated(
            event_id=str(uuid.uuid4()),
            event_type="COMPLIANCE_REPORT_GENERATED",
            organization_id=str(organization.id),
            report_id=str(report.id),
            report_type=report_type,
        )
    )

    logger.info("ComplianceReport generated: %s", title)
    return report


@transaction.atomic
def create_government_filing_record(
    *,
    organization: Organization,
    filing_type: str = StatutoryFilingType.MONTHLY_TAX_RETURN,
    period_name: str,
    total_tax_amount: Decimal,
    total_contribution_amount: Decimal,
    filing_reference_number: str = "",
) -> GovernmentFilingRecord:
    """Create statutory government filing record."""
    return GovernmentFilingRecord.objects.create(
        organization=organization,
        filing_type=filing_type,
        period_name=period_name,
        status=ComplianceStatus.COMPLIANT,
        total_tax_amount=total_tax_amount,
        total_contribution_amount=total_contribution_amount,
        filing_reference_number=filing_reference_number,
    )


# ── Payroll Analytics & Executive Reporting Services ─────────────────────────

from .enums import AnalyticsGranularity, DashboardType
from .events import (
    PayrollAnalyticsGenerated,
    PayrollDashboardGenerated,
    PayrollExportGenerated,
    PayrollReportGenerated,
)
from .models import (
    PayrollAnalyticsSnapshot,
    PayrollExecutiveDashboard,
    WorkforceCostIntelligence,
)


@transaction.atomic
def generate_payroll_analytics_snapshot(
    *,
    organization: Organization,
    period_name: str,
    granularity: str = AnalyticsGranularity.MONTHLY,
) -> PayrollAnalyticsSnapshot:
    """Generate and persist a periodic analytics metrics snapshot record."""
    runs = PayrollRun.objects.filter(
        organization=organization,
        status__in=[PayrollRunStatus.FINALIZED, PayrollRunStatus.LOCKED],
    )

    from django.db.models import Avg, Sum
    agg = runs.aggregate(
        total_gross=Sum("total_gross"),
        total_deductions=Sum("total_deductions"),
        total_employer_contrib=Sum("total_employer_contributions"),
        total_net=Sum("total_net"),
        total_emp=Sum("total_employees"),
    )

    total_emp = agg["total_emp"] or 0
    total_gross = agg["total_gross"] or Decimal("0.00")
    avg_salary = (total_gross / Decimal(str(total_emp))).quantize(Decimal("0.01")) if total_emp > 0 else Decimal("0.00")

    snapshot, _ = PayrollAnalyticsSnapshot.objects.update_or_create(
        organization=organization,
        period_name=period_name,
        granularity=granularity,
        defaults={
            "total_employees": total_emp,
            "total_gross": total_gross,
            "total_deductions": agg["total_deductions"] or Decimal("0.00"),
            "total_employer_contributions": agg["total_employer_contrib"] or Decimal("0.00"),
            "total_net": agg["total_net"] or Decimal("0.00"),
            "average_salary": avg_salary,
            "median_salary": avg_salary,
        },
    )

    publish_payroll_event(
        PayrollAnalyticsGenerated(
            event_id=str(uuid.uuid4()),
            event_type="PAYROLL_ANALYTICS_GENERATED",
            organization_id=str(organization.id),
            snapshot_id=str(snapshot.id),
            period_name=period_name,
        )
    )

    logger.info("PayrollAnalyticsSnapshot generated for Org %s period %s.", organization.name, period_name)
    return snapshot


@transaction.atomic
def generate_executive_dashboard(
    *,
    organization: Organization,
    dashboard_type: str = DashboardType.CEO,
) -> PayrollExecutiveDashboard:
    """Generate and persist pre-compiled executive dashboard metrics payload."""
    kpis = selectors.get_executive_kpis(organization_id=organization.id)
    cost_breakdown = selectors.get_workforce_cost_intelligence(organization_id=organization.id)

    metrics_payload = {
        "dashboard_type": dashboard_type,
        "kpis": kpis,
        "workforce_cost_breakdown": cost_breakdown,
        "generated_at": date.today().isoformat(),
    }

    dash, _ = PayrollExecutiveDashboard.objects.update_or_create(
        organization=organization,
        dashboard_type=dashboard_type,
        defaults={"metrics_json": metrics_payload},
    )

    publish_payroll_event(
        PayrollDashboardGenerated(
            event_id=str(uuid.uuid4()),
            event_type="PAYROLL_DASHBOARD_GENERATED",
            organization_id=str(organization.id),
            dashboard_type=dashboard_type,
        )
    )

    logger.info("PayrollExecutiveDashboard refreshed for Org %s type %s.", organization.name, dashboard_type)
    return dash


def export_payroll_register_report(*, organization: Organization, period_name: str = "") -> str:
    """Generate CSV payroll register export report."""
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["Organization Payroll Register Report", organization.name])
    writer.writerow(["Period", period_name or "ALL_TIME"])
    writer.writerow([])
    writer.writerow(["Run Name", "Cycle", "Status", "Employees", "Gross Salary", "Deductions", "Employer Contrib", "Net Salary"])

    runs = PayrollRun.objects.filter(
        organization=organization,
        status__in=[PayrollRunStatus.FINALIZED, PayrollRunStatus.LOCKED],
    ).select_related("payroll_cycle")

    for run in runs:
        writer.writerow([
            run.name,
            run.payroll_cycle.name,
            run.status,
            run.total_employees,
            run.total_gross,
            run.total_deductions,
            run.total_employer_contributions,
            run.total_net,
        ])

    publish_payroll_event(
        PayrollExportGenerated(
            event_id=str(uuid.uuid4()),
            event_type="PAYROLL_EXPORT_GENERATED",
            organization_id=str(organization.id),
            export_format="CSV",
        )
    )

    return output.getvalue()




