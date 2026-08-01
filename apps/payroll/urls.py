"""URL pattern routing for payroll app."""

from django.urls import path

from .views import (
    ActiveSalaryStructureAPIView,
    CompensationHistoryAPIView,
    ComplianceExceptionListOverrideAPIView,
    ComplianceReportListGenerateAPIView,
    ComplianceRuleConfigListCreateAPIView,
    ComplianceValidateAPIView,
    EmployeePayrollProfileAPIView,
    ESSPayslipListAPIView,
    ExecutiveDashboardAPIView,
    ExecutiveKPIsAPIView,
    GovernmentFilingListCreateAPIView,
    PayrollAnalyticsSummaryAPIView,
    PayrollCycleListCreateAPIView,
    PayrollExportReportAPIView,
    PayrollForecastDataAPIView,
    PayrollPolicyListCreateAPIView,
    PayrollRunApproveAPIView,
    PayrollRunCalculateAPIView,
    PayrollRunFinalizeAPIView,
    PayrollRunItemsAPIView,
    PayrollRunListCreateAPIView,
    PayrollRunReopenAPIView,
    PayrollRunRollbackAPIView,
    PayrollRunValidateAPIView,
    PayslipDetailAPIView,
    PayslipDownloadAPIView,
    PayslipGenerateBulkAPIView,
    RetroactiveAdjustmentListCreateAPIView,
    SalaryAssignAPIView,
    SalaryComponentListCreateAPIView,
    SalaryDistributionListCreateAPIView,
    SalaryRevisionHistoryAPIView,
    SalaryTemplateListCreateAPIView,
    WorkforceCostIntelligenceAPIView,
)

app_name = "payroll"

urlpatterns = [
    # Salary Component & Template Master Endpoints
    path("components/", SalaryComponentListCreateAPIView.as_view(), name="salary-component-list-create"),
    path("templates/", SalaryTemplateListCreateAPIView.as_view(), name="salary-template-list-create"),
    # Employee Profile & Salary Assignment Endpoints
    path("profiles/", EmployeePayrollProfileAPIView.as_view(), name="employee-payroll-profile"),
    path("structures/assign/", SalaryAssignAPIView.as_view(), name="salary-assign"),
    path("structures/active/", ActiveSalaryStructureAPIView.as_view(), name="active-salary-structure"),
    path("structures/revisions/", SalaryRevisionHistoryAPIView.as_view(), name="salary-revision-history"),
    # Policy & Cycle Endpoints
    path("policies/", PayrollPolicyListCreateAPIView.as_view(), name="payroll-policy-list-create"),
    path("cycles/", PayrollCycleListCreateAPIView.as_view(), name="payroll-cycle-list-create"),
    # Payroll Processing & Run Endpoints
    path("runs/", PayrollRunListCreateAPIView.as_view(), name="payroll-run-list-create"),
    path("runs/<uuid:pk>/calculate/", PayrollRunCalculateAPIView.as_view(), name="payroll-run-calculate"),
    path("runs/<uuid:pk>/validate/", PayrollRunValidateAPIView.as_view(), name="payroll-run-validate"),
    path("runs/<uuid:pk>/approve/", PayrollRunApproveAPIView.as_view(), name="payroll-run-approve"),
    path("runs/<uuid:pk>/finalize/", PayrollRunFinalizeAPIView.as_view(), name="payroll-run-finalize"),
    path("runs/<uuid:pk>/reopen/", PayrollRunReopenAPIView.as_view(), name="payroll-run-reopen"),
    path("runs/<uuid:pk>/rollback/", PayrollRunRollbackAPIView.as_view(), name="payroll-run-rollback"),
    path("runs/<uuid:pk>/items/", PayrollRunItemsAPIView.as_view(), name="payroll-run-items"),
    # Payslip, Distribution & Compensation Endpoints
    path("payslips/generate/", PayslipGenerateBulkAPIView.as_view(), name="payslip-generate-bulk"),
    path("payslips/ess/", ESSPayslipListAPIView.as_view(), name="payslip-ess-list"),
    path("payslips/<uuid:pk>/", PayslipDetailAPIView.as_view(), name="payslip-detail"),
    path("payslips/<uuid:pk>/download/", PayslipDownloadAPIView.as_view(), name="payslip-download"),
    path("distributions/", SalaryDistributionListCreateAPIView.as_view(), name="salary-distribution-list-create"),
    path("retroactive-adjustments/", RetroactiveAdjustmentListCreateAPIView.as_view(), name="retroactive-adjustment-list-create"),
    path("compensation/history/", CompensationHistoryAPIView.as_view(), name="compensation-history"),
    # Payroll Compliance & Statutory Endpoints
    path("compliance/rules/", ComplianceRuleConfigListCreateAPIView.as_view(), name="compliance-rule-config-list-create"),
    path("compliance/validate/", ComplianceValidateAPIView.as_view(), name="compliance-validate"),
    path("compliance/exceptions/", ComplianceExceptionListOverrideAPIView.as_view(), name="compliance-exception-list-override"),
    path("compliance/reports/", ComplianceReportListGenerateAPIView.as_view(), name="compliance-report-list-generate"),
    path("compliance/filings/", GovernmentFilingListCreateAPIView.as_view(), name="government-filing-list-create"),
    # Payroll Analytics, Executive Reporting & Cost Intelligence Endpoints
    path("analytics/summary/", PayrollAnalyticsSummaryAPIView.as_view(), name="analytics-summary"),
    path("analytics/cost-intelligence/", WorkforceCostIntelligenceAPIView.as_view(), name="workforce-cost-intelligence"),
    path("analytics/kpis/", ExecutiveKPIsAPIView.as_view(), name="executive-kpis"),
    path("analytics/dashboards/", ExecutiveDashboardAPIView.as_view(), name="executive-dashboards"),
    path("analytics/forecast-data/", PayrollForecastDataAPIView.as_view(), name="payroll-forecast-data"),
    path("analytics/export/", PayrollExportReportAPIView.as_view(), name="payroll-export-report"),
]
