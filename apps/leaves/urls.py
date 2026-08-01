"""URL pattern routing for leaves app."""

from django.urls import path

from .views import (
    BranchLeaveAnalyticsAPIView,
    DepartmentLeaveAnalyticsAPIView,
    EmployeeLeaveAnalyticsAPIView,
    ExecutiveLeaveDashboardAPIView,
    LeaveAccrualRunAPIView,
    LeaveApplyAPIView,
    LeaveApproveAPIView,
    LeaveBalanceAdjustAPIView,
    LeaveBalanceListInitAPIView,
    LeaveCalendarAPIView,
    LeaveCancelAPIView,
    LeaveCarryForwardRunAPIView,
    LeaveComplianceAPIView,
    LeaveDelegationListCreateAPIView,
    LeaveEligibilityCheckAPIView,
    LeaveExportReportAPIView,
    LeaveForecastAPIView,
    LeaveKPIsAPIView,
    LeaveModifyAPIView,
    LeavePendingApprovalsAPIView,
    LeavePolicyListCreateAPIView,
    LeaveRejectAPIView,
    LeaveRequestListAPIView,
    LeaveSubmitAPIView,
    LeaveTypeListCreateAPIView,
    LeaveWithdrawAPIView,
    LeaveWorkingDaysCheckAPIView,
    ManagerLeaveDashboardAPIView,
    OrganizationLeaveAnalyticsAPIView,
    TeamLeaveAnalyticsAPIView,
)

app_name = "leaves"

urlpatterns = [
    # Foundation Endpoints
    path("types/", LeaveTypeListCreateAPIView.as_view(), name="leave-type-list-create"),
    path("policies/", LeavePolicyListCreateAPIView.as_view(), name="leave-policy-list-create"),
    path("balances/", LeaveBalanceListInitAPIView.as_view(), name="leave-balance-list-init"),
    path("balances/adjust/", LeaveBalanceAdjustAPIView.as_view(), name="leave-balance-adjust"),
    path("accruals/run/", LeaveAccrualRunAPIView.as_view(), name="leave-accrual-run"),
    path("eligibility/check/", LeaveEligibilityCheckAPIView.as_view(), name="leave-eligibility-check"),
    path("carry-forward/run/", LeaveCarryForwardRunAPIView.as_view(), name="leave-carry-forward-run"),
    path("working-days/check/", LeaveWorkingDaysCheckAPIView.as_view(), name="leave-working-days-check"),
    # Workflow Endpoints
    path("requests/", LeaveRequestListAPIView.as_view(), name="leave-request-list"),
    path("requests/apply/", LeaveApplyAPIView.as_view(), name="leave-request-apply"),
    path("requests/<uuid:pk>/submit/", LeaveSubmitAPIView.as_view(), name="leave-request-submit"),
    path("requests/<uuid:pk>/approve/", LeaveApproveAPIView.as_view(), name="leave-request-approve"),
    path("requests/<uuid:pk>/reject/", LeaveRejectAPIView.as_view(), name="leave-request-reject"),
    path("requests/<uuid:pk>/cancel/", LeaveCancelAPIView.as_view(), name="leave-request-cancel"),
    path("requests/<uuid:pk>/withdraw/", LeaveWithdrawAPIView.as_view(), name="leave-request-withdraw"),
    path("requests/<uuid:pk>/modify/", LeaveModifyAPIView.as_view(), name="leave-request-modify"),
    path("approvals/pending/", LeavePendingApprovalsAPIView.as_view(), name="leave-approvals-pending"),
    path("delegations/", LeaveDelegationListCreateAPIView.as_view(), name="leave-delegations"),
    path("calendar/", LeaveCalendarAPIView.as_view(), name="leave-calendar"),
    # Analytics & KPI Endpoints
    path("analytics/employee/", EmployeeLeaveAnalyticsAPIView.as_view(), name="leave-analytics-employee"),
    path("analytics/team/", TeamLeaveAnalyticsAPIView.as_view(), name="leave-analytics-team"),
    path("analytics/department/", DepartmentLeaveAnalyticsAPIView.as_view(), name="leave-analytics-department"),
    path("analytics/branch/", BranchLeaveAnalyticsAPIView.as_view(), name="leave-analytics-branch"),
    path("analytics/organization/", OrganizationLeaveAnalyticsAPIView.as_view(), name="leave-analytics-organization"),
    path("analytics/kpis/", LeaveKPIsAPIView.as_view(), name="leave-analytics-kpis"),
    # Compliance Endpoint
    path("analytics/compliance/", LeaveComplianceAPIView.as_view(), name="leave-analytics-compliance"),
    # Forecast Endpoint
    path("analytics/forecast/", LeaveForecastAPIView.as_view(), name="leave-analytics-forecast"),
    # Dashboard Endpoints
    path("dashboards/executive/", ExecutiveLeaveDashboardAPIView.as_view(), name="leave-dashboard-executive"),
    path("dashboards/manager/", ManagerLeaveDashboardAPIView.as_view(), name="leave-dashboard-manager"),
    # Report Export Endpoint
    path("reports/export/", LeaveExportReportAPIView.as_view(), name="leave-report-export"),
]
