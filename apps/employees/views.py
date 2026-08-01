"""Thin API views for the Employee Lifecycle & Workforce Assignment Engine."""

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
from apps.organizations import selectors as org_selectors

from . import selectors, services
from .permissions import IsEmployeeManager
from .serializers import (
    AssignManagerSerializer,
    AssignShiftSerializer,
    AssignTeamSerializer,
    AssignWorkLocationSerializer,
    BulkAssignManagerSerializer,
    EmployeeAuditEventSerializer,
    EmployeeConfirmSerializer,
    EmployeeCreateSerializer,
    EmployeeDetailSerializer,
    EmployeePromoteSerializer,
    EmployeeResignationApproveSerializer,
    EmployeeResignationSerializer,
    EmployeeResignationSubmitSerializer,
    EmployeeSerializer,
    EmployeeTransferSerializer,
    EmployeeTransitionStatusSerializer,
    EmploymentHistorySerializer,
    ManagerAssignmentSerializer,
    WorkforceAssignmentSerializer,
)


@extend_schema_view(
    post=extend_schema(
        tags=["Workforce Assignments"],
        summary="Assign Reporting Manager",
        description="Assign a primary, secondary, functional, HR, project, or mentor manager with hierarchy loop guards.",
        request=AssignManagerSerializer,
        responses={201: ManagerAssignmentSerializer},
    )
)
class AssignManagerAPIView(APIView):
    permission_classes = [IsAuthenticated, IsEmployeeManager]

    def post(self, request, pk):
        employee = selectors.get_employee(employee_id=pk)
        if not employee:
            return not_found_response(message="Employee not found.")

        serializer = AssignManagerSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        manager = selectors.get_employee(employee_id=data["manager_id"])
        if not manager:
            return validation_error_response(message="Invalid manager employee specified.")

        user = request.user
        try:
            assignment = services.assign_manager(
                employee=employee,
                manager=manager,
                manager_type=data.get("manager_type", "PRIMARY"),
                effective_date=data.get("effective_date"),
                reason=data.get("reason", ""),
                actor_user_id=str(user.id) if user else "",
            )
            return created_response(
                message="Manager assigned successfully.",
                data=ManagerAssignmentSerializer(assignment).data,
            )
        except Exception as e:
            return validation_error_response(errors={"manager": str(e)}, message="Manager assignment failed.")


@extend_schema_view(
    post=extend_schema(
        tags=["Workforce Assignments"],
        summary="Bulk Assign Reporting Manager",
        description="Bulk assign a manager to multiple employees in a single transaction.",
        request=BulkAssignManagerSerializer,
        responses={200: OpenApiResponse(description="Bulk manager assignment count.")},
    )
)
class BulkAssignManagerAPIView(APIView):
    permission_classes = [IsAuthenticated, IsEmployeeManager]

    def post(self, request):
        serializer = BulkAssignManagerSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        manager = selectors.get_employee(employee_id=data["manager_id"])
        if not manager:
            return validation_error_response(message="Invalid manager employee specified.")

        user = request.user
        try:
            count = services.bulk_assign_manager(
                employee_ids=data["employee_ids"],
                manager=manager,
                manager_type=data.get("manager_type", "PRIMARY"),
                effective_date=data.get("effective_date"),
                actor_user_id=str(user.id) if user else "",
            )
            return success_response(
                message=f"Bulk manager assigned successfully to {count} employees.",
                data={"assigned_count": count},
            )
        except Exception as e:
            return validation_error_response(errors={"bulk_assignment": str(e)}, message="Bulk assignment failed.")


@extend_schema_view(
    post=extend_schema(
        tags=["Workforce Assignments"],
        summary="Assign Shift Template",
        description="Assign a reusable Shift template to an employee with history tracking.",
        request=AssignShiftSerializer,
        responses={201: WorkforceAssignmentSerializer},
    )
)
class AssignShiftAPIView(APIView):
    permission_classes = [IsAuthenticated, IsEmployeeManager]

    def post(self, request, pk):
        employee = selectors.get_employee(employee_id=pk)
        if not employee:
            return not_found_response(message="Employee not found.")

        serializer = AssignShiftSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        shift = org_selectors.get_shift(shift_id=data["shift_id"])
        if not shift:
            return validation_error_response(message="Invalid shift template specified.")

        user = request.user
        try:
            assignment = services.assign_shift(
                employee=employee,
                shift=shift,
                effective_date=data.get("effective_date"),
                end_date=data.get("end_date"),
                is_temporary=data.get("is_temporary", False),
                reason=data.get("reason", ""),
                actor_user_id=str(user.id) if user else "",
            )
            return created_response(
                message="Shift assigned successfully.",
                data=WorkforceAssignmentSerializer(assignment).data,
            )
        except Exception as e:
            return validation_error_response(errors={"shift": str(e)}, message="Shift assignment failed.")


@extend_schema_view(
    post=extend_schema(
        tags=["Workforce Assignments"],
        summary="Assign Work Location",
        description="Assign physical office, remote, hybrid, or site work location.",
        request=AssignWorkLocationSerializer,
        responses={201: WorkforceAssignmentSerializer},
    )
)
class AssignWorkLocationAPIView(APIView):
    permission_classes = [IsAuthenticated, IsEmployeeManager]

    def post(self, request, pk):
        employee = selectors.get_employee(employee_id=pk)
        if not employee:
            return not_found_response(message="Employee not found.")

        serializer = AssignWorkLocationSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        user = request.user
        try:
            assignment = services.assign_work_location(
                employee=employee,
                work_location=data["work_location"],
                location_type=data.get("location_type", "OFFICE"),
                effective_date=data.get("effective_date"),
                reason=data.get("reason", ""),
                actor_user_id=str(user.id) if user else "",
            )
            return created_response(
                message="Work location assigned successfully.",
                data=WorkforceAssignmentSerializer(assignment).data,
            )
        except Exception as e:
            return validation_error_response(errors={"location": str(e)}, message="Location assignment failed.")


@extend_schema_view(
    post=extend_schema(
        tags=["Workforce Assignments"],
        summary="Assign Team Unit",
        description="Assign employee to an organizational team unit.",
        request=AssignTeamSerializer,
        responses={201: WorkforceAssignmentSerializer},
    )
)
class AssignTeamAPIView(APIView):
    permission_classes = [IsAuthenticated, IsEmployeeManager]

    def post(self, request, pk):
        employee = selectors.get_employee(employee_id=pk)
        if not employee:
            return not_found_response(message="Employee not found.")

        serializer = AssignTeamSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        team = org_selectors.get_team(team_id=data["team_id"])
        if not team:
            return validation_error_response(message="Invalid team specified.")

        user = request.user
        try:
            assignment = services.assign_team(
                employee=employee,
                team=team,
                effective_date=data.get("effective_date"),
                reason=data.get("reason", ""),
                actor_user_id=str(user.id) if user else "",
            )
            return created_response(
                message="Team assigned successfully.",
                data=WorkforceAssignmentSerializer(assignment).data,
            )
        except Exception as e:
            return validation_error_response(errors={"team": str(e)}, message="Team assignment failed.")


@extend_schema_view(
    get=extend_schema(tags=["Workforce Assignments"], summary="List Workforce Assignment History", responses={200: WorkforceAssignmentSerializer(many=True)}),
)
class WorkforceAssignmentListAPIView(APIView):
    permission_classes = [IsAuthenticated, IsEmployeeManager]

    def get(self, request, pk):
        assignments = selectors.list_workforce_assignments(employee_id=pk)
        page = request.query_params.get("page", 1)
        page_size = request.query_params.get("page_size", 20)
        return paginated_response(
            assignments,
            serializer_class=WorkforceAssignmentSerializer,
            message="Workforce assignment history retrieved.",
            page=page,
            page_size=page_size,
        )


# ── Org Chart & Workforce Trees Views ─────────────────────────────────────────


@extend_schema_view(
    get=extend_schema(tags=["Workforce Trees"], summary="Retrieve Organization Tree Structure", responses={200: OpenApiResponse()}),
)
class OrganizationTreeAPIView(APIView):
    permission_classes = [IsAuthenticated, IsEmployeeManager]

    def get(self, request, org_pk):
        tree = selectors.get_organization_tree(organization_id=org_pk)
        return success_response(message="Organization tree structure retrieved.", data=tree)


@extend_schema_view(
    get=extend_schema(tags=["Workforce Trees"], summary="Retrieve Department Tree Structure", responses={200: OpenApiResponse()}),
)
class DepartmentTreeAPIView(APIView):
    permission_classes = [IsAuthenticated, IsEmployeeManager]

    def get(self, request, org_pk):
        tree = selectors.get_department_tree(organization_id=org_pk)
        return success_response(message="Department tree structure retrieved.", data=tree)


@extend_schema_view(
    get=extend_schema(tags=["Workforce Trees"], summary="Retrieve Team Tree Structure", responses={200: OpenApiResponse()}),
)
class TeamTreeAPIView(APIView):
    permission_classes = [IsAuthenticated, IsEmployeeManager]

    def get(self, request, org_pk):
        tree = selectors.get_team_tree(organization_id=org_pk)
        return success_response(message="Team tree structure retrieved.", data=tree)


# ── Employee Lifecycle & Resignation Views ───────────────────────────────────


@extend_schema_view(
    post=extend_schema(
        tags=["Employee Lifecycle"],
        summary="Transition Employee Lifecycle Status (FSM)",
        description="Transition employee lifecycle status adhering to strict 14-state FSM state machine rules.",
        request=EmployeeTransitionStatusSerializer,
        responses={200: EmployeeDetailSerializer, 400: OpenApiResponse(description="Invalid state transition.")},
    )
)
class EmployeeTransitionStatusAPIView(APIView):
    permission_classes = [IsAuthenticated, IsEmployeeManager]

    def post(self, request, pk):
        employee = selectors.get_employee(employee_id=pk)
        if not employee:
            return not_found_response(message="Employee not found.")

        serializer = EmployeeTransitionStatusSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = request.user

        try:
            employee = services.transition_employee_lifecycle_status(
                employee=employee,
                target_status=serializer.validated_data["target_status"],
                reason=serializer.validated_data.get("reason", ""),
                user_id=str(user.id) if user else "",
                user_email=getattr(user, "email", ""),
                ip_address=request.META.get("REMOTE_ADDR"),
                request_id=getattr(request, "request_id", ""),
            )
            return success_response(
                message="Employee lifecycle status transitioned successfully.",
                data=EmployeeDetailSerializer(employee).data,
            )
        except Exception as e:
            return validation_error_response(errors={"target_status": str(e)}, message="Lifecycle transition failed.")


@extend_schema_view(
    post=extend_schema(
        tags=["Employee Lifecycle"],
        summary="Confirm Employee Probation",
        description="Confirm probation and transition employee status to CONFIRMED.",
        request=EmployeeConfirmSerializer,
        responses={200: EmployeeDetailSerializer},
    )
)
class EmployeeConfirmAPIView(APIView):
    permission_classes = [IsAuthenticated, IsEmployeeManager]

    def post(self, request, pk):
        employee = selectors.get_employee(employee_id=pk)
        if not employee:
            return not_found_response(message="Employee not found.")

        serializer = EmployeeConfirmSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = request.user

        try:
            employee = services.confirm_employee_probation(
                employee=employee,
                confirmation_date=serializer.validated_data.get("confirmation_date"),
                remarks=serializer.validated_data.get("remarks", ""),
                user_id=str(user.id) if user else "",
                user_email=getattr(user, "email", ""),
            )
            return success_response(
                message="Employee probation confirmed successfully.",
                data=EmployeeDetailSerializer(employee).data,
            )
        except Exception as e:
            return validation_error_response(errors={"probation": str(e)}, message="Confirmation failed.")


@extend_schema_view(
    post=extend_schema(
        tags=["Employee Resignation"],
        summary="Submit Resignation",
        description="Submit a formal resignation request for an employee.",
        request=EmployeeResignationSubmitSerializer,
        responses={201: EmployeeResignationSerializer},
    )
)
class EmployeeResignAPIView(APIView):
    permission_classes = [IsAuthenticated, IsEmployeeManager]

    def post(self, request, pk):
        employee = selectors.get_employee(employee_id=pk)
        if not employee:
            return not_found_response(message="Employee not found.")

        serializer = EmployeeResignationSubmitSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = request.user

        try:
            resignation = services.submit_resignation(
                employee=employee,
                resignation_date=serializer.validated_data["resignation_date"],
                notice_period_days=serializer.validated_data.get("notice_period_days", 30),
                requested_exit_date=serializer.validated_data.get("requested_exit_date"),
                reason=serializer.validated_data.get("reason", ""),
                user_id=str(user.id) if user else "",
                user_email=getattr(user, "email", ""),
            )
            return created_response(
                message="Resignation submitted successfully.",
                data=EmployeeResignationSerializer(resignation).data,
            )
        except Exception as e:
            return validation_error_response(errors={"resignation": str(e)}, message="Resignation submission failed.")


@extend_schema_view(
    patch=extend_schema(
        tags=["Employee Resignation"],
        summary="Approve Resignation",
        description="Approve resignation request and transition employee into NOTICE_PERIOD.",
        request=EmployeeResignationApproveSerializer,
        responses={200: EmployeeResignationSerializer},
    ),
    delete=extend_schema(
        tags=["Employee Resignation"],
        summary="Withdraw Resignation",
        description="Withdraw active resignation request and restore employee to ACTIVE state.",
        responses={200: OpenApiResponse(description="Resignation withdrawn.")},
    ),
)
class EmployeeResignationActionAPIView(APIView):
    permission_classes = [IsAuthenticated, IsEmployeeManager]

    def patch(self, request, pk):
        resignation = selectors.get_active_resignation(employee_id=pk)
        if not resignation:
            return not_found_response(message="No active resignation request found for employee.")

        serializer = EmployeeResignationApproveSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = request.user

        try:
            resignation = services.approve_resignation(
                resignation=resignation,
                approved_exit_date=serializer.validated_data.get("approved_exit_date"),
                comments=serializer.validated_data.get("comments", ""),
                processed_by_id=str(user.id) if user else "",
            )
            return updated_response(
                message="Resignation approved successfully.",
                data=EmployeeResignationSerializer(resignation).data,
            )
        except Exception as e:
            return validation_error_response(errors={"resignation": str(e)}, message="Approval failed.")

    def delete(self, request, pk):
        resignation = selectors.get_active_resignation(employee_id=pk)
        if not resignation:
            return not_found_response(message="No active resignation request found for employee.")

        try:
            services.withdraw_resignation(resignation=resignation, remarks=request.data.get("remarks", ""))
            return success_response(message="Resignation request withdrawn successfully.")
        except Exception as e:
            return validation_error_response(errors={"resignation": str(e)}, message="Withdrawal failed.")


@extend_schema_view(
    get=extend_schema(
        tags=["Employee Hierarchy"],
        summary="Retrieve Org Chart Reporting Hierarchy",
        description="Retrieve recursive organizational reporting tree for an employee up to max depth.",
        responses={200: OpenApiResponse(description="Organizational chart hierarchy dictionary.")},
    )
)
class EmployeeOrgChartAPIView(APIView):
    permission_classes = [IsAuthenticated, IsEmployeeManager]

    def get(self, request, pk):
        employee = selectors.get_employee(employee_id=pk)
        if not employee:
            return not_found_response(message="Employee not found.")
        tree = selectors.get_org_chart_hierarchy(employee_id=pk)
        return success_response(message="Organizational reporting hierarchy retrieved.", data=tree)


@extend_schema_view(
    get=extend_schema(
        tags=["Employee Audit"],
        summary="List Employee Audit Events",
        responses={200: EmployeeAuditEventSerializer(many=True)},
    )
)
class EmployeeAuditEventListAPIView(APIView):
    permission_classes = [IsAuthenticated, IsEmployeeManager]

    def get(self, request, pk):
        events = selectors.list_employee_audit_events(employee_id=pk)
        page = request.query_params.get("page", 1)
        page_size = request.query_params.get("page_size", 20)
        return paginated_response(
            events,
            serializer_class=EmployeeAuditEventSerializer,
            message="Employee audit log trail retrieved.",
            page=page,
            page_size=page_size,
        )


# ── Employee CRUD Views ──────────────────────────────────────────────────────


@extend_schema_view(
    get=extend_schema(
        tags=["Employees"],
        summary="List Employees",
        description="Retrieve a paginated list of employees for an organization with optional filters.",
        responses={200: EmployeeSerializer(many=True)},
    ),
    post=extend_schema(
        tags=["Employees"],
        summary="Create Employee",
        description="Execute atomic Employee creation and Profile initialization workflow.",
        request=EmployeeCreateSerializer,
        responses={201: EmployeeDetailSerializer, 400: OpenApiResponse(description="Validation error.")},
    ),
)
class EmployeeListAPIView(APIView):
    permission_classes = [IsAuthenticated, IsEmployeeManager]

    def get(self, request):
        organization_id = request.query_params.get("organization_id")
        if not organization_id:
            orgs = org_selectors.list_organizations()
            if orgs.exists():
                organization_id = str(orgs.first().id)
            else:
                return validation_error_response(errors={"organization_id": "organization_id query parameter is required."})

        employees = selectors.list_employees(
            organization_id=organization_id,
            branch_id=request.query_params.get("branch_id"),
            department_id=request.query_params.get("department_id"),
            designation_id=request.query_params.get("designation_id"),
            employment_status=request.query_params.get("employment_status"),
            search=request.query_params.get("search"),
        )
        page = request.query_params.get("page", 1)
        page_size = request.query_params.get("page_size", 20)
        return paginated_response(
            employees,
            serializer_class=EmployeeSerializer,
            message="Employees retrieved successfully.",
            page=page,
            page_size=page_size,
        )

    def post(self, request):
        serializer = EmployeeCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        org = org_selectors.get_organization(organization_id=data["organization_id"])
        branch = org_selectors.get_branch(branch_id=data["branch_id"])
        dept = org_selectors.get_department(department_id=data["department_id"])
        desig = org_selectors.get_designation(designation_id=data["designation_id"])

        if not org or not branch or not dept or not desig:
            return validation_error_response(message="Invalid hierarchy IDs specified.")

        team = org_selectors.get_team(team_id=data["team_id"]) if data.get("team_id") else None
        manager = selectors.get_employee(employee_id=data["reporting_manager_id"]) if data.get("reporting_manager_id") else None
        shift = org_selectors.get_shift(shift_id=data["shift_id"]) if data.get("shift_id") else None

        try:
            employee = services.create_employee(
                organization=org,
                branch=branch,
                department=dept,
                designation=desig,
                team=team,
                reporting_manager=manager,
                shift=shift,
                first_name=data["first_name"],
                last_name=data["last_name"],
                official_email=data["official_email"],
                official_phone=data.get("official_phone", ""),
                date_of_joining=data["date_of_joining"],
                employment_type=data.get("employment_type", "FULL_TIME"),
                employment_status=data.get("employment_status", "PROBATION"),
                probation_period_months=data.get("probation_period_months", 3),
                work_location=data.get("work_location", ""),
                gender=data.get("gender", ""),
                date_of_birth=data.get("date_of_birth"),
                blood_group=data.get("blood_group", ""),
                nationality=data.get("nationality", ""),
                marital_status=data.get("marital_status", ""),
                personal_email=data.get("personal_email", ""),
                personal_phone=data.get("personal_phone", ""),
                current_address=data.get("current_address", ""),
                permanent_address=data.get("permanent_address", ""),
                city=data.get("city", ""),
                state=data.get("state", ""),
                country=data.get("country", ""),
                postal_code=data.get("postal_code", ""),
                pan_number=data.get("pan_number", ""),
                aadhaar_number=data.get("aadhaar_number", ""),
                passport_number=data.get("passport_number", ""),
            )
            return created_response(
                message="Employee record created successfully.",
                data=EmployeeDetailSerializer(employee).data,
            )
        except Exception as e:
            return validation_error_response(errors={"employee": str(e)}, message="Employee creation failed.")


@extend_schema_view(
    get=extend_schema(tags=["Employees"], summary="Retrieve Employee Details", responses={200: EmployeeDetailSerializer}),
    patch=extend_schema(tags=["Employees"], summary="Update Employee Record", request=EmployeeSerializer, responses={200: EmployeeDetailSerializer}),
    delete=extend_schema(tags=["Employees"], summary="Soft Delete Employee", responses={204: OpenApiResponse()}),
)
class EmployeeDetailAPIView(APIView):
    permission_classes = [IsAuthenticated, IsEmployeeManager]

    def get(self, request, pk):
        employee = selectors.get_employee(employee_id=pk)
        if not employee:
            return not_found_response(message="Employee not found.")
        return success_response(message="Employee details retrieved.", data=EmployeeDetailSerializer(employee).data)

    def patch(self, request, pk):
        employee = selectors.get_employee(employee_id=pk)
        if not employee:
            return not_found_response(message="Employee not found.")
        serializer = EmployeeSerializer(data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        try:
            employee = services.update_employee(employee=employee, **serializer.validated_data)
            return updated_response(message="Employee record updated.", data=EmployeeDetailSerializer(employee).data)
        except Exception as e:
            return validation_error_response(errors={"employee": str(e)}, message="Update failed.")

    def delete(self, request, pk):
        employee = selectors.get_employee(employee_id=pk)
        if not employee:
            return not_found_response(message="Employee not found.")
        services.soft_delete_employee(employee=employee)
        return deleted_response(message="Employee deleted successfully.")


@extend_schema_view(
    post=extend_schema(
        tags=["Employees"],
        summary="Transfer Employee",
        description="Transfer employee to a new Branch and Department with automated EmploymentHistory audit entry.",
        request=EmployeeTransferSerializer,
        responses={200: EmployeeDetailSerializer},
    )
)
class EmployeeTransferAPIView(APIView):
    permission_classes = [IsAuthenticated, IsEmployeeManager]

    def post(self, request, pk):
        employee = selectors.get_employee(employee_id=pk)
        if not employee:
            return not_found_response(message="Employee not found.")

        serializer = EmployeeTransferSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        new_branch = org_selectors.get_branch(branch_id=data["new_branch_id"])
        new_dept = org_selectors.get_department(department_id=data["new_department_id"])
        if not new_branch or not new_dept:
            return validation_error_response(message="Invalid branch or department specified.")

        try:
            employee = services.transfer_employee(
                employee=employee,
                new_branch=new_branch,
                new_department=new_dept,
                effective_date=data["effective_date"],
                remarks=data.get("remarks", ""),
            )
            return success_response(
                message="Employee transferred successfully.",
                data=EmployeeDetailSerializer(employee).data,
            )
        except Exception as e:
            return validation_error_response(errors={"transfer": str(e)}, message="Transfer failed.")


@extend_schema_view(
    post=extend_schema(
        tags=["Employees"],
        summary="Promote Employee",
        description="Promote employee to a new Designation with automated EmploymentHistory audit entry.",
        request=EmployeePromoteSerializer,
        responses={200: EmployeeDetailSerializer},
    )
)
class EmployeePromoteAPIView(APIView):
    permission_classes = [IsAuthenticated, IsEmployeeManager]

    def post(self, request, pk):
        employee = selectors.get_employee(employee_id=pk)
        if not employee:
            return not_found_response(message="Employee not found.")

        serializer = EmployeePromoteSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        new_desig = org_selectors.get_designation(designation_id=data["new_designation_id"])
        if not new_desig:
            return validation_error_response(message="Invalid designation specified.")

        try:
            employee = services.promote_employee(
                employee=employee,
                new_designation=new_desig,
                effective_date=data["effective_date"],
                remarks=data.get("remarks", ""),
            )
            return success_response(
                message="Employee promoted successfully.",
                data=EmployeeDetailSerializer(employee).data,
            )
        except Exception as e:
            return validation_error_response(errors={"promotion": str(e)}, message="Promotion failed.")


@extend_schema_view(
    get=extend_schema(tags=["Employment History"], summary="List Employment History Audit Trail", responses={200: EmploymentHistorySerializer(many=True)}),
)
class EmploymentHistoryListAPIView(APIView):
    permission_classes = [IsAuthenticated, IsEmployeeManager]

    def get(self, request, emp_pk):
        histories = selectors.list_employment_histories(employee_id=emp_pk)
        page = request.query_params.get("page", 1)
        page_size = request.query_params.get("page_size", 20)
        return paginated_response(
            histories,
            serializer_class=EmploymentHistorySerializer,
            message="Employment history audit trail retrieved.",
            page=page,
            page_size=page_size,
        )
