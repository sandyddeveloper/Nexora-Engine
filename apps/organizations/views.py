"""Thin API views for the organizations domain."""

from drf_spectacular.utils import OpenApiResponse, extend_schema, extend_schema_view
from rest_framework.permissions import IsAuthenticated
from rest_framework.views import APIView

from core.pagination import paginated_response
from core.responses import (
    created_response,
    deleted_response,
    not_found_response,
    success_response,
    updated_response,
    validation_error_response,
)

from . import selectors, services
from .permissions import IsOrganizationAdmin
from .serializers import (
    AssignRosterShiftSerializer,
    BranchCreateSerializer,
    BranchSerializer,
    BulkAssignTeamRosterShiftSerializer,
    DepartmentSerializer,
    DesignationSerializer,
    HolidayCalendarSerializer,
    OrganizationAuditEventSerializer,
    OrganizationDetailSerializer,
    OrganizationFeatureFlagSerializer,
    OrganizationLimitSerializer,
    OrganizationOnboardSerializer,
    OrganizationSerializer,
    OrganizationSettingSerializer,
    OrganizationTransitionStatusSerializer,
    ShiftOverrideSerializer,
    ShiftRosterAssignmentSerializer,
    ShiftRosterSerializer,
    ShiftSerializer,
    ShiftSwapRequestSerializer,
    TeamSerializer,
)


# ── Onboarding & Engine Views ────────────────────────────────────────────────


@extend_schema_view(
    post=extend_schema(
        tags=["Organizations"],
        summary="Onboard Organization",
        description="Execute single-transaction Organization Onboarding Engine workflow creating Org, HQ Branch, Default Departments, Default Shift, and Default Holiday Calendar.",
        request=OrganizationOnboardSerializer,
        responses={201: OrganizationDetailSerializer, 400: OpenApiResponse(description="Validation error.")},
    )
)
class OrganizationOnboardAPIView(APIView):
    permission_classes = [IsAuthenticated, IsOrganizationAdmin]

    def post(self, request):
        serializer = OrganizationOnboardSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = request.user
        org = services.onboard_organization(
            **serializer.validated_data,
            user_id=str(user.id) if user else "",
            user_email=getattr(user, "email", ""),
            ip_address=request.META.get("REMOTE_ADDR"),
            request_id=getattr(request, "request_id", ""),
        )
        return created_response(
            message="Organization onboarded successfully.",
            data=OrganizationDetailSerializer(org).data,
        )


@extend_schema_view(
    post=extend_schema(
        tags=["Organizations"],
        summary="Transition Organization Status (FSM)",
        description="Execute lifecycle FSM status transition (DRAFT -> PENDING_VERIFICATION -> ACTIVE -> SUSPENDED -> INACTIVE -> ARCHIVED).",
        request=OrganizationTransitionStatusSerializer,
        responses={200: OrganizationDetailSerializer, 400: OpenApiResponse(description="Invalid state transition.")},
    )
)
class OrganizationTransitionStatusAPIView(APIView):
    permission_classes = [IsAuthenticated, IsOrganizationAdmin]

    def post(self, request, pk):
        org = selectors.get_organization(organization_id=pk)
        if org is None:
            return not_found_response(message="Organization not found.")

        serializer = OrganizationTransitionStatusSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = request.user

        try:
            org = services.transition_organization_status(
                organization=org,
                target_status=serializer.validated_data["target_status"],
                reason=serializer.validated_data.get("reason", ""),
                user_id=str(user.id) if user else "",
                user_email=getattr(user, "email", ""),
                ip_address=request.META.get("REMOTE_ADDR"),
                request_id=getattr(request, "request_id", ""),
            )
            return success_response(
                message="Organization status transitioned successfully.",
                data=OrganizationDetailSerializer(org).data,
            )
        except Exception as e:
            return validation_error_response(
                errors={"target_status": str(e)},
                message="Lifecycle transition failed.",
            )


@extend_schema_view(
    get=extend_schema(tags=["Organization Settings"], summary="Retrieve Organization Limits", responses={200: OrganizationLimitSerializer}),
    patch=extend_schema(tags=["Organization Settings"], summary="Update Organization Limits", request=OrganizationLimitSerializer, responses={200: OrganizationLimitSerializer}),
)
class OrganizationLimitAPIView(APIView):
    permission_classes = [IsAuthenticated, IsOrganizationAdmin]

    def get(self, request, org_pk):
        limit = selectors.get_organization_limit(organization_id=org_pk)
        if limit is None:
            return not_found_response(message="Organization limits not found.")
        return success_response(message="Limits retrieved.", data=OrganizationLimitSerializer(limit).data)

    def patch(self, request, org_pk):
        limit = selectors.get_organization_limit(organization_id=org_pk)
        if limit is None:
            return not_found_response(message="Organization limits not found.")
        serializer = OrganizationLimitSerializer(data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        limit = services.update_organization_limit(limit=limit, **serializer.validated_data)
        return updated_response(message="Organization limits updated.", data=OrganizationLimitSerializer(limit).data)


@extend_schema_view(
    get=extend_schema(tags=["Organization Settings"], summary="Retrieve Feature Flags", responses={200: OrganizationFeatureFlagSerializer}),
    patch=extend_schema(tags=["Organization Settings"], summary="Update Feature Flags", request=OrganizationFeatureFlagSerializer, responses={200: OrganizationFeatureFlagSerializer}),
)
class OrganizationFeatureFlagAPIView(APIView):
    permission_classes = [IsAuthenticated, IsOrganizationAdmin]

    def get(self, request, org_pk):
        flag = selectors.get_organization_feature_flag(organization_id=org_pk)
        if flag is None:
            return not_found_response(message="Feature flags not found.")
        return success_response(message="Feature flags retrieved.", data=OrganizationFeatureFlagSerializer(flag).data)

    def patch(self, request, org_pk):
        flag = selectors.get_organization_feature_flag(organization_id=org_pk)
        if flag is None:
            return not_found_response(message="Feature flags not found.")
        serializer = OrganizationFeatureFlagSerializer(data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        flag = services.update_organization_feature_flag(feature_flag=flag, **serializer.validated_data)
        return updated_response(message="Feature flags updated.", data=OrganizationFeatureFlagSerializer(flag).data)


@extend_schema_view(
    get=extend_schema(tags=["Organization Audit"], summary="List Organization Audit Events", responses={200: OrganizationAuditEventSerializer(many=True)}),
)
class OrganizationAuditEventListAPIView(APIView):
    permission_classes = [IsAuthenticated, IsOrganizationAdmin]

    def get(self, request, org_pk):
        events = selectors.list_organization_audit_events(organization_id=org_pk)
        page = request.query_params.get("page", 1)
        page_size = request.query_params.get("page_size", 20)
        return paginated_response(
            events,
            serializer_class=OrganizationAuditEventSerializer,
            message="Audit log trail retrieved successfully.",
            page=page,
            page_size=page_size,
        )


# ── Organization CRUD Views ──────────────────────────────────────────────────


@extend_schema_view(
    get=extend_schema(
        tags=["Organizations"],
        summary="List Organizations",
        description="Retrieve a paginated list of all active organizations.",
        responses={200: OrganizationSerializer(many=True)},
    ),
    post=extend_schema(
        tags=["Organizations"],
        summary="Create Organization",
        description="Register a new enterprise organization.",
        request=OrganizationSerializer,
        responses={
            201: OrganizationDetailSerializer,
            400: OpenApiResponse(description="Validation error."),
        },
    ),
)
class OrganizationListAPIView(APIView):
    permission_classes = [IsAuthenticated, IsOrganizationAdmin]

    def get(self, request):
        organizations = selectors.list_organizations()
        page = request.query_params.get("page", 1)
        page_size = request.query_params.get("page_size", 20)
        return paginated_response(
            organizations,
            serializer_class=OrganizationSerializer,
            message="Organizations retrieved successfully.",
            page=page,
            page_size=page_size,
        )

    def post(self, request):
        serializer = OrganizationSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        org = services.create_organization(**serializer.validated_data)
        return created_response(
            message="Organization created successfully.",
            data=OrganizationDetailSerializer(org).data,
        )


@extend_schema_view(
    get=extend_schema(
        tags=["Organizations"],
        summary="Retrieve Organization Details",
        responses={200: OrganizationDetailSerializer, 404: OpenApiResponse(description="Not found.")},
    ),
    patch=extend_schema(
        tags=["Organizations"],
        summary="Update Organization",
        request=OrganizationSerializer,
        responses={200: OrganizationDetailSerializer, 404: OpenApiResponse(description="Not found.")},
    ),
    delete=extend_schema(
        tags=["Organizations"],
        summary="Soft Delete Organization",
        responses={204: OpenApiResponse(description="Deleted successfully.")},
    ),
)
class OrganizationDetailAPIView(APIView):
    permission_classes = [IsAuthenticated, IsOrganizationAdmin]

    def get(self, request, pk):
        org = selectors.get_organization(organization_id=pk)
        if org is None:
            return not_found_response(message="Organization not found.")
        return success_response(
            message="Organization details retrieved successfully.",
            data=OrganizationDetailSerializer(org).data,
        )

    def patch(self, request, pk):
        org = selectors.get_organization(organization_id=pk)
        if org is None:
            return not_found_response(message="Organization not found.")
        serializer = OrganizationSerializer(data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        org = services.update_organization(organization=org, **serializer.validated_data)
        return updated_response(
            message="Organization updated successfully.",
            data=OrganizationDetailSerializer(org).data,
        )

    def delete(self, request, pk):
        org = selectors.get_organization(organization_id=pk)
        if org is None:
            return not_found_response(message="Organization not found.")
        try:
            services.soft_delete_organization(organization=org)
            return deleted_response(message="Organization deleted successfully.")
        except Exception as e:
            return validation_error_response(errors={"organization": str(e)}, message="Deletion failed.")


# ── Branch Views ─────────────────────────────────────────────────────────────


@extend_schema_view(
    get=extend_schema(tags=["Branches"], summary="List Branches", responses={200: BranchSerializer(many=True)}),
    post=extend_schema(tags=["Branches"], summary="Create Branch", request=BranchCreateSerializer, responses={201: BranchSerializer}),
)
class BranchListAPIView(APIView):
    permission_classes = [IsAuthenticated, IsOrganizationAdmin]

    def get(self, request, org_pk):
        branches = selectors.list_branches(organization_id=org_pk)
        page = request.query_params.get("page", 1)
        page_size = request.query_params.get("page_size", 20)
        return paginated_response(
            branches,
            serializer_class=BranchSerializer,
            message="Branches retrieved successfully.",
            page=page,
            page_size=page_size,
        )

    def post(self, request, org_pk):
        org = selectors.get_organization(organization_id=org_pk)
        if org is None:
            return not_found_response(message="Organization not found.")
        serializer = BranchCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            branch = services.create_branch(organization=org, **serializer.validated_data)
            return created_response(message="Branch created successfully.", data=BranchSerializer(branch).data)
        except Exception as e:
            return validation_error_response(errors={"branch": str(e)}, message="Branch creation failed.")


@extend_schema_view(
    get=extend_schema(tags=["Branches"], summary="Retrieve Branch Details", responses={200: BranchSerializer}),
    patch=extend_schema(tags=["Branches"], summary="Update Branch", request=BranchCreateSerializer, responses={200: BranchSerializer}),
    delete=extend_schema(tags=["Branches"], summary="Soft Delete Branch", responses={204: OpenApiResponse()}),
)
class BranchDetailAPIView(APIView):
    permission_classes = [IsAuthenticated, IsOrganizationAdmin]

    def get(self, request, pk):
        branch = selectors.get_branch(branch_id=pk)
        if branch is None:
            return not_found_response(message="Branch not found.")
        return success_response(message="Branch retrieved.", data=BranchSerializer(branch).data)

    def patch(self, request, pk):
        branch = selectors.get_branch(branch_id=pk)
        if branch is None:
            return not_found_response(message="Branch not found.")
        serializer = BranchCreateSerializer(data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        branch = services.update_branch(branch=branch, **serializer.validated_data)
        return updated_response(message="Branch updated.", data=BranchSerializer(branch).data)

    def delete(self, request, pk):
        branch = selectors.get_branch(branch_id=pk)
        if branch is None:
            return not_found_response(message="Branch not found.")
        try:
            services.soft_delete_branch(branch=branch)
            return deleted_response(message="Branch deleted successfully.")
        except Exception as e:
            return validation_error_response(errors={"branch": str(e)}, message="Branch deletion failed.")


# ── Department Views ─────────────────────────────────────────────────────────


@extend_schema_view(
    get=extend_schema(tags=["Departments"], summary="List Departments", responses={200: DepartmentSerializer(many=True)}),
    post=extend_schema(tags=["Departments"], summary="Create Department", request=DepartmentSerializer, responses={201: DepartmentSerializer}),
)
class DepartmentListAPIView(APIView):
    permission_classes = [IsAuthenticated, IsOrganizationAdmin]

    def get(self, request, org_pk):
        branch_id = request.query_params.get("branch_id")
        departments = selectors.list_departments(organization_id=org_pk, branch_id=branch_id)
        page = request.query_params.get("page", 1)
        page_size = request.query_params.get("page_size", 20)
        return paginated_response(
            departments,
            serializer_class=DepartmentSerializer,
            message="Departments retrieved successfully.",
            page=page,
            page_size=page_size,
        )

    def post(self, request, org_pk):
        org = selectors.get_organization(organization_id=org_pk)
        if org is None:
            return not_found_response(message="Organization not found.")
        serializer = DepartmentSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        branch_id = serializer.validated_data.get("branch").id
        branch = selectors.get_branch(branch_id=branch_id)
        if branch is None:
            return validation_error_response(errors={"branch": "Invalid branch specified."})
        try:
            dept = services.create_department(
                organization=org,
                branch=branch,
                name=serializer.validated_data["name"],
                code=serializer.validated_data["code"],
                parent_department=serializer.validated_data.get("parent_department"),
                description=serializer.validated_data.get("description", ""),
                ordering=serializer.validated_data.get("ordering", 0),
                status=serializer.validated_data.get("status", "ACTIVE"),
            )
            return created_response(message="Department created successfully.", data=DepartmentSerializer(dept).data)
        except Exception as e:
            return validation_error_response(errors={"department": str(e)}, message="Department creation failed.")


# ── Designation Views ────────────────────────────────────────────────────────


@extend_schema_view(
    get=extend_schema(tags=["Designations"], summary="List Designations", responses={200: DesignationSerializer(many=True)}),
    post=extend_schema(tags=["Designations"], summary="Create Designation", request=DesignationSerializer, responses={201: DesignationSerializer}),
)
class DesignationListAPIView(APIView):
    permission_classes = [IsAuthenticated, IsOrganizationAdmin]

    def get(self, request, org_pk):
        designations = selectors.list_designations(organization_id=org_pk)
        page = request.query_params.get("page", 1)
        page_size = request.query_params.get("page_size", 20)
        return paginated_response(
            designations,
            serializer_class=DesignationSerializer,
            message="Designations retrieved successfully.",
            page=page,
            page_size=page_size,
        )

    def post(self, request, org_pk):
        org = selectors.get_organization(organization_id=org_pk)
        if org is None:
            return not_found_response(message="Organization not found.")
        serializer = DesignationSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        designation = services.create_designation(
            organization=org,
            name=serializer.validated_data["name"],
            code=serializer.validated_data["code"],
            department=serializer.validated_data.get("department"),
            grade=serializer.validated_data.get("grade", ""),
            level=serializer.validated_data.get("level", 1),
            description=serializer.validated_data.get("description", ""),
            status=serializer.validated_data.get("status", "ACTIVE"),
        )
        return created_response(message="Designation created.", data=DesignationSerializer(designation).data)


# ── Team Views ───────────────────────────────────────────────────────────────


@extend_schema_view(
    get=extend_schema(tags=["Teams"], summary="List Teams", responses={200: TeamSerializer(many=True)}),
    post=extend_schema(tags=["Teams"], summary="Create Team", request=TeamSerializer, responses={201: TeamSerializer}),
)
class TeamListAPIView(APIView):
    permission_classes = [IsAuthenticated, IsOrganizationAdmin]

    def get(self, request, org_pk):
        branch_id = request.query_params.get("branch_id")
        teams = selectors.list_teams(organization_id=org_pk, branch_id=branch_id)
        page = request.query_params.get("page", 1)
        page_size = request.query_params.get("page_size", 20)
        return paginated_response(
            teams,
            serializer_class=TeamSerializer,
            message="Teams retrieved successfully.",
            page=page,
            page_size=page_size,
        )

    def post(self, request, org_pk):
        org = selectors.get_organization(organization_id=org_pk)
        if org is None:
            return not_found_response(message="Organization not found.")
        serializer = TeamSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            team = services.create_team(
                organization=org,
                branch=serializer.validated_data["branch"],
                department=serializer.validated_data["department"],
                name=serializer.validated_data["name"],
                code=serializer.validated_data["code"],
                description=serializer.validated_data.get("description", ""),
                status=serializer.validated_data.get("status", "ACTIVE"),
            )
            return created_response(message="Team created successfully.", data=TeamSerializer(team).data)
        except Exception as e:
            return validation_error_response(errors={"team": str(e)}, message="Team creation failed.")


# ── Shift Views ──────────────────────────────────────────────────────────────


@extend_schema_view(
    get=extend_schema(tags=["Shifts"], summary="List Shift Templates", responses={200: ShiftSerializer(many=True)}),
    post=extend_schema(tags=["Shifts"], summary="Create Shift Template", request=ShiftSerializer, responses={201: ShiftSerializer}),
)
class ShiftListAPIView(APIView):
    permission_classes = [IsAuthenticated, IsOrganizationAdmin]

    def get(self, request, org_pk):
        shifts = selectors.list_shifts(organization_id=org_pk)
        page = request.query_params.get("page", 1)
        page_size = request.query_params.get("page_size", 20)
        return paginated_response(
            shifts,
            serializer_class=ShiftSerializer,
            message="Shift templates retrieved successfully.",
            page=page,
            page_size=page_size,
        )

    def post(self, request, org_pk):
        org = selectors.get_organization(organization_id=org_pk)
        if org is None:
            return not_found_response(message="Organization not found.")
        serializer = ShiftSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            shift = services.create_shift(
                organization=org,
                name=serializer.validated_data["name"],
                code=serializer.validated_data["code"],
                start_time=serializer.validated_data["start_time"],
                end_time=serializer.validated_data["end_time"],
                shift_type=serializer.validated_data.get("shift_type", "REGULAR"),
                grace_time_minutes=serializer.validated_data.get("grace_time_minutes", 15),
                flexible_hours=serializer.validated_data.get("flexible_hours", False),
                is_night_shift=serializer.validated_data.get("is_night_shift", False),
                break_duration_minutes=serializer.validated_data.get("break_duration_minutes", 60),
                working_hours=serializer.validated_data.get("working_hours", 8.00),
                status=serializer.validated_data.get("status", "ACTIVE"),
            )
            return created_response(message="Shift template created successfully.", data=ShiftSerializer(shift).data)
        except Exception as e:
            return validation_error_response(errors={"shift": str(e)}, message="Shift creation failed.")


# ── Holiday Calendar Views ───────────────────────────────────────────────────


@extend_schema_view(
    get=extend_schema(tags=["Holidays"], summary="List Holiday Calendars", responses={200: HolidayCalendarSerializer(many=True)}),
    post=extend_schema(tags=["Holidays"], summary="Create Holiday Entry", request=HolidayCalendarSerializer, responses={201: HolidayCalendarSerializer}),
)
class HolidayListAPIView(APIView):
    permission_classes = [IsAuthenticated, IsOrganizationAdmin]

    def get(self, request, org_pk):
        branch_id = request.query_params.get("branch_id")
        holidays = selectors.list_holidays(organization_id=org_pk, branch_id=branch_id)
        page = request.query_params.get("page", 1)
        page_size = request.query_params.get("page_size", 20)
        return paginated_response(
            holidays,
            serializer_class=HolidayCalendarSerializer,
            message="Holiday calendar retrieved successfully.",
            page=page,
            page_size=page_size,
        )

    def post(self, request, org_pk):
        org = selectors.get_organization(organization_id=org_pk)
        if org is None:
            return not_found_response(message="Organization not found.")
        serializer = HolidayCalendarSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        holiday = services.create_holiday(
            organization=org,
            branch=serializer.validated_data.get("branch"),
            name=serializer.validated_data["name"],
            holiday_date=serializer.validated_data["holiday_date"],
            holiday_type=serializer.validated_data.get("holiday_type", "PUBLIC"),
            description=serializer.validated_data.get("description", ""),
            is_recurring=serializer.validated_data.get("is_recurring", False),
            status=serializer.validated_data.get("status", "ACTIVE"),
        )
        return created_response(message="Holiday entry created successfully.", data=HolidayCalendarSerializer(holiday).data)


# ── Organization Setting Views ───────────────────────────────────────────────


@extend_schema_view(
    get=extend_schema(tags=["Organization Settings"], summary="Retrieve Organization Settings", responses={200: OrganizationSettingSerializer}),
    patch=extend_schema(tags=["Organization Settings"], summary="Update Organization Settings", request=OrganizationSettingSerializer, responses={200: OrganizationSettingSerializer}),
)
class OrganizationSettingAPIView(APIView):
    permission_classes = [IsAuthenticated, IsOrganizationAdmin]

    def get(self, request, org_pk):
        setting = selectors.get_organization_setting(organization_id=org_pk)
        if setting is None:
            return not_found_response(message="Organization settings not found.")
        return success_response(message="Settings retrieved.", data=OrganizationSettingSerializer(setting).data)

    def patch(self, request, org_pk):
        setting = selectors.get_organization_setting(organization_id=org_pk)
        if setting is None:
            return not_found_response(message="Organization settings not found.")
        serializer = OrganizationSettingSerializer(data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        setting = services.update_organization_setting(setting=setting, **serializer.validated_data)
        return updated_response(message="Organization settings updated.", data=OrganizationSettingSerializer(setting).data)


# ── Shift Rostering & Scheduling Views ───────────────────────────────────────


@extend_schema_view(
    get=extend_schema(
        tags=["Shift Rosters"],
        summary="List Shift Rosters",
        responses={200: ShiftRosterSerializer(many=True)},
    ),
    post=extend_schema(
        tags=["Shift Rosters"],
        summary="Create Shift Roster Plan (DRAFT)",
        request=ShiftRosterSerializer,
        responses={201: ShiftRosterSerializer},
    ),
)
class ShiftRosterListCreateAPIView(APIView):
    permission_classes = [IsAuthenticated, IsOrganizationAdmin]

    def get(self, request):
        organization_id = request.query_params.get("organization_id")
        if not organization_id:
            orgs = selectors.list_organizations()
            if orgs.exists():
                organization_id = str(orgs.first().id)
            else:
                return validation_error_response(errors={"organization_id": "organization_id query parameter is required."})

        rosters = selectors.list_shift_rosters(
            organization_id=organization_id,
            status=request.query_params.get("status"),
        )
        return success_response(message="Shift rosters retrieved.", data=ShiftRosterSerializer(rosters, many=True).data)

    def post(self, request):
        serializer = ShiftRosterSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        org = selectors.get_organization(organization_id=data["organization"].id)
        if not org:
            return validation_error_response(message="Invalid organization specified.")

        try:
            roster = services.create_shift_roster(
                organization=org,
                name=data["name"],
                code=data["code"],
                period_type=data.get("period_type", "WEEKLY"),
                start_date=data["start_date"],
                end_date=data["end_date"],
            )
            return created_response(
                message="Shift roster plan created in DRAFT state.",
                data=ShiftRosterSerializer(roster).data,
            )
        except Exception as e:
            return validation_error_response(errors={"roster": str(e)}, message="Roster creation failed.")


@extend_schema_view(
    post=extend_schema(
        tags=["Shift Rosters"],
        summary="Publish Shift Roster",
        description="Publish a draft shift roster making scheduling active.",
        request=None,
        responses={200: ShiftRosterSerializer},
    )
)
class ShiftRosterPublishAPIView(APIView):
    permission_classes = [IsAuthenticated, IsOrganizationAdmin]

    def post(self, request, pk):
        roster = selectors.get_shift_roster(roster_id=pk)
        if not roster:
            return not_found_response(message="Shift roster not found.")

        try:
            roster = services.publish_shift_roster(roster=roster)
            return success_response(
                message="Shift roster published successfully.",
                data=ShiftRosterSerializer(roster).data,
            )
        except Exception as e:
            return validation_error_response(errors={"publish": str(e)}, message="Roster publication failed.")


@extend_schema_view(
    post=extend_schema(
        tags=["Shift Rosters"],
        summary="Assign Shift to Employee in Roster",
        request=AssignRosterShiftSerializer,
        responses={201: ShiftRosterAssignmentSerializer},
    )
)
class AssignRosterShiftAPIView(APIView):
    permission_classes = [IsAuthenticated, IsOrganizationAdmin]

    def post(self, request, pk):
        roster = selectors.get_shift_roster(roster_id=pk)
        if not roster:
            return not_found_response(message="Shift roster not found.")

        serializer = AssignRosterShiftSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        from apps.employees import selectors as emp_selectors
        employee = emp_selectors.get_employee(employee_id=data["employee_id"])
        shift = selectors.Shift.objects.filter(id=data["shift_id"]).first()
        if not employee or not shift:
            return validation_error_response(message="Invalid employee or shift specified.")

        try:
            assignment = services.assign_employee_roster_shift(
                roster=roster,
                employee=employee,
                shift=shift,
                date=data["date"],
                is_override=data.get("is_override", False),
                override_reason=data.get("override_reason", ""),
            )
            return created_response(
                message="Employee shift assigned in roster.",
                data=ShiftRosterAssignmentSerializer(assignment).data,
            )
        except Exception as e:
            return validation_error_response(errors={"assignment": str(e)}, message="Shift assignment failed.")


@extend_schema_view(
    post=extend_schema(
        tags=["Shift Rosters"],
        summary="Bulk Assign Team Shift Roster",
        request=BulkAssignTeamRosterShiftSerializer,
        responses={200: OpenApiResponse(description="Bulk count of assignments created.")},
    )
)
class BulkAssignTeamRosterShiftAPIView(APIView):
    permission_classes = [IsAuthenticated, IsOrganizationAdmin]

    def post(self, request, pk):
        roster = selectors.get_shift_roster(roster_id=pk)
        if not roster:
            return not_found_response(message="Shift roster not found.")

        serializer = BulkAssignTeamRosterShiftSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        shift = selectors.Shift.objects.filter(id=data["shift_id"]).first()
        if not shift:
            return validation_error_response(message="Invalid shift specified.")

        try:
            count = services.bulk_assign_team_roster_shift(
                roster=roster,
                team_id=data["team_id"],
                shift=shift,
                start_date=data["start_date"],
                end_date=data["end_date"],
            )
            return success_response(
                message=f"Bulk shift roster assignment created for {count} entries.",
                data={"assigned_count": count},
            )
        except Exception as e:
            return validation_error_response(errors={"bulk_roster": str(e)}, message="Bulk assignment failed.")


@extend_schema_view(
    get=extend_schema(
        tags=["Roster Calendars"],
        summary="Retrieve Employee Roster Calendar Matrix",
        responses={200: OpenApiResponse()},
    )
)
class EmployeeRosterCalendarAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        employee_id = request.query_params.get("employee_id")
        start_date = request.query_params.get("start_date")
        end_date = request.query_params.get("end_date")

        if not employee_id or not start_date or not end_date:
            return validation_error_response(message="employee_id, start_date, and end_date query parameters are required.")

        calendar = selectors.get_employee_roster_calendar(
            employee_id=employee_id,
            start_date=start_date,
            end_date=end_date,
        )
        return success_response(message="Employee roster calendar matrix retrieved.", data=calendar)


@extend_schema_view(
    get=extend_schema(
        tags=["Roster Calendars"],
        summary="Retrieve Team Roster Calendar Matrix",
        responses={200: OpenApiResponse()},
    )
)
class TeamRosterCalendarAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        team_id = request.query_params.get("team_id")
        start_date = request.query_params.get("start_date")
        end_date = request.query_params.get("end_date")

        if not team_id or not start_date or not end_date:
            return validation_error_response(message="team_id, start_date, and end_date query parameters are required.")

        calendar = selectors.get_team_roster_calendar(
            team_id=team_id,
            start_date=start_date,
            end_date=end_date,
        )
        return success_response(message="Team roster calendar matrix retrieved.", data=calendar)

