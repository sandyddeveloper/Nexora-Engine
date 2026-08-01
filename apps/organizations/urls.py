"""URL pattern routing for organizations app."""

from django.urls import path

from .views import (
    AssignRosterShiftAPIView,
    BranchDetailAPIView,
    BranchListAPIView,
    BulkAssignTeamRosterShiftAPIView,
    DepartmentListAPIView,
    DesignationListAPIView,
    EmployeeRosterCalendarAPIView,
    HolidayListAPIView,
    OrganizationAuditEventListAPIView,
    OrganizationDetailAPIView,
    OrganizationFeatureFlagAPIView,
    OrganizationLimitAPIView,
    OrganizationListAPIView,
    OrganizationOnboardAPIView,
    OrganizationSettingAPIView,
    OrganizationTransitionStatusAPIView,
    ShiftListAPIView,
    ShiftRosterListCreateAPIView,
    ShiftRosterPublishAPIView,
    TeamListAPIView,
    TeamRosterCalendarAPIView,
)

app_name = "organizations"

urlpatterns = [
    # Engine & Onboarding URLs
    path("onboard/", OrganizationOnboardAPIView.as_view(), name="organization-onboard"),
    # Shift Rostering & Calendar URLs
    path("rosters/", ShiftRosterListCreateAPIView.as_view(), name="roster-list-create"),
    path("rosters/<uuid:pk>/publish/", ShiftRosterPublishAPIView.as_view(), name="roster-publish"),
    path("rosters/<uuid:pk>/assign-employee/", AssignRosterShiftAPIView.as_view(), name="roster-assign-employee"),
    path("rosters/<uuid:pk>/assign-team/", BulkAssignTeamRosterShiftAPIView.as_view(), name="roster-assign-team"),
    path("rosters/calendar/employee/", EmployeeRosterCalendarAPIView.as_view(), name="roster-calendar-employee"),
    path("rosters/calendar/team/", TeamRosterCalendarAPIView.as_view(), name="roster-calendar-team"),
    # Organization Core CRUD & Lifecycle URLs
    path("", OrganizationListAPIView.as_view(), name="organization-list"),
    path("<uuid:pk>/", OrganizationDetailAPIView.as_view(), name="organization-detail"),
    path("<uuid:pk>/transition-status/", OrganizationTransitionStatusAPIView.as_view(), name="organization-transition-status"),
    path("<uuid:org_pk>/settings/", OrganizationSettingAPIView.as_view(), name="organization-settings"),
    path("<uuid:org_pk>/limits/", OrganizationLimitAPIView.as_view(), name="organization-limits"),
    path("<uuid:org_pk>/feature-flags/", OrganizationFeatureFlagAPIView.as_view(), name="organization-feature-flags"),
    path("<uuid:org_pk>/audit-logs/", OrganizationAuditEventListAPIView.as_view(), name="organization-audit-logs"),
    # Branch URLs
    path("<uuid:org_pk>/branches/", BranchListAPIView.as_view(), name="branch-list"),
    path("branches/<uuid:pk>/", BranchDetailAPIView.as_view(), name="branch-detail"),
    # Department URLs
    path("<uuid:org_pk>/departments/", DepartmentListAPIView.as_view(), name="department-list"),
    # Designation URLs
    path("<uuid:org_pk>/designations/", DesignationListAPIView.as_view(), name="designation-list"),
    # Team URLs
    path("<uuid:org_pk>/teams/", TeamListAPIView.as_view(), name="team-list"),
    # Shift URLs
    path("<uuid:org_pk>/shifts/", ShiftListAPIView.as_view(), name="shift-list"),
    # Holiday Calendar URLs
    path("<uuid:org_pk>/holidays/", HolidayListAPIView.as_view(), name="holiday-list"),
]
