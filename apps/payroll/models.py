"""Domain models for the Payroll Foundation Engine extending BaseModel."""

from decimal import Decimal
from django.db import models
from django.utils.translation import gettext_lazy as _

from apps.common.models import BaseModel
from apps.employees.models import Employee
from apps.organizations.models import Branch, Department, Designation, Organization

from .enums import (
    AdjustmentCategory,
    AnalyticsGranularity,
    CalculationType,
    ComplianceExceptionSeverity,
    ComplianceReportType,
    ComplianceStatus,
    ComponentType,
    DashboardType,
    DistributionMethod,
    DistributionStatus,
    PayFrequency,
    PayrollApprovalLevel,
    PayrollItemStatus,
    PayrollRunStatus,
    PayrollStatus,
    PayslipStatus,
    PayslipType,
    StatutoryFilingType,
    TaxRegime,
)


class SalaryComponent(BaseModel):
    """Master definition of earning, deduction, and statutory salary components."""

    organization = models.ForeignKey(
        Organization,
        on_delete=models.PROTECT,
        related_name="salary_components",
        help_text=_("Associated organization instance."),
    )
    name = models.CharField(
        max_length=150,
        help_text=_("Component name (e.g. Basic Salary, House Rent Allowance, Provident Fund)."),
    )
    code = models.CharField(
        max_length=50,
        help_text=_("Unique component identifier code per organization (e.g. BASIC, HRA, PF)."),
    )
    component_type = models.CharField(
        max_length=50,
        choices=ComponentType.choices,
        default=ComponentType.EARNING,
        help_text=_("Classification of component (Earning, Deduction, Statutory, Reimbursement)."),
    )
    calculation_type = models.CharField(
        max_length=50,
        choices=CalculationType.choices,
        default=CalculationType.FIXED,
        help_text=_("Method of component calculation (Fixed, Percentage of Basic, Formula)."),
    )
    default_amount_percentage = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=Decimal("0.00"),
        help_text=_("Default amount or percentage value depending on calculation_type."),
    )
    formula_expression = models.CharField(
        max_length=500,
        blank=True,
        help_text=_("Formula expression placeholder for dynamic calculations."),
    )
    is_taxable = models.BooleanField(
        default=True,
        help_text=_("Whether component is subject to income tax calculation."),
    )
    is_recurring = models.BooleanField(
        default=True,
        help_text=_("Whether component recurs every payroll cycle or is one-time."),
    )
    is_statutory = models.BooleanField(
        default=False,
        help_text=_("Whether component is a mandatory statutory item (PF, ESI, PT)."),
    )
    is_active = models.BooleanField(
        default=True,
        help_text=_("Whether component definition is active for new structures."),
    )

    class Meta:
        verbose_name = _("Salary Component")
        verbose_name_plural = _("Salary Components")
        unique_together = ("organization", "code")
        indexes = [
            models.Index(fields=["organization", "component_type"], name="idx_salcomp_org_type"),
        ]

    def __str__(self) -> str:
        return f"{self.name} ({self.code})"


class SalaryTemplate(BaseModel):
    """Reusable master salary structure template for an organization."""

    organization = models.ForeignKey(
        Organization,
        on_delete=models.PROTECT,
        related_name="salary_templates",
        help_text=_("Associated organization instance."),
    )
    name = models.CharField(
        max_length=150,
        help_text=_("Template name (e.g. Standard Executive Grade A, Software Engineer Band 2)."),
    )
    code = models.CharField(
        max_length=50,
        help_text=_("Unique template code per organization."),
    )
    description = models.TextField(
        blank=True,
        help_text=_("Detailed description of template eligibility."),
    )
    currency = models.CharField(
        max_length=10,
        default="INR",
        help_text=_("Currency ISO code (e.g. INR, USD)."),
    )
    is_active = models.BooleanField(
        default=True,
        help_text=_("Whether template is active."),
    )

    class Meta:
        verbose_name = _("Salary Template")
        verbose_name_plural = _("Salary Templates")
        unique_together = ("organization", "code")

    def __str__(self) -> str:
        return f"{self.name} ({self.code})"


class SalaryTemplateComponent(BaseModel):
    """Mapping of a SalaryComponent to a SalaryTemplate with specific rules."""

    salary_template = models.ForeignKey(
        SalaryTemplate,
        on_delete=models.CASCADE,
        related_name="components",
        help_text=_("Parent salary template."),
    )
    salary_component = models.ForeignKey(
        SalaryComponent,
        on_delete=models.PROTECT,
        related_name="template_mappings",
        help_text=_("Linked salary component."),
    )
    calculation_type = models.CharField(
        max_length=50,
        choices=CalculationType.choices,
        default=CalculationType.FIXED,
        help_text=_("Override calculation type for template line item."),
    )
    amount_percentage = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=Decimal("0.00"),
        help_text=_("Overridden amount or percentage for template line item."),
    )

    class Meta:
        verbose_name = _("Salary Template Component")
        verbose_name_plural = _("Salary Template Components")
        unique_together = ("salary_template", "salary_component")

    def __str__(self) -> str:
        return f"{self.salary_template.code} - {self.salary_component.code}"


class EmployeePayrollProfile(BaseModel):
    """Master payroll settings and profile mapping for an employee."""

    employee = models.OneToOneField(
        Employee,
        on_delete=models.PROTECT,
        related_name="payroll_profile",
        help_text=_("Associated employee record."),
    )
    organization = models.ForeignKey(
        Organization,
        on_delete=models.PROTECT,
        related_name="employee_payroll_profiles",
        help_text=_("Associated organization instance."),
    )
    status = models.CharField(
        max_length=50,
        choices=PayrollStatus.choices,
        default=PayrollStatus.ACTIVE,
        help_text=_("Current payroll status of employee."),
    )
    tax_regime = models.CharField(
        max_length=50,
        choices=TaxRegime.choices,
        default=TaxRegime.NEW_REGIME,
        help_text=_("Employee chosen tax regime."),
    )
    pf_account_number = models.CharField(
        max_length=100,
        blank=True,
        help_text=_("Provident Fund (PF) account number or UAN."),
    )
    esi_account_number = models.CharField(
        max_length=100,
        blank=True,
        help_text=_("Employee State Insurance (ESI) account number."),
    )
    pan_number = models.CharField(
        max_length=50,
        blank=True,
        help_text=_("Income Tax Permanent Account Number (PAN)."),
    )
    bank_account_number_placeholder = models.CharField(
        max_length=100,
        blank=True,
        help_text=_("Bank account number placeholder for salary disbursement."),
    )
    bank_ifsc_placeholder = models.CharField(
        max_length=50,
        blank=True,
        help_text=_("Bank IFSC / Routing Code placeholder."),
    )
    is_pf_eligible = models.BooleanField(
        default=True,
        help_text=_("Whether employee is covered under PF statutory contribution."),
    )
    is_esi_eligible = models.BooleanField(
        default=True,
        help_text=_("Whether employee is covered under ESI statutory contribution."),
    )

    class Meta:
        verbose_name = _("Employee Payroll Profile")
        verbose_name_plural = _("Employee Payroll Profiles")
        indexes = [
            models.Index(fields=["organization", "status"], name="idx_payprof_org_status"),
        ]

    def __str__(self) -> str:
        return f"PayrollProfile ({self.employee.employee_id}) - {self.status}"


class EmployeeSalaryStructure(BaseModel):
    """Specific active/historical salary structure assigned to an employee."""

    employee = models.ForeignKey(
        Employee,
        on_delete=models.PROTECT,
        related_name="salary_structures",
        help_text=_("Associated employee record."),
    )
    organization = models.ForeignKey(
        Organization,
        on_delete=models.PROTECT,
        related_name="employee_salary_structures",
        help_text=_("Associated organization instance."),
    )
    salary_template = models.ForeignKey(
        SalaryTemplate,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="assigned_structures",
        help_text=_("Source salary template if assigned from template."),
    )
    version = models.PositiveIntegerField(
        default=1,
        help_text=_("Structure version number for historical tracking."),
    )
    annual_ctc = models.DecimalField(
        max_digits=14,
        decimal_places=2,
        default=Decimal("0.00"),
        help_text=_("Total annual Cost to Company (CTC)."),
    )
    monthly_basic = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=Decimal("0.00"),
        help_text=_("Calculated monthly basic salary."),
    )
    gross_salary_placeholder = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=Decimal("0.00"),
        help_text=_("Gross monthly salary placeholder."),
    )
    net_salary_placeholder = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=Decimal("0.00"),
        help_text=_("Net monthly take-home salary placeholder."),
    )
    currency = models.CharField(
        max_length=10,
        default="INR",
        help_text=_("Currency code."),
    )
    effective_date = models.DateField(
        help_text=_("Effective starting date of this salary structure."),
    )
    is_active = models.BooleanField(
        default=True,
        help_text=_("Whether this is the single active salary structure for the employee."),
    )

    class Meta:
        verbose_name = _("Employee Salary Structure")
        verbose_name_plural = _("Employee Salary Structures")
        indexes = [
            models.Index(fields=["employee", "is_active"], name="idx_salstruct_emp_active"),
            models.Index(fields=["organization", "effective_date"], name="idx_salstruct_org_effdate"),
        ]

    def __str__(self) -> str:
        return f"SalaryStructure v{self.version} ({self.employee.employee_id}) - CTC: {self.annual_ctc}"


class EmployeeSalaryComponent(BaseModel):
    """Line item component breakup for an EmployeeSalaryStructure."""

    salary_structure = models.ForeignKey(
        EmployeeSalaryStructure,
        on_delete=models.CASCADE,
        related_name="components",
        help_text=_("Parent employee salary structure."),
    )
    salary_component = models.ForeignKey(
        SalaryComponent,
        on_delete=models.PROTECT,
        related_name="assigned_employee_components",
        help_text=_("Linked salary component master."),
    )
    monthly_amount = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=Decimal("0.00"),
        help_text=_("Calculated monthly amount for this component."),
    )
    annual_amount = models.DecimalField(
        max_digits=14,
        decimal_places=2,
        default=Decimal("0.00"),
        help_text=_("Calculated annual amount for this component."),
    )

    class Meta:
        verbose_name = _("Employee Salary Component")
        verbose_name_plural = _("Employee Salary Components")
        unique_together = ("salary_structure", "salary_component")

    def __str__(self) -> str:
        return f"{self.salary_structure.employee.employee_id} - {self.salary_component.code}: {self.monthly_amount}/mo"


class SalaryRevisionHistory(BaseModel):
    """Audit log of salary increments, revisions, and structural updates."""

    employee = models.ForeignKey(
        Employee,
        on_delete=models.PROTECT,
        related_name="salary_revisions",
        help_text=_("Associated employee record."),
    )
    organization = models.ForeignKey(
        Organization,
        on_delete=models.PROTECT,
        related_name="salary_revisions",
        help_text=_("Associated organization instance."),
    )
    previous_salary_structure = models.ForeignKey(
        EmployeeSalaryStructure,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="superseded_revisions",
        help_text=_("Previous salary structure superseded by this revision."),
    )
    new_salary_structure = models.ForeignKey(
        EmployeeSalaryStructure,
        on_delete=models.PROTECT,
        related_name="created_revisions",
        help_text=_("New salary structure created by this revision."),
    )
    previous_ctc = models.DecimalField(
        max_digits=14,
        decimal_places=2,
        default=Decimal("0.00"),
        help_text=_("Previous annual CTC."),
    )
    new_ctc = models.DecimalField(
        max_digits=14,
        decimal_places=2,
        default=Decimal("0.00"),
        help_text=_("New annual CTC after revision."),
    )
    increment_percentage = models.DecimalField(
        max_digits=8,
        decimal_places=2,
        default=Decimal("0.00"),
        help_text=_("Calculated increment percentage."),
    )
    effective_date = models.DateField(
        help_text=_("Effective date of salary revision."),
    )
    revision_reason = models.TextField(
        blank=True,
        help_text=_("Reason or notes for salary revision (e.g. Annual Appraisal, Promotion)."),
    )
    approved_by = models.ForeignKey(
        Employee,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="approved_salary_revisions",
        help_text=_("Approving manager employee record."),
    )

    class Meta:
        verbose_name = _("Salary Revision History")
        verbose_name_plural = _("Salary Revision Histories")
        indexes = [
            models.Index(fields=["employee", "effective_date"], name="idx_salrev_emp_date"),
        ]

    def __str__(self) -> str:
        return f"SalaryRevision ({self.employee.employee_id}): {self.previous_ctc} -> {self.new_ctc}"


class PayrollPolicy(BaseModel):
    """Payroll rules and cutoff configuration at Organization/Branch/Department/Designation scope."""

    organization = models.ForeignKey(
        Organization,
        on_delete=models.PROTECT,
        related_name="payroll_policies",
        help_text=_("Associated organization instance."),
    )
    branch = models.ForeignKey(
        Branch,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="payroll_policies",
        help_text=_("Branch scope override if applicable."),
    )
    department = models.ForeignKey(
        Department,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="payroll_policies",
        help_text=_("Department scope override if applicable."),
    )
    designation = models.ForeignKey(
        Designation,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="payroll_policies",
        help_text=_("Designation scope override if applicable."),
    )
    name = models.CharField(
        max_length=150,
        help_text=_("Policy name (e.g. Standard Corporate Payroll Policy)."),
    )
    code = models.CharField(
        max_length=50,
        help_text=_("Unique policy code per organization."),
    )
    cutoff_day_of_month = models.PositiveIntegerField(
        default=25,
        help_text=_("Day of month when attendance/leave cutoff closes for processing (1-31)."),
    )
    pay_day_of_month = models.PositiveIntegerField(
        default=30,
        help_text=_("Day of month when salary payment is disbursed (1-31)."),
    )
    is_payroll_locked = models.BooleanField(
        default=False,
        help_text=_("Whether payroll master is locked against edits for current cycle."),
    )
    leave_deduction_enabled = models.BooleanField(
        default=True,
        help_text=_("Whether unpaid leaves automatically deduct from gross salary."),
    )
    overtime_policy_placeholder = models.CharField(
        max_length=255,
        blank=True,
        help_text=_("Overtime calculation policy placeholder."),
    )
    is_default = models.BooleanField(
        default=False,
        help_text=_("Whether policy is the default fallback policy for organization."),
    )

    class Meta:
        verbose_name = _("Payroll Policy")
        verbose_name_plural = _("Payroll Policies")
        unique_together = ("organization", "code")

    def __str__(self) -> str:
        return f"{self.name} ({self.code})"


class PayrollCycle(BaseModel):
    """Payroll execution cycle schedule and cutoff dates."""

    organization = models.ForeignKey(
        Organization,
        on_delete=models.PROTECT,
        related_name="payroll_cycles",
        help_text=_("Associated organization instance."),
    )
    name = models.CharField(
        max_length=150,
        help_text=_("Cycle name (e.g. Monthly Cycle - August 2026)."),
    )
    frequency = models.CharField(
        max_length=50,
        choices=PayFrequency.choices,
        default=PayFrequency.MONTHLY,
        help_text=_("Payment cycle frequency."),
    )
    start_date = models.DateField(
        help_text=_("Cycle start date."),
    )
    end_date = models.DateField(
        help_text=_("Cycle end date."),
    )
    cutoff_date = models.DateField(
        help_text=_("Data freeze / cutoff date for attendance and leave sync."),
    )
    processing_date = models.DateField(
        help_text=_("Scheduled date for salary calculation processing."),
    )
    payment_date = models.DateField(
        help_text=_("Scheduled bank disbursement date."),
    )
    is_closed = models.BooleanField(
        default=False,
        help_text=_("Whether payroll cycle has been processed and closed."),
    )

    class Meta:
        verbose_name = _("Payroll Cycle")
        verbose_name_plural = _("Payroll Cycles")
        indexes = [
            models.Index(fields=["organization", "start_date", "end_date"], name="idx_paycycle_org_dates"),
        ]

    def __str__(self) -> str:
        return f"{self.name} ({self.start_date} to {self.end_date})"


class StatutoryContributionConfig(BaseModel):
    """Configuration rules for Statutory Contributions (PF, ESI, Professional Tax)."""

    organization = models.ForeignKey(
        Organization,
        on_delete=models.PROTECT,
        related_name="statutory_configs",
        help_text=_("Associated organization instance."),
    )
    name = models.CharField(
        max_length=150,
        help_text=_("Statutory config name (e.g. India Standard PF & ESI 2026)."),
    )
    employee_pf_rate_pct = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=Decimal("12.00"),
        help_text=_("Employee Provident Fund contribution percentage."),
    )
    employer_pf_rate_pct = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=Decimal("12.00"),
        help_text=_("Employer Provident Fund contribution percentage."),
    )
    pf_wage_cap = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=Decimal("15000.00"),
        help_text=_("Statutory PF monthly wage ceiling cap."),
    )
    employee_esi_rate_pct = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=Decimal("0.75"),
        help_text=_("Employee ESI contribution percentage."),
    )
    employer_esi_rate_pct = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=Decimal("3.25"),
        help_text=_("Employer ESI contribution percentage."),
    )
    esi_wage_cap = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=Decimal("21000.00"),
        help_text=_("Statutory ESI monthly wage ceiling cap."),
    )
    is_active = models.BooleanField(
        default=True,
        help_text=_("Whether statutory configuration is active."),
    )

    class Meta:
        verbose_name = _("Statutory Contribution Config")
        verbose_name_plural = _("Statutory Contribution Configs")

    def __str__(self) -> str:
        return f"{self.name} (Org: {self.organization.code})"


class TaxSlabConfig(BaseModel):
    """Income tax regime and slab architecture placeholder per financial year."""

    organization = models.ForeignKey(
        Organization,
        on_delete=models.PROTECT,
        related_name="tax_slab_configs",
        help_text=_("Associated organization instance."),
    )
    financial_year = models.CharField(
        max_length=20,
        help_text=_("Financial year label (e.g. FY 2026-2027)."),
    )
    tax_regime = models.CharField(
        max_length=50,
        choices=TaxRegime.choices,
        default=TaxRegime.NEW_REGIME,
        help_text=_("Tax regime specification."),
    )
    min_income = models.DecimalField(
        max_digits=14,
        decimal_places=2,
        default=Decimal("0.00"),
        help_text=_("Lower bound of income slab."),
    )
    max_income = models.DecimalField(
        max_digits=14,
        decimal_places=2,
        null=True,
        blank=True,
        help_text=_("Upper bound of income slab (null for open-ended top slab)."),
    )
    tax_rate_pct = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=Decimal("0.00"),
        help_text=_("Tax rate percentage for slab."),
    )

    class Meta:
        verbose_name = _("Tax Slab Config")
        verbose_name_plural = _("Tax Slab Configs")

    def __str__(self) -> str:
        return f"{self.financial_year} [{self.tax_regime}] ({self.min_income} - {self.max_income}): {self.tax_rate_pct}%"


# ── Payroll Processing & Run Engine Models ───────────────────────────────────


class PayrollRun(BaseModel):
    """Container entity for a payroll processing execution run."""

    organization = models.ForeignKey(
        Organization,
        on_delete=models.PROTECT,
        related_name="payroll_runs",
        help_text=_("Associated organization."),
    )
    payroll_cycle = models.ForeignKey(
        PayrollCycle,
        on_delete=models.PROTECT,
        related_name="runs",
        help_text=_("Associated payroll cycle."),
    )
    name = models.CharField(
        max_length=200,
        help_text=_("Human-readable run name."),
    )
    status = models.CharField(
        max_length=50,
        choices=PayrollRunStatus.choices,
        default=PayrollRunStatus.DRAFT,
        help_text=_("Current processing status."),
    )
    total_employees = models.PositiveIntegerField(
        default=0,
        help_text=_("Total employees processed."),
    )
    total_gross = models.DecimalField(
        max_digits=16,
        decimal_places=2,
        default=Decimal("0.00"),
        help_text=_("Aggregate gross salary."),
    )
    total_deductions = models.DecimalField(
        max_digits=16,
        decimal_places=2,
        default=Decimal("0.00"),
        help_text=_("Aggregate deductions."),
    )
    total_employer_contributions = models.DecimalField(
        max_digits=16,
        decimal_places=2,
        default=Decimal("0.00"),
        help_text=_("Aggregate employer statutory contributions."),
    )
    total_net = models.DecimalField(
        max_digits=16,
        decimal_places=2,
        default=Decimal("0.00"),
        help_text=_("Aggregate net salary."),
    )
    calculated_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text=_("Timestamp when calculation completed."),
    )
    finalized_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text=_("Timestamp when run finalized."),
    )
    is_locked = models.BooleanField(
        default=False,
        help_text=_("Whether the run is locked against modifications."),
    )

    class Meta:
        verbose_name = _("Payroll Run")
        verbose_name_plural = _("Payroll Runs")
        indexes = [
            models.Index(fields=["organization", "status"], name="idx_payrun_org_status"),
            models.Index(fields=["payroll_cycle", "status"], name="idx_payrun_cycle_status"),
        ]

    def __str__(self) -> str:
        return f"{self.name} [{self.status}]"


class PayrollItem(BaseModel):
    """Per-employee calculated salary output line for a PayrollRun."""

    payroll_run = models.ForeignKey(
        PayrollRun,
        on_delete=models.CASCADE,
        related_name="items",
        help_text=_("Parent payroll run."),
    )
    employee = models.ForeignKey(
        Employee,
        on_delete=models.PROTECT,
        related_name="payroll_items",
        help_text=_("Associated employee."),
    )
    salary_structure = models.ForeignKey(
        EmployeeSalaryStructure,
        on_delete=models.PROTECT,
        related_name="payroll_items",
        help_text=_("Salary structure used for calculation."),
    )
    status = models.CharField(
        max_length=50,
        choices=PayrollItemStatus.choices,
        default=PayrollItemStatus.PENDING,
        help_text=_("Calculation status."),
    )
    total_working_days = models.PositiveIntegerField(
        default=0,
        help_text=_("Total working days in period."),
    )
    days_present = models.PositiveIntegerField(
        default=0,
        help_text=_("Days present (from attendance)."),
    )
    days_absent = models.PositiveIntegerField(
        default=0,
        help_text=_("Days absent."),
    )
    paid_leave_days = models.PositiveIntegerField(
        default=0,
        help_text=_("Paid leave days consumed."),
    )
    unpaid_leave_days = models.PositiveIntegerField(
        default=0,
        help_text=_("Unpaid / LOP leave days deducted."),
    )
    overtime_hours = models.DecimalField(
        max_digits=8,
        decimal_places=2,
        default=Decimal("0.00"),
        help_text=_("Overtime hours worked."),
    )
    earned_basic = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=Decimal("0.00"),
        help_text=_("Prorated earned basic salary."),
    )
    total_earnings = models.DecimalField(
        max_digits=14,
        decimal_places=2,
        default=Decimal("0.00"),
        help_text=_("Sum of all earning components."),
    )
    total_deductions = models.DecimalField(
        max_digits=14,
        decimal_places=2,
        default=Decimal("0.00"),
        help_text=_("Sum of all deduction components."),
    )
    employer_pf = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=Decimal("0.00"),
        help_text=_("Employer PF contribution."),
    )
    employer_esi = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=Decimal("0.00"),
        help_text=_("Employer ESI contribution."),
    )
    gross_salary = models.DecimalField(
        max_digits=14,
        decimal_places=2,
        default=Decimal("0.00"),
        help_text=_("Gross salary before deductions."),
    )
    net_salary = models.DecimalField(
        max_digits=14,
        decimal_places=2,
        default=Decimal("0.00"),
        help_text=_("Net take-home salary after deductions."),
    )
    error_message = models.TextField(
        blank=True,
        help_text=_("Error details if calculation failed."),
    )

    class Meta:
        verbose_name = _("Payroll Item")
        verbose_name_plural = _("Payroll Items")
        unique_together = ("payroll_run", "employee")
        indexes = [
            models.Index(fields=["payroll_run", "status"], name="idx_payitem_run_status"),
        ]

    def __str__(self) -> str:
        return f"PayrollItem ({self.employee.employee_id}) Net: {self.net_salary}"


class PayrollItemComponent(BaseModel):
    """Granular per-component calculation detail for a PayrollItem."""

    payroll_item = models.ForeignKey(
        PayrollItem,
        on_delete=models.CASCADE,
        related_name="component_details",
        help_text=_("Parent payroll item."),
    )
    salary_component = models.ForeignKey(
        SalaryComponent,
        on_delete=models.PROTECT,
        related_name="payroll_item_details",
        help_text=_("Linked salary component."),
    )
    amount = models.DecimalField(
        max_digits=14,
        decimal_places=2,
        default=Decimal("0.00"),
        help_text=_("Calculated amount for this component."),
    )

    class Meta:
        verbose_name = _("Payroll Item Component")
        verbose_name_plural = _("Payroll Item Components")
        unique_together = ("payroll_item", "salary_component")

    def __str__(self) -> str:
        return f"{self.salary_component.code}: {self.amount}"


class PayrollApproval(BaseModel):
    """Decision audit record for multi-level payroll run approval."""

    payroll_run = models.ForeignKey(
        PayrollRun,
        on_delete=models.CASCADE,
        related_name="approvals",
        help_text=_("Associated payroll run."),
    )
    level = models.CharField(
        max_length=50,
        choices=PayrollApprovalLevel.choices,
        help_text=_("Approval level."),
    )
    decision = models.CharField(
        max_length=20,
        default="APPROVED",
        help_text=_("Approval decision."),
    )
    approver = models.ForeignKey(
        Employee,
        on_delete=models.PROTECT,
        related_name="payroll_approvals_given",
        help_text=_("Approving employee."),
    )
    comments = models.TextField(
        blank=True,
        help_text=_("Approval comments or notes."),
    )

    class Meta:
        verbose_name = _("Payroll Approval")
        verbose_name_plural = _("Payroll Approvals")
        unique_together = ("payroll_run", "level")

    def __str__(self) -> str:
        return f"Approval [{self.level}] Run: {self.payroll_run.name}"


class PayrollLock(BaseModel):
    """Period freeze lock for attendance, leave, and payroll modifications."""

    organization = models.ForeignKey(
        Organization,
        on_delete=models.PROTECT,
        related_name="payroll_locks",
        help_text=_("Associated organization."),
    )
    payroll_run = models.ForeignKey(
        PayrollRun,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="locks",
        help_text=_("Associated payroll run."),
    )
    lock_start_date = models.DateField(
        help_text=_("Lock period start date."),
    )
    lock_end_date = models.DateField(
        help_text=_("Lock period end date."),
    )
    attendance_locked = models.BooleanField(
        default=True,
        help_text=_("Attendance data is locked."),
    )
    leave_locked = models.BooleanField(
        default=True,
        help_text=_("Leave data is locked."),
    )
    payroll_locked = models.BooleanField(
        default=True,
        help_text=_("Payroll master data is locked."),
    )
    locked_by_user_id = models.CharField(
        max_length=100,
        blank=True,
        help_text=_("User ID who initiated the lock."),
    )

    class Meta:
        verbose_name = _("Payroll Lock")
        verbose_name_plural = _("Payroll Locks")

    def __str__(self) -> str:
        return f"PayrollLock ({self.lock_start_date} to {self.lock_end_date})"


# ── Payslip, Salary Distribution & Employee Compensation Models ─────────────


class Payslip(BaseModel):
    """Immutable versioned employee payslip record for a finalized payroll run."""

    organization = models.ForeignKey(
        Organization,
        on_delete=models.PROTECT,
        related_name="payslips",
        help_text=_("Associated organization."),
    )
    employee = models.ForeignKey(
        Employee,
        on_delete=models.PROTECT,
        related_name="payslips",
        help_text=_("Associated employee."),
    )
    payroll_run = models.ForeignKey(
        PayrollRun,
        on_delete=models.PROTECT,
        related_name="payslips",
        help_text=_("Associated finalized payroll run."),
    )
    payroll_item = models.ForeignKey(
        PayrollItem,
        on_delete=models.PROTECT,
        related_name="payslips",
        help_text=_("Associated calculated payroll item."),
    )
    payslip_number = models.CharField(
        max_length=100,
        help_text=_("Unique payslip serial/number per organization."),
    )
    payslip_type = models.CharField(
        max_length=50,
        choices=PayslipType.choices,
        default=PayslipType.MONTHLY,
        help_text=_("Classification of payslip (Monthly, Off-Cycle, Correction)."),
    )
    status = models.CharField(
        max_length=50,
        choices=PayslipStatus.choices,
        default=PayslipStatus.GENERATED,
        help_text=_("Publication and access status."),
    )
    version = models.PositiveIntegerField(
        default=1,
        help_text=_("Payslip version number (increments on correction/regeneration)."),
    )
    issue_date = models.DateField(
        help_text=_("Official date of payslip issue."),
    )
    gross_salary = models.DecimalField(
        max_digits=14,
        decimal_places=2,
        default=Decimal("0.00"),
        help_text=_("Gross salary amount."),
    )
    total_deductions = models.DecimalField(
        max_digits=14,
        decimal_places=2,
        default=Decimal("0.00"),
        help_text=_("Total deductions amount."),
    )
    net_salary = models.DecimalField(
        max_digits=14,
        decimal_places=2,
        default=Decimal("0.00"),
        help_text=_("Net take-home salary."),
    )
    download_token = models.CharField(
        max_length=128,
        blank=True,
        help_text=_("Secure download access token for ESS portal."),
    )

    class Meta:
        verbose_name = _("Payslip")
        verbose_name_plural = _("Payslips")
        unique_together = ("organization", "payslip_number")
        indexes = [
            models.Index(fields=["employee", "issue_date"], name="idx_payslip_emp_date"),
            models.Index(fields=["payroll_run", "status"], name="idx_payslip_run_status"),
            models.Index(fields=["download_token"], name="idx_payslip_token"),
        ]

    def __str__(self) -> str:
        return f"Payslip {self.payslip_number} (v{self.version}) - {self.employee.employee_id}"


class PayslipComponentDetail(BaseModel):
    """Snapshot line item component breakdown for a Payslip."""

    payslip = models.ForeignKey(
        Payslip,
        on_delete=models.CASCADE,
        related_name="components",
        help_text=_("Parent payslip."),
    )
    component_name = models.CharField(
        max_length=150,
        help_text=_("Name of salary component."),
    )
    component_code = models.CharField(
        max_length=50,
        help_text=_("Code of salary component."),
    )
    component_type = models.CharField(
        max_length=50,
        choices=ComponentType.choices,
        default=ComponentType.EARNING,
        help_text=_("Component classification."),
    )
    amount = models.DecimalField(
        max_digits=14,
        decimal_places=2,
        default=Decimal("0.00"),
        help_text=_("Line item component amount."),
    )

    class Meta:
        verbose_name = _("Payslip Component Detail")
        verbose_name_plural = _("Payslip Component Details")

    def __str__(self) -> str:
        return f"{self.component_code}: {self.amount}"


class SalaryDistribution(BaseModel):
    """Salary disbursement execution and tracking record."""

    organization = models.ForeignKey(
        Organization,
        on_delete=models.PROTECT,
        related_name="salary_distributions",
        help_text=_("Associated organization."),
    )
    payroll_run = models.ForeignKey(
        PayrollRun,
        on_delete=models.PROTECT,
        related_name="distributions",
        help_text=_("Associated finalized payroll run."),
    )
    method = models.CharField(
        max_length=50,
        choices=DistributionMethod.choices,
        default=DistributionMethod.BANK_TRANSFER,
        help_text=_("Payment disbursement method."),
    )
    status = models.CharField(
        max_length=50,
        choices=DistributionStatus.choices,
        default=DistributionStatus.PENDING,
        help_text=_("Disbursement status."),
    )
    total_amount = models.DecimalField(
        max_digits=16,
        decimal_places=2,
        default=Decimal("0.00"),
        help_text=_("Total disbursement amount."),
    )
    scheduled_date = models.DateField(
        help_text=_("Scheduled disbursement date."),
    )
    completed_date = models.DateField(
        null=True,
        blank=True,
        help_text=_("Actual date disbursement completed."),
    )
    failure_reason = models.TextField(
        blank=True,
        help_text=_("Reason if disbursement batch failed."),
    )

    class Meta:
        verbose_name = _("Salary Distribution")
        verbose_name_plural = _("Salary Distributions")
        indexes = [
            models.Index(fields=["payroll_run", "status"], name="idx_dist_run_status"),
        ]

    def __str__(self) -> str:
        return f"Distribution ({self.method}) Run: {self.payroll_run.name} [{self.status}]"


class RetroactiveAdjustment(BaseModel):
    """Arrears, recoveries, and backdated adjustments for employee payroll."""

    organization = models.ForeignKey(
        Organization,
        on_delete=models.PROTECT,
        related_name="retroactive_adjustments",
        help_text=_("Associated organization."),
    )
    employee = models.ForeignKey(
        Employee,
        on_delete=models.PROTECT,
        related_name="retroactive_adjustments",
        help_text=_("Associated employee."),
    )
    category = models.CharField(
        max_length=50,
        choices=AdjustmentCategory.choices,
        default=AdjustmentCategory.ARREARS,
        help_text=_("Category of adjustment."),
    )
    amount = models.DecimalField(
        max_digits=14,
        decimal_places=2,
        default=Decimal("0.00"),
        help_text=_("Adjustment amount (positive for arrears/earnings, negative for recovery)."),
    )
    effective_date = models.DateField(
        help_text=_("Effective historical date for calculation."),
    )
    reason = models.TextField(
        help_text=_("Explanation or justification for retroactive adjustment."),
    )
    is_processed = models.BooleanField(
        default=False,
        help_text=_("Whether adjustment has been consumed in a payroll run."),
    )

    class Meta:
        verbose_name = _("Retroactive Adjustment")
        verbose_name_plural = _("Retroactive Adjustments")
        indexes = [
            models.Index(fields=["employee", "is_processed"], name="idx_retro_emp_proc"),
        ]

    def __str__(self) -> str:
        return f"RetroAdjustment ({self.category}) {self.employee.employee_id}: {self.amount}"


class CompensationHistory(BaseModel):
    """Immutable ledger recording historical total compensation snapshots for an employee."""

    organization = models.ForeignKey(
        Organization,
        on_delete=models.PROTECT,
        related_name="compensation_histories",
        help_text=_("Associated organization."),
    )
    employee = models.ForeignKey(
        Employee,
        on_delete=models.PROTECT,
        related_name="compensation_histories",
        help_text=_("Associated employee."),
    )
    annual_ctc = models.DecimalField(
        max_digits=14,
        decimal_places=2,
        default=Decimal("0.00"),
        help_text=_("Annual CTC snapshot."),
    )
    monthly_basic = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=Decimal("0.00"),
        help_text=_("Monthly basic snapshot."),
    )
    effective_date = models.DateField(
        help_text=_("Effective date of compensation change."),
    )
    revision_reason = models.CharField(
        max_length=255,
        blank=True,
        help_text=_("Reason for compensation change."),
    )

    class Meta:
        verbose_name = _("Compensation History")
        verbose_name_plural = _("Compensation Histories")
        indexes = [
            models.Index(fields=["employee", "effective_date"], name="idx_comphist_emp_date"),
        ]

    def __str__(self) -> str:
        return f"CompHistory {self.employee.employee_id}: CTC={self.annual_ctc} ({self.effective_date})"


# ── Payroll Compliance & Statutory Engine Models ────────────────────────────


class ComplianceRuleConfig(BaseModel):
    """Pluggable country/state statutory rule definition container."""

    organization = models.ForeignKey(
        Organization,
        on_delete=models.PROTECT,
        related_name="compliance_rule_configs",
        help_text=_("Associated organization."),
    )
    country_code = models.CharField(
        max_length=10,
        default="IN",
        help_text=_("ISO 2-letter country code (e.g. IN, US, UK)."),
    )
    state_code = models.CharField(
        max_length=50,
        blank=True,
        help_text=_("State or regional jurisdiction code."),
    )
    rule_code = models.CharField(
        max_length=50,
        help_text=_("Unique statutory rule identifier code."),
    )
    name = models.CharField(
        max_length=150,
        help_text=_("Human-readable rule name."),
    )
    min_wage_limit = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=Decimal("0.00"),
        help_text=_("Statutory minimum wage threshold."),
    )
    max_contribution_cap = models.DecimalField(
        max_digits=14,
        decimal_places=2,
        default=Decimal("0.00"),
        help_text=_("Statutory contribution ceiling cap."),
    )
    effective_date = models.DateField(
        help_text=_("Effective start date for rule application."),
    )
    is_active = models.BooleanField(
        default=True,
        help_text=_("Whether rule configuration is active."),
    )

    class Meta:
        verbose_name = _("Compliance Rule Config")
        verbose_name_plural = _("Compliance Rule Configs")
        unique_together = ("organization", "country_code", "state_code", "rule_code")

    def __str__(self) -> str:
        return f"{self.country_code}-{self.rule_code} ({self.name})"


class ComplianceException(BaseModel):
    """Exception record for calculation flags, cap breaches, and overrides."""

    organization = models.ForeignKey(
        Organization,
        on_delete=models.PROTECT,
        related_name="compliance_exceptions",
        help_text=_("Associated organization."),
    )
    payroll_run = models.ForeignKey(
        PayrollRun,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="compliance_exceptions",
        help_text=_("Associated payroll run."),
    )
    employee = models.ForeignKey(
        Employee,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="compliance_exceptions",
        help_text=_("Associated employee if applicable."),
    )
    severity = models.CharField(
        max_length=50,
        choices=ComplianceExceptionSeverity.choices,
        default=ComplianceExceptionSeverity.WARNING,
        help_text=_("Severity classification."),
    )
    rule_code = models.CharField(
        max_length=50,
        help_text=_("Violated statutory rule code."),
    )
    description = models.TextField(
        help_text=_("Detailed description of compliance exception."),
    )
    is_overridden = models.BooleanField(
        default=False,
        help_text=_("Whether exception was manually overridden by an authorized user."),
    )
    overridden_by_user_id = models.CharField(
        max_length=100,
        blank=True,
        help_text=_("User ID who performed manual override."),
    )
    override_reason = models.TextField(
        blank=True,
        help_text=_("Justification for manual override."),
    )

    class Meta:
        verbose_name = _("Compliance Exception")
        verbose_name_plural = _("Compliance Exceptions")
        indexes = [
            models.Index(fields=["payroll_run", "severity"], name="idx_compexcep_run_sev"),
        ]

    def __str__(self) -> str:
        return f"[{self.severity}] {self.rule_code}: {self.description[:50]}"


class ComplianceReport(BaseModel):
    """Snapshot record of generated statutory compliance report aggregations."""

    organization = models.ForeignKey(
        Organization,
        on_delete=models.PROTECT,
        related_name="compliance_reports",
        help_text=_("Associated organization."),
    )
    report_type = models.CharField(
        max_length=50,
        choices=ComplianceReportType.choices,
        default=ComplianceReportType.TAX_SUMMARY,
        help_text=_("Classification of compliance report."),
    )
    title = models.CharField(
        max_length=200,
        help_text=_("Human-readable report title."),
    )
    start_date = models.DateField(
        help_text=_("Reporting period start date."),
    )
    end_date = models.DateField(
        help_text=_("Reporting period end date."),
    )
    summary_json = models.JSONField(
        default=dict,
        help_text=_("Structured report aggregation metrics."),
    )

    class Meta:
        verbose_name = _("Compliance Report")
        verbose_name_plural = _("Compliance Reports")

    def __str__(self) -> str:
        return f"{self.title} ({self.start_date} to {self.end_date})"


class GovernmentFilingRecord(BaseModel):
    """Statutory government filing batch tracking record."""

    organization = models.ForeignKey(
        Organization,
        on_delete=models.PROTECT,
        related_name="government_filings",
        help_text=_("Associated organization."),
    )
    filing_type = models.CharField(
        max_length=50,
        choices=StatutoryFilingType.choices,
        default=StatutoryFilingType.MONTHLY_TAX_RETURN,
        help_text=_("Type of statutory filing."),
    )
    period_name = models.CharField(
        max_length=50,
        help_text=_("Filing period identifier (e.g. 2026-Q3, 2026-08)."),
    )
    status = models.CharField(
        max_length=50,
        choices=ComplianceStatus.choices,
        default=ComplianceStatus.COMPLIANT,
        help_text=_("Current status of filing."),
    )
    total_tax_amount = models.DecimalField(
        max_digits=16,
        decimal_places=2,
        default=Decimal("0.00"),
        help_text=_("Aggregate tax amount in filing."),
    )
    total_contribution_amount = models.DecimalField(
        max_digits=16,
        decimal_places=2,
        default=Decimal("0.00"),
        help_text=_("Aggregate contribution amount in filing."),
    )
    filing_reference_number = models.CharField(
        max_length=100,
        blank=True,
        help_text=_("Official government acknowledgment/reference ID."),
    )

    class Meta:
        verbose_name = _("Government Filing Record")
        verbose_name_plural = _("Government Filing Records")

    def __str__(self) -> str:
        return f"Filing ({self.filing_type}) {self.period_name} [{self.status}]"


# ── Payroll Analytics, Executive Reporting & Cost Intelligence Models ────────


class PayrollAnalyticsSnapshot(BaseModel):
    """Pre-aggregated periodic analytics metrics snapshot record."""

    organization = models.ForeignKey(
        Organization,
        on_delete=models.PROTECT,
        related_name="payroll_analytics_snapshots",
        help_text=_("Associated organization."),
    )
    branch = models.ForeignKey(
        Branch,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="payroll_analytics_snapshots",
        help_text=_("Associated branch filter."),
    )
    department = models.ForeignKey(
        Department,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="payroll_analytics_snapshots",
        help_text=_("Associated department filter."),
    )
    period_name = models.CharField(
        max_length=50,
        help_text=_("Period designation (e.g. 2026-08, 2026-Q3, 2026)."),
    )
    granularity = models.CharField(
        max_length=50,
        choices=AnalyticsGranularity.choices,
        default=AnalyticsGranularity.MONTHLY,
        help_text=_("Temporal granularity."),
    )
    total_employees = models.PositiveIntegerField(
        default=0,
        help_text=_("Headcount in snapshot."),
    )
    total_gross = models.DecimalField(
        max_digits=16,
        decimal_places=2,
        default=Decimal("0.00"),
        help_text=_("Total gross salary."),
    )
    total_deductions = models.DecimalField(
        max_digits=16,
        decimal_places=2,
        default=Decimal("0.00"),
        help_text=_("Total deductions."),
    )
    total_employer_contributions = models.DecimalField(
        max_digits=16,
        decimal_places=2,
        default=Decimal("0.00"),
        help_text=_("Total employer statutory contributions."),
    )
    total_net = models.DecimalField(
        max_digits=16,
        decimal_places=2,
        default=Decimal("0.00"),
        help_text=_("Total net salary disbursement."),
    )
    average_salary = models.DecimalField(
        max_digits=14,
        decimal_places=2,
        default=Decimal("0.00"),
        help_text=_("Mean employee salary."),
    )
    median_salary = models.DecimalField(
        max_digits=14,
        decimal_places=2,
        default=Decimal("0.00"),
        help_text=_("Median employee salary."),
    )
    overtime_cost = models.DecimalField(
        max_digits=14,
        decimal_places=2,
        default=Decimal("0.00"),
        help_text=_("Total overtime expenditure."),
    )

    class Meta:
        verbose_name = _("Payroll Analytics Snapshot")
        verbose_name_plural = _("Payroll Analytics Snapshots")
        indexes = [
            models.Index(fields=["organization", "period_name"], name="idx_payanal_org_period"),
        ]

    def __str__(self) -> str:
        return f"Analytics {self.period_name} ({self.granularity}) Net: {self.total_net}"


class WorkforceCostIntelligence(BaseModel):
    """Departmental, branch, and designation workforce cost intelligence metrics."""

    organization = models.ForeignKey(
        Organization,
        on_delete=models.PROTECT,
        related_name="workforce_cost_metrics",
        help_text=_("Associated organization."),
    )
    department = models.ForeignKey(
        Department,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="cost_metrics",
        help_text=_("Department cost center."),
    )
    branch = models.ForeignKey(
        Branch,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="cost_metrics",
        help_text=_("Branch location cost center."),
    )
    designation = models.ForeignKey(
        Designation,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="cost_metrics",
        help_text=_("Designation cost tier."),
    )
    period_name = models.CharField(
        max_length=50,
        help_text=_("Period identifier."),
    )
    headcount = models.PositiveIntegerField(
        default=0,
        help_text=_("Employee count in cost group."),
    )
    total_cost = models.DecimalField(
        max_digits=16,
        decimal_places=2,
        default=Decimal("0.00"),
        help_text=_("Total workforce cost (gross + employer statutory)."),
    )
    cost_per_employee = models.DecimalField(
        max_digits=14,
        decimal_places=2,
        default=Decimal("0.00"),
        help_text=_("Average cost per employee."),
    )

    class Meta:
        verbose_name = _("Workforce Cost Intelligence")
        verbose_name_plural = _("Workforce Cost Intelligence Metrics")
        indexes = [
            models.Index(fields=["organization", "period_name"], name="idx_costintel_org_period"),
        ]

    def __str__(self) -> str:
        return f"CostIntel {self.period_name}: Total {self.total_cost}"


class PayrollExecutiveDashboard(BaseModel):
    """Pre-compiled dashboard metric snapshot for CEO, HR, and Finance views."""

    organization = models.ForeignKey(
        Organization,
        on_delete=models.PROTECT,
        related_name="executive_dashboards",
        help_text=_("Associated organization."),
    )
    dashboard_type = models.CharField(
        max_length=50,
        choices=DashboardType.choices,
        default=DashboardType.CEO,
        help_text=_("Target executive view type."),
    )
    metrics_json = models.JSONField(
        default=dict,
        help_text=_("Structured metric dictionary tailored for frontend dashboards."),
    )
    refreshed_at = models.DateTimeField(
        auto_now=True,
        help_text=_("Timestamp when metrics were last calculated."),
    )

    class Meta:
        verbose_name = _("Payroll Executive Dashboard")
        verbose_name_plural = _("Payroll Executive Dashboards")

    def __str__(self) -> str:
        return f"ExecutiveDashboard [{self.dashboard_type}] ({self.organization.name})"



