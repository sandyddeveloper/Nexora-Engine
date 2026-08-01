"""DRF Serializers for the Payroll Foundation Engine."""

from rest_framework import serializers

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
    PayrollItemComponent,
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


class SalaryComponentSerializer(serializers.ModelSerializer):
    organization_name = serializers.CharField(source="organization.name", read_only=True)

    class Meta:
        model = SalaryComponent
        fields = [
            "id",
            "organization",
            "organization_name",
            "name",
            "code",
            "component_type",
            "calculation_type",
            "default_amount_percentage",
            "formula_expression",
            "is_taxable",
            "is_recurring",
            "is_statutory",
            "is_active",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "created_at", "updated_at"]


class SalaryTemplateComponentSerializer(serializers.ModelSerializer):
    salary_component_code = serializers.CharField(source="salary_component.code", read_only=True)
    salary_component_name = serializers.CharField(source="salary_component.name", read_only=True)

    class Meta:
        model = SalaryTemplateComponent
        fields = [
            "id",
            "salary_component",
            "salary_component_code",
            "salary_component_name",
            "calculation_type",
            "amount_percentage",
        ]
        read_only_fields = ["id"]


class SalaryTemplateSerializer(serializers.ModelSerializer):
    organization_name = serializers.CharField(source="organization.name", read_only=True)
    components = SalaryTemplateComponentSerializer(many=True, read_only=True)

    class Meta:
        model = SalaryTemplate
        fields = [
            "id",
            "organization",
            "organization_name",
            "name",
            "code",
            "description",
            "currency",
            "is_active",
            "components",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "created_at", "updated_at"]


class EmployeePayrollProfileSerializer(serializers.ModelSerializer):
    employee_code = serializers.CharField(source="employee.employee_id", read_only=True)
    employee_name = serializers.CharField(source="employee.display_name", read_only=True)

    class Meta:
        model = EmployeePayrollProfile
        fields = [
            "id",
            "employee",
            "employee_code",
            "employee_name",
            "organization",
            "status",
            "tax_regime",
            "pf_account_number",
            "esi_account_number",
            "pan_number",
            "bank_account_number_placeholder",
            "bank_ifsc_placeholder",
            "is_pf_eligible",
            "is_esi_eligible",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "created_at", "updated_at"]


class EmployeeSalaryComponentSerializer(serializers.ModelSerializer):
    salary_component_code = serializers.CharField(source="salary_component.code", read_only=True)
    salary_component_name = serializers.CharField(source="salary_component.name", read_only=True)

    class Meta:
        model = EmployeeSalaryComponent
        fields = [
            "id",
            "salary_component",
            "salary_component_code",
            "salary_component_name",
            "monthly_amount",
            "annual_amount",
        ]
        read_only_fields = ["id"]


class EmployeeSalaryStructureSerializer(serializers.ModelSerializer):
    employee_code = serializers.CharField(source="employee.employee_id", read_only=True)
    employee_name = serializers.CharField(source="employee.display_name", read_only=True)
    components = EmployeeSalaryComponentSerializer(many=True, read_only=True)

    class Meta:
        model = EmployeeSalaryStructure
        fields = [
            "id",
            "employee",
            "employee_code",
            "employee_name",
            "organization",
            "salary_template",
            "version",
            "annual_ctc",
            "monthly_basic",
            "gross_salary_placeholder",
            "net_salary_placeholder",
            "currency",
            "effective_date",
            "is_active",
            "components",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "version", "created_at", "updated_at"]


class SalaryRevisionHistorySerializer(serializers.ModelSerializer):
    employee_code = serializers.CharField(source="employee.employee_id", read_only=True)

    class Meta:
        model = SalaryRevisionHistory
        fields = [
            "id",
            "employee",
            "employee_code",
            "previous_salary_structure",
            "new_salary_structure",
            "previous_ctc",
            "new_ctc",
            "increment_percentage",
            "effective_date",
            "revision_reason",
            "approved_by",
            "created_at",
        ]
        read_only_fields = ["id", "created_at"]


class PayrollPolicySerializer(serializers.ModelSerializer):
    organization_name = serializers.CharField(source="organization.name", read_only=True)

    class Meta:
        model = PayrollPolicy
        fields = [
            "id",
            "organization",
            "organization_name",
            "branch",
            "department",
            "designation",
            "name",
            "code",
            "cutoff_day_of_month",
            "pay_day_of_month",
            "is_payroll_locked",
            "leave_deduction_enabled",
            "overtime_policy_placeholder",
            "is_default",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "created_at", "updated_at"]


class PayrollCycleSerializer(serializers.ModelSerializer):
    organization_name = serializers.CharField(source="organization.name", read_only=True)

    class Meta:
        model = PayrollCycle
        fields = [
            "id",
            "organization",
            "organization_name",
            "name",
            "frequency",
            "start_date",
            "end_date",
            "cutoff_date",
            "processing_date",
            "payment_date",
            "is_closed",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "created_at", "updated_at"]


class SalaryAssignmentSerializer(serializers.Serializer):
    """Serializer for assigning/revising salary structure for an employee."""

    employee_id = serializers.UUIDField()
    annual_ctc = serializers.DecimalField(max_digits=14, decimal_places=2)
    effective_date = serializers.DateField()
    salary_template_id = serializers.UUIDField(required=False, allow_null=True)
    currency = serializers.CharField(default="INR")
    revision_reason = serializers.CharField(required=False, allow_blank=True, default="Salary Assignment")
    components_breakup = serializers.ListField(child=serializers.DictField(), required=False, default=list)


# ── Payroll Processing & Run Engine Serializers ──────────────────────────────


class PayrollRunSerializer(serializers.ModelSerializer):
    organization_name = serializers.CharField(source="organization.name", read_only=True)
    cycle_name = serializers.CharField(source="payroll_cycle.name", read_only=True)

    class Meta:
        model = PayrollRun
        fields = [
            "id",
            "organization",
            "organization_name",
            "payroll_cycle",
            "cycle_name",
            "name",
            "status",
            "total_employees",
            "total_gross",
            "total_deductions",
            "total_employer_contributions",
            "total_net",
            "calculated_at",
            "finalized_at",
            "is_locked",
            "created_at",
            "updated_at",
        ]
        read_only_fields = [
            "id",
            "status",
            "total_employees",
            "total_gross",
            "total_deductions",
            "total_employer_contributions",
            "total_net",
            "calculated_at",
            "finalized_at",
            "is_locked",
            "created_at",
            "updated_at",
        ]


class PayrollItemSerializer(serializers.ModelSerializer):
    employee_code = serializers.CharField(source="employee.employee_id", read_only=True)
    employee_name = serializers.CharField(source="employee.display_name", read_only=True)

    class Meta:
        model = PayrollItem
        fields = [
            "id",
            "payroll_run",
            "employee",
            "employee_code",
            "employee_name",
            "status",
            "total_working_days",
            "days_present",
            "days_absent",
            "paid_leave_days",
            "unpaid_leave_days",
            "overtime_hours",
            "earned_basic",
            "total_earnings",
            "total_deductions",
            "employer_pf",
            "employer_esi",
            "gross_salary",
            "net_salary",
            "error_message",
            "created_at",
        ]
        read_only_fields = ["id", "created_at"]


class PayrollApprovalSerializer(serializers.ModelSerializer):
    approver_name = serializers.CharField(source="approver.display_name", read_only=True)

    class Meta:
        model = PayrollApproval
        fields = [
            "id",
            "payroll_run",
            "level",
            "decision",
            "approver",
            "approver_name",
            "comments",
            "created_at",
        ]
        read_only_fields = ["id", "created_at"]


class PayrollRunCreateSerializer(serializers.Serializer):
    organization_id = serializers.UUIDField()
    payroll_cycle_id = serializers.UUIDField()
    name = serializers.CharField(max_length=200)


class PayrollApprovalRequestSerializer(serializers.Serializer):
    approver_id = serializers.UUIDField()
    level = serializers.ChoiceField(choices=["LEVEL_1_FINANCE", "LEVEL_2_HR", "LEVEL_3_MANAGEMENT"], default="LEVEL_1_FINANCE")
    comments = serializers.CharField(required=False, allow_blank=True, default="")


class PayrollActionReasonSerializer(serializers.Serializer):
    reason = serializers.CharField(required=True)


# ── Payslip, Distribution & Compensation Serializers ─────────────────────────


class PayslipComponentDetailSerializer(serializers.ModelSerializer):
    class Meta:
        model = PayslipComponentDetail
        fields = [
            "id",
            "component_name",
            "component_code",
            "component_type",
            "amount",
        ]
        read_only_fields = ["id"]


class PayslipSerializer(serializers.ModelSerializer):
    employee_code = serializers.CharField(source="employee.employee_id", read_only=True)
    employee_name = serializers.CharField(source="employee.display_name", read_only=True)
    run_name = serializers.CharField(source="payroll_run.name", read_only=True)
    components = PayslipComponentDetailSerializer(many=True, read_only=True)

    class Meta:
        model = Payslip
        fields = [
            "id",
            "organization",
            "employee",
            "employee_code",
            "employee_name",
            "payroll_run",
            "run_name",
            "payslip_number",
            "payslip_type",
            "status",
            "version",
            "issue_date",
            "gross_salary",
            "total_deductions",
            "net_salary",
            "download_token",
            "components",
            "created_at",
            "updated_at",
        ]
        read_only_fields = [
            "id",
            "payslip_number",
            "version",
            "download_token",
            "created_at",
            "updated_at",
        ]


class SalaryDistributionSerializer(serializers.ModelSerializer):
    run_name = serializers.CharField(source="payroll_run.name", read_only=True)

    class Meta:
        model = SalaryDistribution
        fields = [
            "id",
            "organization",
            "payroll_run",
            "run_name",
            "method",
            "status",
            "total_amount",
            "scheduled_date",
            "completed_date",
            "failure_reason",
            "created_at",
        ]
        read_only_fields = ["id", "created_at"]


class RetroactiveAdjustmentSerializer(serializers.ModelSerializer):
    employee_code = serializers.CharField(source="employee.employee_id", read_only=True)

    class Meta:
        model = RetroactiveAdjustment
        fields = [
            "id",
            "organization",
            "employee",
            "employee_code",
            "category",
            "amount",
            "effective_date",
            "reason",
            "is_processed",
            "created_at",
        ]
        read_only_fields = ["id", "is_processed", "created_at"]


class CompensationHistorySerializer(serializers.ModelSerializer):
    employee_code = serializers.CharField(source="employee.employee_id", read_only=True)

    class Meta:
        model = CompensationHistory
        fields = [
            "id",
            "organization",
            "employee",
            "employee_code",
            "annual_ctc",
            "monthly_basic",
            "effective_date",
            "revision_reason",
            "created_at",
        ]
        read_only_fields = ["id", "created_at"]


class PayslipBulkGenerateSerializer(serializers.Serializer):
    payroll_run_id = serializers.UUIDField()


class SalaryDistributionCreateSerializer(serializers.Serializer):
    payroll_run_id = serializers.UUIDField()
    method = serializers.ChoiceField(
        choices=["BANK_TRANSFER", "CASH", "CHEQUE", "WALLET", "UPI"], default="BANK_TRANSFER"
    )
    scheduled_date = serializers.DateField()


class RetroactiveAdjustmentCreateSerializer(serializers.Serializer):
    employee_id = serializers.UUIDField()
    category = serializers.ChoiceField(
        choices=["ARREARS", "RECOVERY", "SALARY_DIFFERENCE", "ATTENDANCE_CORRECTION", "LEAVE_ADJUSTMENT", "MANUAL"],
        default="ARREARS",
    )
    amount = serializers.DecimalField(max_digits=14, decimal_places=2)
    effective_date = serializers.DateField()
    reason = serializers.CharField(required=True)


# ── Payroll Compliance & Statutory Serializers ───────────────────────────────


class ComplianceRuleConfigSerializer(serializers.ModelSerializer):
    class Meta:
        model = ComplianceRuleConfig
        fields = [
            "id",
            "organization",
            "country_code",
            "state_code",
            "rule_code",
            "name",
            "min_wage_limit",
            "max_contribution_cap",
            "effective_date",
            "is_active",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "created_at", "updated_at"]


class ComplianceExceptionSerializer(serializers.ModelSerializer):
    employee_code = serializers.CharField(source="employee.employee_id", read_only=True)

    class Meta:
        model = ComplianceException
        fields = [
            "id",
            "organization",
            "payroll_run",
            "employee",
            "employee_code",
            "severity",
            "rule_code",
            "description",
            "is_overridden",
            "overridden_by_user_id",
            "override_reason",
            "created_at",
        ]
        read_only_fields = ["id", "is_overridden", "overridden_by_user_id", "override_reason", "created_at"]


class ComplianceReportSerializer(serializers.ModelSerializer):
    class Meta:
        model = ComplianceReport
        fields = [
            "id",
            "organization",
            "report_type",
            "title",
            "start_date",
            "end_date",
            "summary_json",
            "created_at",
        ]
        read_only_fields = ["id", "created_at"]


class GovernmentFilingRecordSerializer(serializers.ModelSerializer):
    class Meta:
        model = GovernmentFilingRecord
        fields = [
            "id",
            "organization",
            "filing_type",
            "period_name",
            "status",
            "total_tax_amount",
            "total_contribution_amount",
            "filing_reference_number",
            "created_at",
        ]
        read_only_fields = ["id", "created_at"]


class ComplianceValidateRequestSerializer(serializers.Serializer):
    payroll_run_id = serializers.UUIDField()


class ComplianceOverrideRequestSerializer(serializers.Serializer):
    exception_id = serializers.UUIDField()
    override_reason = serializers.CharField(required=True)


class ComplianceReportCreateSerializer(serializers.Serializer):
    organization_id = serializers.UUIDField()
    report_type = serializers.ChoiceField(
        choices=["TAX_SUMMARY", "CONTRIBUTION_SUMMARY", "PAYROLL_COMPLIANCE", "ORG_COMPLIANCE", "AUDIT_REPORT"],
        default="TAX_SUMMARY",
    )
    title = serializers.CharField(max_length=200)
    start_date = serializers.DateField()
    end_date = serializers.DateField()


class GovernmentFilingCreateSerializer(serializers.Serializer):
    organization_id = serializers.UUIDField()
    filing_type = serializers.ChoiceField(
        choices=["MONTHLY_TAX_RETURN", "PF_ECR_FILING", "ESI_RETURNS", "ANNUAL_TAX_CERTIFICATE"],
        default="MONTHLY_TAX_RETURN",
    )
    period_name = serializers.CharField(max_length=50)
    total_tax_amount = serializers.DecimalField(max_digits=16, decimal_places=2)
    total_contribution_amount = serializers.DecimalField(max_digits=16, decimal_places=2)
    filing_reference_number = serializers.CharField(required=False, allow_blank=True, default="")


# ── Payroll Analytics & Executive Reporting Serializers ──────────────────────


class PayrollAnalyticsSnapshotSerializer(serializers.ModelSerializer):
    class Meta:
        model = PayrollAnalyticsSnapshot
        fields = [
            "id",
            "organization",
            "branch",
            "department",
            "period_name",
            "granularity",
            "total_employees",
            "total_gross",
            "total_deductions",
            "total_employer_contributions",
            "total_net",
            "average_salary",
            "median_salary",
            "overtime_cost",
            "created_at",
        ]
        read_only_fields = ["id", "created_at"]


class WorkforceCostIntelligenceSerializer(serializers.ModelSerializer):
    department_name = serializers.CharField(source="department.name", read_only=True)
    branch_name = serializers.CharField(source="branch.name", read_only=True)

    class Meta:
        model = WorkforceCostIntelligence
        fields = [
            "id",
            "organization",
            "department",
            "department_name",
            "branch",
            "branch_name",
            "designation",
            "period_name",
            "headcount",
            "total_cost",
            "cost_per_employee",
            "created_at",
        ]
        read_only_fields = ["id", "created_at"]


class PayrollExecutiveDashboardSerializer(serializers.ModelSerializer):
    class Meta:
        model = PayrollExecutiveDashboard
        fields = [
            "id",
            "organization",
            "dashboard_type",
            "metrics_json",
            "refreshed_at",
        ]
        read_only_fields = ["id", "refreshed_at"]


class AnalyticsSnapshotCreateSerializer(serializers.Serializer):
    organization_id = serializers.UUIDField()
    period_name = serializers.CharField(max_length=50)
    granularity = serializers.ChoiceField(
        choices=["DAILY", "MONTHLY", "QUARTERLY", "YEARLY"],
        default="MONTHLY",
    )


class DashboardRefreshRequestSerializer(serializers.Serializer):
    organization_id = serializers.UUIDField()
    dashboard_type = serializers.ChoiceField(
        choices=["CEO", "HR", "FINANCE", "PAYROLL", "ORGANIZATION", "BRANCH", "DEPARTMENT"],
        default="CEO",
    )

    period_name = serializers.CharField(max_length=50)
    total_tax_amount = serializers.DecimalField(max_digits=16, decimal_places=2)
    total_contribution_amount = serializers.DecimalField(max_digits=16, decimal_places=2)
    filing_reference_number = serializers.CharField(required=False, allow_blank=True, default="")



