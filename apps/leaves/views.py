"""Thin REST API views for the Leave Management Foundation Engine."""

from drf_spectacular.utils import OpenApiResponse, extend_schema, extend_schema_view
from rest_framework.permissions import IsAuthenticated
from rest_framework.views import APIView

from core.pagination import paginated_response
from core.responses import (
    created_response,
    not_found_response,
    success_response,
    validation_error_response,
)
from apps.employees.selectors import get_employee
from apps.organizations.selectors import get_organization

from . import selectors, services
from .serializers import (
    ApprovalDelegationCreateSerializer,
    ApprovalDelegationSerializer,
    EmployeeLeaveAnalyticsRequestSerializer,
    ExecutiveDashboardRequestSerializer,
    LeaveAccrualRunSerializer,
    LeaveAnalyticsRequestSerializer,
    LeaveApplySerializer,
    LeaveApprovalDecisionSerializer,
    LeaveBalanceAdjustmentSerializer,
    LeaveBalanceHistorySerializer,
    LeaveBalanceSerializer,
    LeaveCalendarRequestSerializer,
    LeaveCancellationSerializer,
    LeaveCarryForwardRunSerializer,
    LeaveComplianceRequestSerializer,
    LeaveConfigurationSerializer,
    LeaveEligibilityCheckSerializer,
    LeaveExportRequestSerializer,
    LeaveForecastRequestSerializer,
    LeaveKPIRequestSerializer,
    LeaveModificationSerializer,
    LeavePolicySerializer,
    LeaveRequestSerializer,
    LeaveTypeSerializer,
    LeaveWorkingDaysCheckSerializer,
    ManagerDashboardRequestSerializer,
)


@extend_schema_view(
    get=extend_schema(
        tags=["Leave Types"],
        summary="List Leave Types",
        description="Retrieve all configured leave types for an organization.",
        responses={200: LeaveTypeSerializer(many=True)},
    ),
    post=extend_schema(
        tags=["Leave Types"],
        summary="Create Leave Type",
        description="Define a new enterprise leave type (Annual, Casual, Sick, Comp Off, Maternity, etc.).",
        request=LeaveTypeSerializer,
        responses={201: LeaveTypeSerializer},
    ),
)
class LeaveTypeListCreateAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        organization_id = request.query_params.get("organization_id")
        if not organization_id:
            return validation_error_response(message="organization_id query parameter is required.")

        types = selectors.list_leave_types(organization_id=organization_id)
        return success_response(message="Leave types retrieved.", data=LeaveTypeSerializer(types, many=True).data)

    def post(self, request):
        serializer = LeaveTypeSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        org = get_organization(organization_id=data["organization"].id)
        if not org:
            return validation_error_response(message="Invalid organization specified.")

        try:
            leave_type = services.create_leave_type(
                organization=org,
                name=data["name"],
                code=data["code"],
                category=data.get("category", "CASUAL"),
                description=data.get("description", ""),
                is_paid=data.get("is_paid", True),
                is_encashable=data.get("is_encashable", False),
                is_wfh_placeholder=data.get("is_wfh_placeholder", False),
                is_compensatory_off=data.get("is_compensatory_off", False),
                requires_attachment=data.get("requires_attachment", False),
                gender_suitability=data.get("gender_suitability", "ALL"),
            )
            return created_response(
                message="Leave type created successfully.",
                data=LeaveTypeSerializer(leave_type).data,
            )
        except Exception as e:
            return validation_error_response(errors={"leave_type": str(e)}, message="Leave type creation failed.")


@extend_schema_view(
    get=extend_schema(
        tags=["Leave Policies"],
        summary="List Leave Policies",
        responses={200: LeavePolicySerializer(many=True)},
    ),
    post=extend_schema(
        tags=["Leave Policies"],
        summary="Create Leave Policy",
        request=LeavePolicySerializer,
        responses={201: LeavePolicySerializer},
    ),
)
class LeavePolicyListCreateAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        organization_id = request.query_params.get("organization_id")
        if not organization_id:
            return validation_error_response(message="organization_id query parameter is required.")

        from .models import LeavePolicy as LeavePolicyModel
        policies = LeavePolicyModel.objects.filter(organization_id=organization_id, is_active=True)
        return success_response(message="Leave policies retrieved.", data=LeavePolicySerializer(policies, many=True).data)

    def post(self, request):
        serializer = LeavePolicySerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        org = get_organization(organization_id=data["organization"].id)
        leave_type = selectors.get_leave_type(leave_type_id=data["leave_type"].id)
        if not org or not leave_type:
            return validation_error_response(message="Invalid organization or leave type specified.")

        try:
            policy = services.create_leave_policy(
                organization=org,
                leave_type=leave_type,
                name=data["name"],
                code=data["code"],
                max_leave_per_year=data.get("max_leave_per_year"),
                min_leave_per_request=data.get("min_leave_per_request"),
                max_leave_per_request=data.get("max_leave_per_request"),
                half_day_allowed=data.get("half_day_allowed", True),
                hourly_leave_allowed=data.get("hourly_leave_allowed", False),
                negative_balance_allowed=data.get("negative_balance_allowed", False),
                max_negative_balance=data.get("max_negative_balance"),
                carry_forward_allowed=data.get("carry_forward_allowed", False),
                max_carry_forward_days=data.get("max_carry_forward_days"),
                carry_forward_percentage=data.get("carry_forward_percentage"),
                carry_forward_expiry_days=data.get("carry_forward_expiry_days", 90),
                notice_period_days=data.get("notice_period_days", 3),
                max_consecutive_days=data.get("max_consecutive_days", 15),
                min_gap_between_leaves_days=data.get("min_gap_between_leaves_days", 0),
                attachment_required_threshold_days=data.get("attachment_required_threshold_days", 3),
                reset_period=data.get("reset_period", "CALENDAR_YEAR"),
                is_default=data.get("is_default", False),
            )
            return created_response(
                message="Leave policy created successfully.",
                data=LeavePolicySerializer(policy).data,
            )
        except Exception as e:
            return validation_error_response(errors={"policy": str(e)}, message="Leave policy creation failed.")


@extend_schema_view(
    get=extend_schema(
        tags=["Leave Balances"],
        summary="List Leave Balances",
        responses={200: LeaveBalanceSerializer(many=True)},
    ),
    post=extend_schema(
        tags=["Leave Balances"],
        summary="Initialize Employee Leave Balance",
        responses={201: LeaveBalanceSerializer},
    ),
)
class LeaveBalanceListInitAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        employee_id = request.query_params.get("employee_id")
        organization_id = request.query_params.get("organization_id")

        if employee_id:
            balances = selectors.list_employee_leave_balances(employee_id=employee_id)
            return success_response(message="Employee leave balances retrieved.", data=LeaveBalanceSerializer(balances, many=True).data)

        if organization_id:
            balances = selectors.list_organization_leave_balances(organization_id=organization_id)
            return success_response(message="Organization leave balances retrieved.", data=LeaveBalanceSerializer(balances, many=True).data)

        return validation_error_response(message="Either employee_id or organization_id query parameter is required.")

    def post(self, request):
        employee_id = request.data.get("employee_id")
        leave_type_id = request.data.get("leave_type_id")
        opening_balance = request.data.get("opening_balance", "0.00")

        employee = get_employee(employee_id=employee_id)
        leave_type = selectors.get_leave_type(leave_type_id=leave_type_id)

        if not employee or not leave_type:
            return validation_error_response(message="Invalid employee or leave type specified.")

        user = request.user
        try:
            from decimal import Decimal
            bal = services.initialize_employee_leave_balance(
                employee=employee,
                leave_type=leave_type,
                opening_balance=Decimal(str(opening_balance)),
                actor_user_id=str(user.id) if user else "",
                actor_email=getattr(user, "email", ""),
            )
            return created_response(
                message="Leave balance initialized successfully.",
                data=LeaveBalanceSerializer(bal).data,
            )
        except Exception as e:
            return validation_error_response(errors={"balance": str(e)}, message="Balance initialization failed.")


@extend_schema_view(
    post=extend_schema(
        tags=["Leave Balances"],
        summary="Adjust Leave Balance (Credit / Debit / Correction)",
        request=LeaveBalanceAdjustmentSerializer,
        responses={200: LeaveBalanceSerializer},
    )
)
class LeaveBalanceAdjustAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        serializer = LeaveBalanceAdjustmentSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        try:
            from .models import LeaveBalance as LeaveBalanceModel
            bal = LeaveBalanceModel.objects.get(id=data["leave_balance_id"])
        except LeaveBalanceModel.DoesNotExist:
            return not_found_response(message="Leave balance record not found.")

        user = request.user
        try:
            updated_bal = services.adjust_leave_balance(
                leave_balance=bal,
                adjustment_type=data["adjustment_type"],
                delta=data["delta"],
                reason=data["reason"],
                actor_user_id=str(user.id) if user else "",
                actor_email=getattr(user, "email", ""),
            )
            return success_response(
                message="Leave balance adjusted successfully.",
                data=LeaveBalanceSerializer(updated_bal).data,
            )
        except Exception as e:
            return validation_error_response(errors={"adjustment": str(e)}, message="Balance adjustment failed.")


@extend_schema_view(
    post=extend_schema(
        tags=["Leave Accrual Engine"],
        summary="Run Scheduled Leave Accruals",
        request=LeaveAccrualRunSerializer,
        responses={200: OpenApiResponse(description="Accrual run summary.")},
    )
)
class LeaveAccrualRunAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        serializer = LeaveAccrualRunSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        org = get_organization(organization_id=data["organization_id"])
        if not org:
            return validation_error_response(message="Invalid organization specified.")

        try:
            res = services.process_scheduled_accruals(
                organization=org,
                accrual_frequency=data.get("accrual_frequency", "MONTHLY"),
                accrual_date=data.get("accrual_date"),
            )
            return success_response(message="Scheduled leave accruals processed successfully.", data=res)
        except Exception as e:
            return validation_error_response(errors={"accrual": str(e)}, message="Accrual execution failed.")


@extend_schema_view(
    post=extend_schema(
        tags=["Leave Eligibility Engine"],
        summary="Check Leave Eligibility",
        request=LeaveEligibilityCheckSerializer,
        responses={200: OpenApiResponse(description="Eligibility verdict payload.")},
    )
)
class LeaveEligibilityCheckAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        serializer = LeaveEligibilityCheckSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        employee = get_employee(employee_id=data["employee_id"])
        leave_type = selectors.get_leave_type(leave_type_id=data["leave_type_id"])
        if not employee or not leave_type:
            return validation_error_response(message="Invalid employee or leave type specified.")

        is_eligible, reason = selectors.check_leave_eligibility(
            employee=employee,
            leave_type=leave_type,
            requested_days=float(data["requested_days"]),
        )

        return success_response(
            message="Leave eligibility check completed.",
            data={"is_eligible": is_eligible, "reason": reason, "employee_id": str(employee.id), "leave_type_id": str(leave_type.id)},
        )


@extend_schema_view(
    post=extend_schema(
        tags=["Carry Forward Engine"],
        summary="Run Year-End Carry Forward Transfer",
        request=LeaveCarryForwardRunSerializer,
        responses={200: OpenApiResponse(description="Carry forward run summary.")},
    )
)
class LeaveCarryForwardRunAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        serializer = LeaveCarryForwardRunSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        org = get_organization(organization_id=data["organization_id"])
        if not org:
            return validation_error_response(message="Invalid organization specified.")

        try:
            res = services.process_carry_forward(
                organization=org,
                from_year=data["from_year"],
                to_year=data["to_year"],
            )
            return success_response(message="Year-end leave carry forward processed successfully.", data=res)
        except Exception as e:
            return validation_error_response(errors={"carry_forward": str(e)}, message="Carry forward processing failed.")


@extend_schema_view(
    get=extend_schema(
        tags=["Holiday Integration Engine"],
        summary="Calculate Working Days Between Window",
        description="Calculates working days between start_date and end_date factoring in public holidays and weekly off schedules.",
        responses={200: OpenApiResponse(description="Working days calculation payload.")},
    )
)
class LeaveWorkingDaysCheckAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        organization_id = request.query_params.get("organization_id")
        start_date = request.query_params.get("start_date")
        end_date = request.query_params.get("end_date")
        if not all([organization_id, start_date, end_date]):
            return validation_error_response(message="organization_id, start_date, and end_date query parameters are required.")

        try:
            from datetime import date as dt_date
            res = selectors.calculate_working_days_between(
                organization_id=organization_id,
                start_date=dt_date.fromisoformat(start_date),
                end_date=dt_date.fromisoformat(end_date),
            )
            return success_response(message="Working days calculation completed.", data=res)
        except Exception as e:
            return validation_error_response(errors={"working_days": str(e)}, message="Working days calculation failed.")


# ── Leave Request & Approval Workflow Views ──────────────────────────────────


@extend_schema_view(
    post=extend_schema(
        tags=["Leave Requests"],
        summary="Apply for Leave",
        description="Submit a new leave application or save as draft with automated policy and overlap validation.",
        request=LeaveApplySerializer,
        responses={201: LeaveRequestSerializer},
    )
)
class LeaveApplyAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        serializer = LeaveApplySerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        employee = get_employee(employee_id=data["employee_id"])
        leave_type = selectors.get_leave_type(leave_type_id=data["leave_type_id"])
        if not employee or not leave_type:
            return validation_error_response(message="Invalid employee or leave type specified.")

        try:
            req = services.apply_leave_request(
                employee=employee,
                leave_type=leave_type,
                start_date=data["start_date"],
                end_date=data["end_date"],
                reason=data["reason"],
                is_half_day=data.get("is_half_day", False),
                half_day_period=data.get("half_day_period"),
                attachment_url=data.get("attachment_url", ""),
                is_emergency=data.get("is_emergency", False),
                is_draft=data.get("is_draft", False),
            )
            return created_response(message="Leave application created successfully.", data=LeaveRequestSerializer(req).data)
        except Exception as e:
            return validation_error_response(errors={"application": str(e)}, message="Leave application failed.")


@extend_schema_view(
    post=extend_schema(
        tags=["Leave Requests"],
        summary="Submit Draft Leave Request",
        responses={200: LeaveRequestSerializer},
    )
)
class LeaveSubmitAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, pk):
        req = selectors.get_leave_request(request_id=pk)
        if not req:
            return not_found_response(message="Leave request not found.")

        try:
            sub_req = services.submit_leave_request(leave_request=req, actor_email=getattr(request.user, "email", ""))
            return success_response(message="Leave request submitted for approval.", data=LeaveRequestSerializer(sub_req).data)
        except Exception as e:
            return validation_error_response(errors={"submit": str(e)}, message="Leave request submission failed.")


@extend_schema_view(
    post=extend_schema(
        tags=["Leave Approvals"],
        summary="Approve Leave Request",
        request=LeaveApprovalDecisionSerializer,
        responses={200: LeaveRequestSerializer},
    )
)
class LeaveApproveAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, pk):
        serializer = LeaveApprovalDecisionSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        req = selectors.get_leave_request(request_id=pk)
        approver = get_employee(employee_id=data["approver_employee_id"])
        if not req or not approver:
            return validation_error_response(message="Invalid leave request or approver specified.")

        user = request.user
        try:
            app_req = services.approve_leave_request(
                leave_request=req,
                approver=approver,
                comments=data.get("comments", ""),
                actor_user_id=str(user.id) if user else "",
                actor_email=getattr(user, "email", ""),
            )
            return success_response(message="Leave request approved successfully.", data=LeaveRequestSerializer(app_req).data)
        except Exception as e:
            return validation_error_response(errors={"approval": str(e)}, message="Leave approval failed.")


@extend_schema_view(
    post=extend_schema(
        tags=["Leave Approvals"],
        summary="Reject Leave Request",
        request=LeaveApprovalDecisionSerializer,
        responses={200: LeaveRequestSerializer},
    )
)
class LeaveRejectAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, pk):
        serializer = LeaveApprovalDecisionSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        req = selectors.get_leave_request(request_id=pk)
        approver = get_employee(employee_id=data["approver_employee_id"])
        if not req or not approver:
            return validation_error_response(message="Invalid leave request or approver specified.")

        user = request.user
        try:
            rej_req = services.reject_leave_request(
                leave_request=req,
                approver=approver,
                rejection_reason=data.get("rejection_reason", "Leave request rejected by manager."),
                actor_user_id=str(user.id) if user else "",
                actor_email=getattr(user, "email", ""),
            )
            return success_response(message="Leave request rejected.", data=LeaveRequestSerializer(rej_req).data)
        except Exception as e:
            return validation_error_response(errors={"rejection": str(e)}, message="Leave rejection failed.")


@extend_schema_view(
    post=extend_schema(
        tags=["Leave Workflow"],
        summary="Cancel Leave Request",
        request=LeaveCancellationSerializer,
        responses={200: LeaveRequestSerializer},
    )
)
class LeaveCancelAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, pk):
        serializer = LeaveCancellationSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        req = selectors.get_leave_request(request_id=pk)
        if not req:
            return not_found_response(message="Leave request not found.")

        user = request.user
        try:
            can_req = services.cancel_leave_request(
                leave_request=req,
                cancellation_reason=data["cancellation_reason"],
                actor_user_id=str(user.id) if user else "",
                actor_email=getattr(user, "email", ""),
            )
            return success_response(message="Leave request cancelled and balance restored.", data=LeaveRequestSerializer(can_req).data)
        except Exception as e:
            return validation_error_response(errors={"cancellation": str(e)}, message="Leave cancellation failed.")


@extend_schema_view(
    post=extend_schema(
        tags=["Leave Workflow"],
        summary="Withdraw Leave Request",
        responses={200: LeaveRequestSerializer},
    )
)
class LeaveWithdrawAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, pk):
        req = selectors.get_leave_request(request_id=pk)
        if not req:
            return not_found_response(message="Leave request not found.")

        user = request.user
        try:
            with_req = services.withdraw_leave_request(
                leave_request=req,
                actor_user_id=str(user.id) if user else "",
                actor_email=getattr(user, "email", ""),
            )
            return success_response(message="Leave request withdrawn successfully.", data=LeaveRequestSerializer(with_req).data)
        except Exception as e:
            return validation_error_response(errors={"withdrawal": str(e)}, message="Leave withdrawal failed.")


@extend_schema_view(
    put=extend_schema(
        tags=["Leave Workflow"],
        summary="Modify Pending Leave Request",
        request=LeaveModificationSerializer,
        responses={200: LeaveRequestSerializer},
    )
)
class LeaveModifyAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def put(self, request, pk):
        serializer = LeaveModificationSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        req = selectors.get_leave_request(request_id=pk)
        if not req:
            return not_found_response(message="Leave request not found.")

        user = request.user
        try:
            mod_req = services.modify_leave_request(
                leave_request=req,
                new_start_date=data.get("new_start_date"),
                new_end_date=data.get("new_end_date"),
                new_reason=data.get("new_reason", ""),
                actor_user_id=str(user.id) if user else "",
                actor_email=getattr(user, "email", ""),
            )
            return success_response(message="Leave request modified successfully.", data=LeaveRequestSerializer(mod_req).data)
        except Exception as e:
            return validation_error_response(errors={"modification": str(e)}, message="Leave modification failed.")


@extend_schema_view(
    get=extend_schema(
        tags=["Leave Requests"],
        summary="List Leave Requests",
        responses={200: LeaveRequestSerializer(many=True)},
    )
)
class LeaveRequestListAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        employee_id = request.query_params.get("employee_id")
        status = request.query_params.get("status")
        if not employee_id:
            return validation_error_response(message="employee_id query parameter is required.")

        reqs = selectors.list_employee_leave_requests(employee_id=employee_id, status=status)
        return success_response(message="Leave requests retrieved.", data=LeaveRequestSerializer(reqs, many=True).data)


@extend_schema_view(
    get=extend_schema(
        tags=["Leave Approvals"],
        summary="List Pending Approvals Queue",
        description="Retrieve all pending leave requests assigned to a manager or delegated approver.",
        responses={200: LeaveRequestSerializer(many=True)},
    )
)
class LeavePendingApprovalsAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        approver_id = request.query_params.get("approver_employee_id")
        if not approver_id:
            return validation_error_response(message="approver_employee_id query parameter is required.")

        pending = selectors.list_pending_approval_requests(approver_employee_id=approver_id)
        return success_response(message="Pending leave approval queue retrieved.", data=LeaveRequestSerializer(pending, many=True).data)


@extend_schema_view(
    get=extend_schema(
        tags=["Approval Delegations"],
        summary="List Approval Delegations",
        responses={200: ApprovalDelegationSerializer(many=True)},
    ),
    post=extend_schema(
        tags=["Approval Delegations"],
        summary="Create Approval Delegation Rule",
        request=ApprovalDelegationCreateSerializer,
        responses={201: ApprovalDelegationSerializer},
    ),
)
class LeaveDelegationListCreateAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        organization_id = request.query_params.get("organization_id")
        if not organization_id:
            return validation_error_response(message="organization_id query parameter is required.")

        from .models import ApprovalDelegation
        delegations = ApprovalDelegation.objects.filter(organization_id=organization_id, is_active=True)
        return success_response(message="Approval delegations retrieved.", data=ApprovalDelegationSerializer(delegations, many=True).data)

    def post(self, request):
        serializer = ApprovalDelegationCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        org = get_organization(organization_id=data["organization_id"])
        delegator = get_employee(employee_id=data["delegator_id"])
        delegatee = get_employee(employee_id=data["delegatee_id"])

        if not all([org, delegator, delegatee]):
            return validation_error_response(message="Invalid organization, delegator, or delegatee specified.")

        try:
            dlg = services.create_approval_delegation(
                organization=org,
                delegator=delegator,
                delegatee=delegatee,
                start_date=data["start_date"],
                end_date=data["end_date"],
                reason=data.get("reason", ""),
            )
            return created_response(message="Approval delegation created successfully.", data=ApprovalDelegationSerializer(dlg).data)
        except Exception as e:
            return validation_error_response(errors={"delegation": str(e)}, message="Approval delegation creation failed.")


@extend_schema_view(
    get=extend_schema(
        tags=["Leave Calendar"],
        summary="Get Leave Calendar Events",
        description="Aggregates approved leaves, public holidays, and conflict signals across Employee, Team, Department, or Organization scope.",
        responses={200: OpenApiResponse(description="Calendar events payload.")},
    )
)
class LeaveCalendarAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        organization_id = request.query_params.get("organization_id")
        start_date = request.query_params.get("start_date")
        end_date = request.query_params.get("end_date")
        scope = request.query_params.get("scope", "ORGANIZATION")
        target_id = request.query_params.get("target_id")

        if not all([organization_id, start_date, end_date]):
            return validation_error_response(message="organization_id, start_date, and end_date query parameters are required.")

        try:
            from datetime import date as dt_date
            events = selectors.get_leave_calendar_events(
                organization_id=organization_id,
                start_date=dt_date.fromisoformat(start_date),
                end_date=dt_date.fromisoformat(end_date),
                scope=scope,
                target_id=target_id,
            )
            return success_response(message="Leave calendar events retrieved.", data={"total_events": len(events), "events": events})
        except Exception as e:
            return validation_error_response(errors={"calendar": str(e)}, message="Leave calendar query failed.")


# ── Leave Analytics & Compliance Engine Views ─────────────────────────────────


@extend_schema(
    tags=["Leave Analytics"],
    summary="Employee Leave Analytics",
    description="Comprehensive leave analytics for an individual employee.",
)
class EmployeeLeaveAnalyticsAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        employee_id = request.query_params.get("employee_id")
        if not employee_id:
            return validation_error_response(message="employee_id query parameter is required.")

        data = selectors.get_employee_leave_analytics(employee_id=employee_id)
        return success_response(message="Employee leave analytics retrieved.", data=data)


@extend_schema(
    tags=["Leave Analytics"],
    summary="Team Leave Analytics",
    description="Leave analytics aggregated for a team.",
)
class TeamLeaveAnalyticsAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        organization_id = request.query_params.get("organization_id")
        start_date = request.query_params.get("start_date")
        end_date = request.query_params.get("end_date")
        if not all([organization_id, start_date, end_date]):
            return validation_error_response(message="organization_id, start_date, and end_date are required.")

        from datetime import date as dt_date
        data = selectors.get_organization_leave_analytics(
            organization_id=organization_id, start_date=dt_date.fromisoformat(start_date), end_date=dt_date.fromisoformat(end_date),
        )
        return success_response(message="Team leave analytics retrieved.", data=data)


@extend_schema(
    tags=["Leave Analytics"],
    summary="Department Leave Analytics",
    description="Leave analytics aggregated for a department.",
)
class DepartmentLeaveAnalyticsAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        organization_id = request.query_params.get("organization_id")
        start_date = request.query_params.get("start_date")
        end_date = request.query_params.get("end_date")
        if not all([organization_id, start_date, end_date]):
            return validation_error_response(message="organization_id, start_date, and end_date are required.")

        from datetime import date as dt_date
        data = selectors.get_organization_leave_analytics(
            organization_id=organization_id, start_date=dt_date.fromisoformat(start_date), end_date=dt_date.fromisoformat(end_date),
        )
        return success_response(message="Department leave analytics retrieved.", data=data)


@extend_schema(
    tags=["Leave Analytics"],
    summary="Branch Leave Analytics",
    description="Leave analytics aggregated for a branch.",
)
class BranchLeaveAnalyticsAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        organization_id = request.query_params.get("organization_id")
        start_date = request.query_params.get("start_date")
        end_date = request.query_params.get("end_date")
        if not all([organization_id, start_date, end_date]):
            return validation_error_response(message="organization_id, start_date, and end_date are required.")

        from datetime import date as dt_date
        data = selectors.get_organization_leave_analytics(
            organization_id=organization_id, start_date=dt_date.fromisoformat(start_date), end_date=dt_date.fromisoformat(end_date),
        )
        return success_response(message="Branch leave analytics retrieved.", data=data)


@extend_schema(
    tags=["Leave Analytics"],
    summary="Organization Leave Analytics",
    description="Organization-wide leave analytics and utilization trends.",
)
class OrganizationLeaveAnalyticsAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        organization_id = request.query_params.get("organization_id")
        start_date = request.query_params.get("start_date")
        end_date = request.query_params.get("end_date")
        if not all([organization_id, start_date, end_date]):
            return validation_error_response(message="organization_id, start_date, and end_date are required.")

        from datetime import date as dt_date
        data = selectors.get_organization_leave_analytics(
            organization_id=organization_id, start_date=dt_date.fromisoformat(start_date), end_date=dt_date.fromisoformat(end_date),
        )
        return success_response(message="Organization leave analytics retrieved.", data=data)


@extend_schema(
    tags=["Leave Analytics"],
    summary="Leave KPIs",
    description="Calculate core leave KPIs: Utilization %, Rejection %, Cancellation %, Availability %.",
)
class LeaveKPIsAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        organization_id = request.query_params.get("organization_id")
        start_date = request.query_params.get("start_date")
        end_date = request.query_params.get("end_date")
        if not all([organization_id, start_date, end_date]):
            return validation_error_response(message="organization_id, start_date, and end_date are required.")

        from datetime import date as dt_date
        data = selectors.calculate_leave_kpis(
            organization_id=organization_id, start_date=dt_date.fromisoformat(start_date), end_date=dt_date.fromisoformat(end_date),
        )
        return success_response(message="Leave KPIs calculated.", data=data)


@extend_schema(
    tags=["Leave Compliance"],
    summary="Leave Compliance Audit",
    description="Audit policy violations and calculate Organization Compliance Risk Score (0-100).",
)
class LeaveComplianceAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        organization_id = request.query_params.get("organization_id")
        start_date = request.query_params.get("start_date")
        end_date = request.query_params.get("end_date")
        if not all([organization_id, start_date, end_date]):
            return validation_error_response(message="organization_id, start_date, and end_date are required.")

        from datetime import date as dt_date
        org = get_organization(organization_id=organization_id)
        if not org:
            return not_found_response(message="Organization not found.")

        data = services.audit_leave_compliance(
            organization=org, start_date=dt_date.fromisoformat(start_date), end_date=dt_date.fromisoformat(end_date),
        )
        return success_response(message="Leave compliance audit completed.", data=data)


@extend_schema(
    tags=["Leave Forecasting"],
    summary="Leave Forecast Data",
    description="AI Forecast Foundation: Reusable time-series structures for seasonal demand & burnout indicators.",
)
class LeaveForecastAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        organization_id = request.query_params.get("organization_id")
        if not organization_id:
            return validation_error_response(message="organization_id query parameter is required.")

        data = selectors.get_leave_forecast_data(organization_id=organization_id)
        return success_response(message="Leave forecast data retrieved.", data=data)


@extend_schema(
    tags=["Leave Dashboards"],
    summary="Executive Leave Dashboard",
    description="Executive-level leave dashboard aggregating KPIs, compliance, and analytics for CEO / C-Suite.",
)
class ExecutiveLeaveDashboardAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        organization_id = request.query_params.get("organization_id")
        if not organization_id:
            return validation_error_response(message="organization_id query parameter is required.")

        data = selectors.get_executive_leave_dashboard(organization_id=organization_id)
        return success_response(message="Executive leave dashboard retrieved.", data=data)


@extend_schema(
    tags=["Leave Dashboards"],
    summary="Manager Leave Dashboard",
    description="Manager dashboard showing direct report team absence & pending approvals.",
)
class ManagerLeaveDashboardAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        manager_id = request.query_params.get("manager_id")
        if not manager_id:
            return validation_error_response(message="manager_id query parameter is required.")

        data = selectors.get_manager_leave_dashboard(manager_id=manager_id)
        return success_response(message="Manager leave dashboard retrieved.", data=data)


@extend_schema(
    tags=["Leave Reports"],
    summary="Leave Export Report (CSV)",
    description="Generate CSV export for leave utilization, compliance, or summary reports.",
)
class LeaveExportReportAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        serializer = LeaveExportRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        org = get_organization(organization_id=data["organization_id"])
        if not org:
            return not_found_response(message="Organization not found.")

        try:
            csv_content = services.generate_leave_export_csv(
                organization=org,
                report_type=data["report_type"],
                start_date=data["start_date"],
                end_date=data["end_date"],
            )
            from django.http import HttpResponse
            response = HttpResponse(csv_content, content_type="text/csv")
            response["Content-Disposition"] = f'attachment; filename="leave_report_{org.code}.csv"'
            return response
        except Exception as e:
            return validation_error_response(errors={"export": str(e)}, message="Leave export generation failed.")
