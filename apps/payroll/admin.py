"""Django Admin registration for the Payroll Foundation Engine."""

from django.contrib import admin

from .models import (
    CompensationHistory,
    ComplianceException,
    ComplianceReport,
    ComplianceRuleConfig,
    EmployeePayrollProfile,
    EmployeeSalaryComponent,
    EmployeeSalaryStructure,
    GovernmentFilingRecord,
    PayrollAnalyticsSnapshot,
    PayrollApproval,
    PayrollCycle,
    PayrollExecutiveDashboard,
    PayrollItem,
    PayrollLock,
    PayrollPolicy,
    PayrollRun,
    Payslip,
    PayslipComponentDetail,
    RetroactiveAdjustment,
    SalaryComponent,
    SalaryDistribution,
    SalaryRevisionHistory,
    SalaryTemplate,
    SalaryTemplateComponent,
    StatutoryContributionConfig,
    TaxSlabConfig,
    WorkforceCostIntelligence,
)


class SalaryTemplateComponentInline(admin.TabularInline):
    model = SalaryTemplateComponent
    extra = 1


class EmployeeSalaryComponentInline(admin.TabularInline):
    model = EmployeeSalaryComponent
    extra = 1


@admin.register(SalaryComponent)
class SalaryComponentAdmin(admin.ModelAdmin):
    list_display = ("name", "code", "organization", "component_type", "calculation_type", "is_taxable", "is_statutory", "is_active")
    list_filter = ("component_type", "calculation_type", "is_taxable", "is_statutory", "is_active")
    search_fields = ("name", "code", "organization__name")


@admin.register(SalaryTemplate)
class SalaryTemplateAdmin(admin.ModelAdmin):
    list_display = ("name", "code", "organization", "currency", "is_active")
    list_filter = ("is_active", "currency")
    search_fields = ("name", "code", "organization__name")
    inlines = [SalaryTemplateComponentInline]


@admin.register(EmployeePayrollProfile)
class EmployeePayrollProfileAdmin(admin.ModelAdmin):
    list_display = ("employee", "organization", "status", "tax_regime", "is_pf_eligible", "is_esi_eligible")
    list_filter = ("status", "tax_regime", "is_pf_eligible", "is_esi_eligible")
    search_fields = ("employee__employee_id", "employee__first_name", "employee__last_name", "organization__name")


@admin.register(EmployeeSalaryStructure)
class EmployeeSalaryStructureAdmin(admin.ModelAdmin):
    list_display = ("employee", "organization", "version", "annual_ctc", "effective_date", "is_active")
    list_filter = ("is_active", "version")
    search_fields = ("employee__employee_id", "organization__name")
    inlines = [EmployeeSalaryComponentInline]


@admin.register(SalaryRevisionHistory)
class SalaryRevisionHistoryAdmin(admin.ModelAdmin):
    list_display = ("employee", "organization", "previous_ctc", "new_ctc", "increment_percentage", "effective_date")
    search_fields = ("employee__employee_id", "organization__name")


@admin.register(PayrollPolicy)
class PayrollPolicyAdmin(admin.ModelAdmin):
    list_display = ("name", "code", "organization", "cutoff_day_of_month", "pay_day_of_month", "is_payroll_locked", "is_default")
    list_filter = ("is_payroll_locked", "is_default")
    search_fields = ("name", "code", "organization__name")


@admin.register(PayrollCycle)
class PayrollCycleAdmin(admin.ModelAdmin):
    list_display = ("name", "organization", "frequency", "start_date", "end_date", "cutoff_date", "is_closed")
    list_filter = ("frequency", "is_closed")
    search_fields = ("name", "organization__name")


@admin.register(StatutoryContributionConfig)
class StatutoryContributionConfigAdmin(admin.ModelAdmin):
    list_display = ("name", "organization", "employee_pf_rate_pct", "employer_pf_rate_pct", "employee_esi_rate_pct", "is_active")
    list_filter = ("is_active",)


@admin.register(TaxSlabConfig)
class TaxSlabConfigAdmin(admin.ModelAdmin):
    list_display = ("financial_year", "organization", "tax_regime", "min_income", "max_income", "tax_rate_pct")
    list_filter = ("financial_year", "tax_regime")


@admin.register(PayrollRun)
class PayrollRunAdmin(admin.ModelAdmin):
    list_display = ("name", "organization", "status", "total_employees", "total_gross", "total_net", "is_locked", "created_at")
    list_filter = ("status", "is_locked")
    search_fields = ("name", "organization__name")


@admin.register(PayrollItem)
class PayrollItemAdmin(admin.ModelAdmin):
    list_display = ("employee", "payroll_run", "status", "earned_basic", "gross_salary", "net_salary")
    list_filter = ("status",)
    search_fields = ("employee__employee_id", "payroll_run__name")


@admin.register(PayrollApproval)
class PayrollApprovalAdmin(admin.ModelAdmin):
    list_display = ("payroll_run", "level", "decision", "approver", "created_at")
    list_filter = ("level", "decision")


@admin.register(PayrollLock)
class PayrollLockAdmin(admin.ModelAdmin):
    list_display = ("organization", "lock_start_date", "lock_end_date", "attendance_locked", "leave_locked", "payroll_locked")
    list_filter = ("attendance_locked", "leave_locked", "payroll_locked")


@admin.register(Payslip)
class PayslipAdmin(admin.ModelAdmin):
    list_display = ("payslip_number", "employee", "payroll_run", "version", "status", "issue_date", "net_salary")
    list_filter = ("payslip_type", "status", "version")
    search_fields = ("payslip_number", "employee__employee_id")


@admin.register(SalaryDistribution)
class SalaryDistributionAdmin(admin.ModelAdmin):
    list_display = ("payroll_run", "method", "status", "total_amount", "scheduled_date", "completed_date")
    list_filter = ("method", "status")


@admin.register(RetroactiveAdjustment)
class RetroactiveAdjustmentAdmin(admin.ModelAdmin):
    list_display = ("employee", "category", "amount", "effective_date", "is_processed")
    list_filter = ("category", "is_processed")
    search_fields = ("employee__employee_id", "reason")


@admin.register(CompensationHistory)
class CompensationHistoryAdmin(admin.ModelAdmin):
    list_display = ("employee", "annual_ctc", "monthly_basic", "effective_date", "revision_reason")
    search_fields = ("employee__employee_id", "revision_reason")


@admin.register(ComplianceRuleConfig)
class ComplianceRuleConfigAdmin(admin.ModelAdmin):
    list_display = ("rule_code", "name", "organization", "country_code", "state_code", "min_wage_limit", "is_active")
    list_filter = ("country_code", "is_active")
    search_fields = ("rule_code", "name")


@admin.register(ComplianceException)
class ComplianceExceptionAdmin(admin.ModelAdmin):
    list_display = ("rule_code", "organization", "payroll_run", "severity", "is_overridden")
    list_filter = ("severity", "is_overridden")
    search_fields = ("rule_code", "description")


@admin.register(ComplianceReport)
class ComplianceReportAdmin(admin.ModelAdmin):
    list_display = ("title", "organization", "report_type", "start_date", "end_date")
    list_filter = ("report_type",)


@admin.register(GovernmentFilingRecord)
class GovernmentFilingRecordAdmin(admin.ModelAdmin):
    list_display = ("filing_type", "organization", "period_name", "status", "total_tax_amount", "total_contribution_amount")
    list_filter = ("filing_type", "status")


@admin.register(PayrollAnalyticsSnapshot)
class PayrollAnalyticsSnapshotAdmin(admin.ModelAdmin):
    list_display = ("period_name", "organization", "granularity", "total_employees", "total_gross", "total_net", "average_salary")
    list_filter = ("granularity",)


@admin.register(WorkforceCostIntelligence)
class WorkforceCostIntelligenceAdmin(admin.ModelAdmin):
    list_display = ("period_name", "organization", "department", "headcount", "total_cost", "cost_per_employee")


@admin.register(PayrollExecutiveDashboard)
class PayrollExecutiveDashboardAdmin(admin.ModelAdmin):
    list_display = ("dashboard_type", "organization", "refreshed_at")
    list_filter = ("dashboard_type",)




