"""URL pattern routing for employees app."""

from django.urls import path

from .views import (
    AssignManagerAPIView,
    AssignShiftAPIView,
    AssignTeamAPIView,
    AssignWorkLocationAPIView,
    BulkAssignManagerAPIView,
    DepartmentTreeAPIView,
    EmployeeAuditEventListAPIView,
    EmployeeConfirmAPIView,
    EmployeeDetailAPIView,
    EmployeeListAPIView,
    EmployeeOrgChartAPIView,
    EmployeePromoteAPIView,
    EmployeeResignAPIView,
    EmployeeResignationActionAPIView,
    EmployeeTransferAPIView,
    EmployeeTransitionStatusAPIView,
    EmploymentHistoryListAPIView,
    OrganizationTreeAPIView,
    TeamTreeAPIView,
    WorkforceAssignmentListAPIView,
)

app_name = "employees"

urlpatterns = [
    # Core Employee CRUD & Search
    path("", EmployeeListAPIView.as_view(), name="employee-list"),
    path("<uuid:pk>/", EmployeeDetailAPIView.as_view(), name="employee-detail"),
    # Workforce Assignment Endpoints
    path("<uuid:pk>/assign-manager/", AssignManagerAPIView.as_view(), name="employee-assign-manager"),
    path("bulk-assign-manager/", BulkAssignManagerAPIView.as_view(), name="employee-bulk-assign-manager"),
    path("<uuid:pk>/assign-shift/", AssignShiftAPIView.as_view(), name="employee-assign-shift"),
    path("<uuid:pk>/assign-location/", AssignWorkLocationAPIView.as_view(), name="employee-assign-location"),
    path("<uuid:pk>/assign-team/", AssignTeamAPIView.as_view(), name="employee-assign-team"),
    path("<uuid:pk>/assignments/", WorkforceAssignmentListAPIView.as_view(), name="employee-assignments"),
    # Org Chart & Workforce Trees
    path("trees/organization/<uuid:org_pk>/", OrganizationTreeAPIView.as_view(), name="tree-organization"),
    path("trees/department/<uuid:org_pk>/", DepartmentTreeAPIView.as_view(), name="tree-department"),
    path("trees/team/<uuid:org_pk>/", TeamTreeAPIView.as_view(), name="tree-team"),
    # Employee Lifecycle & Resignation Endpoints
    path("<uuid:pk>/transition-status/", EmployeeTransitionStatusAPIView.as_view(), name="employee-transition-status"),
    path("<uuid:pk>/confirm/", EmployeeConfirmAPIView.as_view(), name="employee-confirm"),
    path("<uuid:pk>/resign/", EmployeeResignAPIView.as_view(), name="employee-resign-submit"),
    path("<uuid:pk>/resign/action/", EmployeeResignationActionAPIView.as_view(), name="employee-resign-action"),
    path("<uuid:pk>/transfer/", EmployeeTransferAPIView.as_view(), name="employee-transfer"),
    path("<uuid:pk>/promote/", EmployeePromoteAPIView.as_view(), name="employee-promote"),
    path("<uuid:pk>/org-chart/", EmployeeOrgChartAPIView.as_view(), name="employee-org-chart"),
    path("<uuid:pk>/audit-logs/", EmployeeAuditEventListAPIView.as_view(), name="employee-audit-logs"),
    path("<uuid:emp_pk>/history/", EmploymentHistoryListAPIView.as_view(), name="employee-history"),
]
