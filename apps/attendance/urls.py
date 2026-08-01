"""URL pattern routing for attendance app."""

from django.urls import path

from .views import (
    AIFoundationDataAPIView,
    AttendanceCorrectionListSubmitAPIView,
    AttendanceCorrectionProcessAPIView,
    AttendanceLockAPIView,
    AttendancePolicyListCreateAPIView,
    AttendanceRecordListCreateAPIView,
    AttendanceSummaryAPIView,
    AttendanceUnlockAPIView,
    BranchAnalyticsAPIView,
    BreakEndAPIView,
    BreakStartAPIView,
    BulkAttendanceImportAPIView,
    CheckInAPIView,
    CheckOutAPIView,
    ComplianceViolationsAPIView,
    DashboardAnalyticsAPIView,
    DepartmentAnalyticsAPIView,
    EmployeeAnalyticsAPIView,
    ExportCSVAPIView,
    OrganizationAnalyticsAPIView,
    TeamAnalyticsAPIView,
)

app_name = "attendance"

urlpatterns = [
    # Operational Processing Endpoints
    path("check-in/", CheckInAPIView.as_view(), name="check-in"),
    path("check-out/", CheckOutAPIView.as_view(), name="check-out"),
    path("break-start/", BreakStartAPIView.as_view(), name="break-start"),
    path("break-end/", BreakEndAPIView.as_view(), name="break-end"),
    path("corrections/", AttendanceCorrectionListSubmitAPIView.as_view(), name="correction-list-submit"),
    path("corrections/<uuid:pk>/process/", AttendanceCorrectionProcessAPIView.as_view(), name="correction-process"),
    path("lock/", AttendanceLockAPIView.as_view(), name="attendance-lock"),
    path("unlock/", AttendanceUnlockAPIView.as_view(), name="attendance-unlock"),
    path("bulk-import/", BulkAttendanceImportAPIView.as_view(), name="bulk-import"),
    # Foundation Policy & Record Endpoints
    path("policies/", AttendancePolicyListCreateAPIView.as_view(), name="policy-list-create"),
    path("records/", AttendanceRecordListCreateAPIView.as_view(), name="record-list-create"),
    path("summary/", AttendanceSummaryAPIView.as_view(), name="attendance-summary"),
    # Analytics & Compliance Endpoints
    path("analytics/employee/", EmployeeAnalyticsAPIView.as_view(), name="analytics-employee"),
    path("analytics/team/", TeamAnalyticsAPIView.as_view(), name="analytics-team"),
    path("analytics/department/", DepartmentAnalyticsAPIView.as_view(), name="analytics-department"),
    path("analytics/branch/", BranchAnalyticsAPIView.as_view(), name="analytics-branch"),
    path("analytics/organization/", OrganizationAnalyticsAPIView.as_view(), name="analytics-organization"),
    path("analytics/compliance/", ComplianceViolationsAPIView.as_view(), name="analytics-compliance"),
    path("analytics/dashboard/", DashboardAnalyticsAPIView.as_view(), name="analytics-dashboard"),
    path("analytics/export-csv/", ExportCSVAPIView.as_view(), name="analytics-export-csv"),
    path("analytics/ai-foundation/", AIFoundationDataAPIView.as_view(), name="analytics-ai-foundation"),
]
