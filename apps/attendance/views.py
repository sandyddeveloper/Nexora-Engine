"""Thin API views for the Attendance Foundation & Processing Engine."""

from drf_spectacular.utils import OpenApiResponse, extend_schema, extend_schema_view
from rest_framework.permissions import IsAuthenticated
from rest_framework.views import APIView

from core.pagination import paginated_response
from core.responses import (
    created_response,
    not_found_response,
    success_response,
    updated_response,
    validation_error_response,
)
from apps.employees import selectors as emp_selectors
from apps.organizations import selectors as org_selectors

from . import selectors, services
from .serializers import (
    AttendanceBreakSerializer,
    AttendanceConfigurationSerializer,
    AttendanceCorrectionProcessSerializer,
    AttendanceCorrectionRequestSerializer,
    AttendanceCorrectionSubmitSerializer,
    AttendanceLockUnlockSerializer,
    AttendancePolicySerializer,
    AttendanceRecordCreateSerializer,
    AttendanceRecordSerializer,
    AttendanceRecordUpdateSerializer,
    AttendanceSessionSerializer,
    BreakEndSerializer,
    BreakStartSerializer,
    BulkAttendanceImportSerializer,
    CheckInSerializer,
    CheckOutSerializer,
)


@extend_schema_view(
    post=extend_schema(
        tags=["Attendance Processing"],
        summary="Employee Check-In",
        description="Execute Check-In workflow opening active session and daily AttendanceRecord.",
        request=CheckInSerializer,
        responses={201: AttendanceSessionSerializer},
    )
)
class CheckInAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        serializer = CheckInSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        employee = emp_selectors.get_employee(employee_id=data["employee_id"])
        if not employee:
            return validation_error_response(message="Invalid employee specified.")

        user = request.user
        try:
            session = services.check_in_employee(
                employee=employee,
                check_in_time=data.get("check_in_time"),
                source=data.get("source", "WEB"),
                work_location=data.get("work_location", ""),
                remarks=data.get("remarks", ""),
                actor_user_id=str(user.id) if user else "",
                actor_email=getattr(user, "email", ""),
            )
            return created_response(
                message="Check-In executed successfully.",
                data=AttendanceSessionSerializer(session).data,
            )
        except Exception as e:
            return validation_error_response(errors={"check_in": str(e)}, message="Check-In failed.")


@extend_schema_view(
    post=extend_schema(
        tags=["Attendance Processing"],
        summary="Employee Check-Out",
        description="Execute Check-Out workflow closing session and triggering daily metrics calculation.",
        request=CheckOutSerializer,
        responses={200: AttendanceSessionSerializer},
    )
)
class CheckOutAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        serializer = CheckOutSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        employee = emp_selectors.get_employee(employee_id=data["employee_id"])
        if not employee:
            return validation_error_response(message="Invalid employee specified.")

        user = request.user
        try:
            session = services.check_out_employee(
                employee=employee,
                check_out_time=data.get("check_out_time"),
                force=data.get("force", False),
                remarks=data.get("remarks", ""),
                actor_user_id=str(user.id) if user else "",
                actor_email=getattr(user, "email", ""),
            )
            return success_response(
                message="Check-Out executed successfully.",
                data=AttendanceSessionSerializer(session).data,
            )
        except Exception as e:
            return validation_error_response(errors={"check_out": str(e)}, message="Check-Out failed.")


@extend_schema_view(
    post=extend_schema(
        tags=["Break Management"],
        summary="Start Break Interval",
        description="Start a lunch, tea, personal, or official break interval for active session.",
        request=BreakStartSerializer,
        responses={201: AttendanceBreakSerializer},
    )
)
class BreakStartAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        serializer = BreakStartSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        employee = emp_selectors.get_employee(employee_id=data["employee_id"])
        if not employee:
            return validation_error_response(message="Invalid employee specified.")

        try:
            brk = services.start_break(
                employee=employee,
                break_type=data.get("break_type", "LUNCH"),
                start_time=data.get("start_time"),
                is_paid=data.get("is_paid", False),
            )
            return created_response(
                message="Break started successfully.",
                data=AttendanceBreakSerializer(brk).data,
            )
        except Exception as e:
            return validation_error_response(errors={"break": str(e)}, message="Break start failed.")


@extend_schema_view(
    post=extend_schema(
        tags=["Break Management"],
        summary="End Break Interval",
        description="End active break interval and resume work.",
        request=BreakEndSerializer,
        responses={200: AttendanceBreakSerializer},
    )
)
class BreakEndAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        serializer = BreakEndSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        employee = emp_selectors.get_employee(employee_id=data["employee_id"])
        if not employee:
            return validation_error_response(message="Invalid employee specified.")

        try:
            brk = services.end_break(
                employee=employee,
                end_time=data.get("end_time"),
            )
            return success_response(
                message="Break ended successfully.",
                data=AttendanceBreakSerializer(brk).data,
            )
        except Exception as e:
            return validation_error_response(errors={"break": str(e)}, message="Break end failed.")


@extend_schema_view(
    get=extend_schema(
        tags=["Attendance Corrections"],
        summary="List Pending Correction Requests",
        responses={200: AttendanceCorrectionRequestSerializer(many=True)},
    ),
    post=extend_schema(
        tags=["Attendance Corrections"],
        summary="Submit Attendance Correction Request",
        request=AttendanceCorrectionSubmitSerializer,
        responses={201: AttendanceCorrectionRequestSerializer},
    ),
)
class AttendanceCorrectionListSubmitAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        organization_id = request.query_params.get("organization_id")
        if not organization_id:
            orgs = org_selectors.list_organizations()
            if orgs.exists():
                organization_id = str(orgs.first().id)
            else:
                return validation_error_response(errors={"organization_id": "organization_id is required."})

        corrections = selectors.list_pending_corrections(organization_id=organization_id)
        return success_response(message="Pending corrections retrieved.", data=AttendanceCorrectionRequestSerializer(corrections, many=True).data)

    def post(self, request):
        serializer = AttendanceCorrectionSubmitSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        record = selectors.get_attendance_record(record_id=data["attendance_record_id"])
        requester = emp_selectors.get_employee(employee_id=data["requested_by_id"])
        if not record or not requester:
            return validation_error_response(message="Invalid attendance record or requester specified.")

        try:
            correction = services.submit_attendance_correction(
                record=record,
                requested_by=requester,
                requested_check_in=data.get("requested_check_in"),
                requested_check_out=data.get("requested_check_out"),
                requested_status=data.get("requested_status", "PRESENT"),
                reason=data["reason"],
            )
            return created_response(
                message="Attendance correction request submitted.",
                data=AttendanceCorrectionRequestSerializer(correction).data,
            )
        except Exception as e:
            return validation_error_response(errors={"correction": str(e)}, message="Correction submission failed.")


@extend_schema_view(
    post=extend_schema(
        tags=["Attendance Corrections"],
        summary="Process Attendance Correction Request (Approve/Reject)",
        request=AttendanceCorrectionProcessSerializer,
        responses={200: AttendanceCorrectionRequestSerializer},
    )
)
class AttendanceCorrectionProcessAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, pk):
        try:
            correction_request = selectors.AttendanceCorrectionRequest.objects.get(id=pk)
        except selectors.AttendanceCorrectionRequest.DoesNotExist:
            return not_found_response(message="Correction request not found.")

        serializer = AttendanceCorrectionProcessSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        user = request.user

        try:
            processed = services.process_attendance_correction(
                correction_request=correction_request,
                approve=data.get("approve", True),
                processed_by_id=str(user.id) if user else "",
            )
            return success_response(
                message="Attendance correction request processed.",
                data=AttendanceCorrectionRequestSerializer(processed).data,
            )
        except Exception as e:
            return validation_error_response(errors={"processing": str(e)}, message="Correction processing failed.")


@extend_schema_view(
    post=extend_schema(
        tags=["Attendance Lock Engine"],
        summary="Lock Attendance Records Up To Date",
        request=AttendanceLockUnlockSerializer,
        responses={200: OpenApiResponse(description="Count of records locked.")},
    )
)
class AttendanceLockAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        serializer = AttendanceLockUnlockSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        user = request.user

        try:
            count = services.lock_attendance_records(
                organization_id=data["organization_id"],
                lock_up_to_date=data["date"],
                actor_user_id=str(user.id) if user else "",
            )
            return success_response(
                message=f"Locked {count} attendance records.",
                data={"locked_count": count},
            )
        except Exception as e:
            return validation_error_response(errors={"lock": str(e)}, message="Lock execution failed.")


@extend_schema_view(
    post=extend_schema(
        tags=["Attendance Lock Engine"],
        summary="Unlock Attendance Records Up To Date",
        request=AttendanceLockUnlockSerializer,
        responses={200: OpenApiResponse(description="Count of records unlocked.")},
    )
)
class AttendanceUnlockAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        serializer = AttendanceLockUnlockSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        user = request.user

        try:
            count = services.unlock_attendance_records(
                organization_id=data["organization_id"],
                unlock_up_to_date=data["date"],
                actor_user_id=str(user.id) if user else "",
            )
            return success_response(
                message=f"Unlocked {count} attendance records.",
                data={"unlocked_count": count},
            )
        except Exception as e:
            return validation_error_response(errors={"unlock": str(e)}, message="Unlock execution failed.")


@extend_schema_view(
    post=extend_schema(
        tags=["Bulk Attendance"],
        summary="Bulk Import Attendance Records",
        request=BulkAttendanceImportSerializer,
        responses={200: OpenApiResponse(description="Bulk import result summary.")},
    )
)
class BulkAttendanceImportAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        serializer = BulkAttendanceImportSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        org = org_selectors.get_organization(organization_id=data["organization_id"])
        if not org:
            return validation_error_response(message="Invalid organization specified.")

        user = request.user
        try:
            res = services.bulk_import_attendance(
                organization=org,
                records_data=data["records"],
                actor_user_id=str(user.id) if user else "",
            )
            return success_response(
                message="Bulk attendance import completed.",
                data=res,
            )
        except Exception as e:
            return validation_error_response(errors={"bulk_import": str(e)}, message="Bulk import failed.")


# ── Foundation Views ─────────────────────────────────────────────────────────


@extend_schema_view(
    get=extend_schema(
        tags=["Attendance Policies"],
        summary="List Attendance Policies",
        responses={200: AttendancePolicySerializer(many=True)},
    ),
    post=extend_schema(
        tags=["Attendance Policies"],
        summary="Create Attendance Policy",
        request=AttendancePolicySerializer,
        responses={201: AttendancePolicySerializer},
    ),
)
class AttendancePolicyListCreateAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        organization_id = request.query_params.get("organization_id")
        if not organization_id:
            orgs = org_selectors.list_organizations()
            if orgs.exists():
                organization_id = str(orgs.first().id)
            else:
                return validation_error_response(errors={"organization_id": "organization_id query parameter is required."})

        policies = selectors.AttendancePolicy.objects.filter(organization_id=organization_id)
        return success_response(message="Attendance policies retrieved.", data=AttendancePolicySerializer(policies, many=True).data)

    def post(self, request):
        serializer = AttendancePolicySerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        org = org_selectors.get_organization(organization_id=data["organization"].id)
        if not org:
            return validation_error_response(message="Invalid organization specified.")

        try:
            policy = services.create_attendance_policy(
                organization=org,
                name=data["name"],
                code=data["code"],
                grace_time_minutes=data.get("grace_time_minutes", 15),
                late_threshold_minutes=data.get("late_threshold_minutes", 30),
                early_exit_threshold_minutes=data.get("early_exit_threshold_minutes", 30),
                minimum_working_hours=data.get("minimum_working_hours"),
                full_day_working_hours=data.get("full_day_working_hours"),
                maximum_working_hours=data.get("maximum_working_hours"),
                overtime_allowed=data.get("overtime_allowed", True),
                half_day_allowed=data.get("half_day_allowed", True),
                auto_checkout_enabled=data.get("auto_checkout_enabled", False),
                approval_required=data.get("approval_required", True),
                is_default=data.get("is_default", False),
            )
            return created_response(
                message="Attendance policy created successfully.",
                data=AttendancePolicySerializer(policy).data,
            )
        except Exception as e:
            return validation_error_response(errors={"policy": str(e)}, message="Policy creation failed.")


@extend_schema_view(
    get=extend_schema(
        tags=["Attendance Records"],
        summary="List Attendance Records",
        responses={200: AttendanceRecordSerializer(many=True)},
    ),
    post=extend_schema(
        tags=["Attendance Records"],
        summary="Create Attendance Record",
        request=AttendanceRecordCreateSerializer,
        responses={201: AttendanceRecordSerializer},
    ),
)
class AttendanceRecordListCreateAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        organization_id = request.query_params.get("organization_id")
        if not organization_id:
            orgs = org_selectors.list_organizations()
            if orgs.exists():
                organization_id = str(orgs.first().id)
            else:
                return validation_error_response(errors={"organization_id": "organization_id is required."})

        records = selectors.list_attendance_records(
            organization_id=organization_id,
            employee_id=request.query_params.get("employee_id"),
            status=request.query_params.get("status"),
        )
        page = request.query_params.get("page", 1)
        page_size = request.query_params.get("page_size", 20)
        return paginated_response(
            records,
            serializer_class=AttendanceRecordSerializer,
            message="Attendance records retrieved.",
            page=page,
            page_size=page_size,
        )

    def post(self, request):
        serializer = AttendanceRecordCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        employee = emp_selectors.get_employee(employee_id=data["employee_id"])
        if not employee:
            return validation_error_response(message="Invalid employee specified.")

        user = request.user
        try:
            record = services.create_attendance_record(
                employee=employee,
                attendance_date=data["attendance_date"],
                status=data.get("status", "PRESENT"),
                source=data.get("source", "WEB"),
                work_location=data.get("work_location", ""),
                working_hours=data.get("working_hours"),
                remarks=data.get("remarks", ""),
                actor_user_id=str(user.id) if user else "",
                actor_email=getattr(user, "email", ""),
            )
            return created_response(
                message="Attendance record logged successfully.",
                data=AttendanceRecordSerializer(record).data,
            )
        except Exception as e:
            return validation_error_response(errors={"attendance": str(e)}, message="Attendance record logging failed.")


@extend_schema_view(
    get=extend_schema(tags=["Attendance Summary"], summary="Retrieve Daily Attendance Summary", responses={200: OpenApiResponse()}),
)
class AttendanceSummaryAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        organization_id = request.query_params.get("organization_id")
        attendance_date = request.query_params.get("date")
        if not organization_id or not attendance_date:
            return validation_error_response(message="Both organization_id and date query parameters are required.")

        summary = selectors.get_attendance_summary(organization_id=organization_id, attendance_date=attendance_date)
        return success_response(message="Daily attendance summary retrieved.", data=summary)


# ── Attendance Analytics & Compliance Views ───────────────────────────────────


@extend_schema_view(
    get=extend_schema(
        tags=["Attendance Analytics"],
        summary="Employee-Level Attendance Analytics",
        description="Generate KPI analytics for a single employee across a date window.",
        responses={200: OpenApiResponse(description="Employee attendance KPI analytics payload.")},
    )
)
class EmployeeAnalyticsAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        target_id = request.query_params.get("target_id")
        start_date = request.query_params.get("start_date")
        end_date = request.query_params.get("end_date")
        if not all([target_id, start_date, end_date]):
            return validation_error_response(message="target_id, start_date, and end_date query parameters are required.")
        try:
            from datetime import date as dt_date
            analytics = selectors.get_employee_attendance_analytics(
                employee_id=target_id,
                start_date=dt_date.fromisoformat(start_date),
                end_date=dt_date.fromisoformat(end_date),
            )
            return success_response(message="Employee attendance analytics retrieved.", data=analytics)
        except Exception as e:
            return validation_error_response(errors={"analytics": str(e)}, message="Employee analytics query failed.")


@extend_schema_view(
    get=extend_schema(
        tags=["Attendance Analytics"],
        summary="Team-Level Attendance Analytics",
        description="Generate aggregated KPI analytics for a team across a date window.",
        responses={200: OpenApiResponse(description="Team attendance KPI analytics payload.")},
    )
)
class TeamAnalyticsAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        target_id = request.query_params.get("target_id")
        start_date = request.query_params.get("start_date")
        end_date = request.query_params.get("end_date")
        if not all([target_id, start_date, end_date]):
            return validation_error_response(message="target_id, start_date, and end_date query parameters are required.")
        try:
            from datetime import date as dt_date
            analytics = selectors.get_team_attendance_analytics(
                team_id=target_id,
                start_date=dt_date.fromisoformat(start_date),
                end_date=dt_date.fromisoformat(end_date),
            )
            return success_response(message="Team attendance analytics retrieved.", data=analytics)
        except Exception as e:
            return validation_error_response(errors={"analytics": str(e)}, message="Team analytics query failed.")


@extend_schema_view(
    get=extend_schema(
        tags=["Attendance Analytics"],
        summary="Department-Level Attendance Analytics",
        description="Generate aggregated KPI analytics for a department across a date window.",
        responses={200: OpenApiResponse(description="Department attendance KPI analytics payload.")},
    )
)
class DepartmentAnalyticsAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        target_id = request.query_params.get("target_id")
        start_date = request.query_params.get("start_date")
        end_date = request.query_params.get("end_date")
        if not all([target_id, start_date, end_date]):
            return validation_error_response(message="target_id, start_date, and end_date query parameters are required.")
        try:
            from datetime import date as dt_date
            analytics = selectors.get_department_attendance_analytics(
                department_id=target_id,
                start_date=dt_date.fromisoformat(start_date),
                end_date=dt_date.fromisoformat(end_date),
            )
            return success_response(message="Department attendance analytics retrieved.", data=analytics)
        except Exception as e:
            return validation_error_response(errors={"analytics": str(e)}, message="Department analytics query failed.")


@extend_schema_view(
    get=extend_schema(
        tags=["Attendance Analytics"],
        summary="Branch-Level Attendance Analytics",
        description="Generate aggregated KPI analytics for a branch across a date window.",
        responses={200: OpenApiResponse(description="Branch attendance KPI analytics payload.")},
    )
)
class BranchAnalyticsAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        target_id = request.query_params.get("target_id")
        start_date = request.query_params.get("start_date")
        end_date = request.query_params.get("end_date")
        if not all([target_id, start_date, end_date]):
            return validation_error_response(message="target_id, start_date, and end_date query parameters are required.")
        try:
            from datetime import date as dt_date
            analytics = selectors.get_branch_attendance_analytics(
                branch_id=target_id,
                start_date=dt_date.fromisoformat(start_date),
                end_date=dt_date.fromisoformat(end_date),
            )
            return success_response(message="Branch attendance analytics retrieved.", data=analytics)
        except Exception as e:
            return validation_error_response(errors={"analytics": str(e)}, message="Branch analytics query failed.")


@extend_schema_view(
    get=extend_schema(
        tags=["Attendance Analytics"],
        summary="Organization-Level Attendance Analytics",
        description="Generate aggregated KPI analytics for entire organization across a date window.",
        responses={200: OpenApiResponse(description="Organization attendance KPI analytics payload.")},
    )
)
class OrganizationAnalyticsAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        target_id = request.query_params.get("target_id")
        start_date = request.query_params.get("start_date")
        end_date = request.query_params.get("end_date")
        if not all([target_id, start_date, end_date]):
            return validation_error_response(message="target_id, start_date, and end_date query parameters are required.")
        try:
            from datetime import date as dt_date
            analytics = selectors.get_organization_attendance_analytics(
                organization_id=target_id,
                start_date=dt_date.fromisoformat(start_date),
                end_date=dt_date.fromisoformat(end_date),
            )
            return success_response(message="Organization attendance analytics retrieved.", data=analytics)
        except Exception as e:
            return validation_error_response(errors={"analytics": str(e)}, message="Organization analytics query failed.")


@extend_schema_view(
    get=extend_schema(
        tags=["Attendance Compliance"],
        summary="Compliance Violations Report",
        description="Detect and aggregate compliance violations (late, early exit, overtime, excessive hours) for an organization.",
        responses={200: OpenApiResponse(description="Compliance violations report payload.")},
    )
)
class ComplianceViolationsAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        organization_id = request.query_params.get("organization_id")
        start_date = request.query_params.get("start_date")
        end_date = request.query_params.get("end_date")
        if not all([organization_id, start_date, end_date]):
            return validation_error_response(message="organization_id, start_date, and end_date query parameters are required.")
        try:
            from datetime import date as dt_date
            violations = selectors.get_compliance_violations(
                organization_id=organization_id,
                start_date=dt_date.fromisoformat(start_date),
                end_date=dt_date.fromisoformat(end_date),
            )
            return success_response(message="Compliance violations report retrieved.", data=violations)
        except Exception as e:
            return validation_error_response(errors={"compliance": str(e)}, message="Compliance query failed.")


@extend_schema_view(
    get=extend_schema(
        tags=["Attendance Dashboard"],
        summary="Executive Dashboard Analytics",
        description="Generate optimized executive dashboard analytics payload with today snapshot, monthly/weekly KPIs, and daily trend.",
        responses={200: OpenApiResponse(description="Dashboard analytics payload.")},
    )
)
class DashboardAnalyticsAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        organization_id = request.query_params.get("organization_id")
        if not organization_id:
            return validation_error_response(message="organization_id query parameter is required.")
        user_role = request.query_params.get("user_role", "EXECUTIVE")
        target_id = request.query_params.get("target_id")
        try:
            dashboard = selectors.get_dashboard_analytics(
                organization_id=organization_id,
                user_role=user_role,
                target_id=target_id,
            )
            return success_response(message="Executive dashboard analytics retrieved.", data=dashboard)
        except Exception as e:
            return validation_error_response(errors={"dashboard": str(e)}, message="Dashboard query failed.")


@extend_schema_view(
    get=extend_schema(
        tags=["Attendance Export"],
        summary="Export Attendance Records CSV",
        description="Export attendance records as flat dictionaries for CSV download.",
        responses={200: OpenApiResponse(description="Attendance CSV export payload.")},
    )
)
class ExportCSVAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        organization_id = request.query_params.get("organization_id")
        start_date = request.query_params.get("start_date")
        end_date = request.query_params.get("end_date")
        if not all([organization_id, start_date, end_date]):
            return validation_error_response(message="organization_id, start_date, and end_date query parameters are required.")
        try:
            from datetime import date as dt_date
            rows = services.export_attendance_report_csv(
                organization_id=organization_id,
                start_date=dt_date.fromisoformat(start_date),
                end_date=dt_date.fromisoformat(end_date),
            )
            return success_response(message="Attendance CSV export generated.", data={"total_records": len(rows), "records": rows})
        except Exception as e:
            return validation_error_response(errors={"export": str(e)}, message="CSV export failed.")


@extend_schema_view(
    get=extend_schema(
        tags=["AI Foundation"],
        summary="AI Foundation Data Export",
        description="Generate structured AI foundation data vectors for workforce analytics and anomaly detection.",
        responses={200: OpenApiResponse(description="AI foundation data payload.")},
    )
)
class AIFoundationDataAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        organization_id = request.query_params.get("organization_id")
        start_date = request.query_params.get("start_date")
        end_date = request.query_params.get("end_date")
        if not all([organization_id, start_date, end_date]):
            return validation_error_response(message="organization_id, start_date, and end_date query parameters are required.")
        try:
            from datetime import date as dt_date
            ai_data = selectors.get_ai_analytics_foundation_data(
                organization_id=organization_id,
                start_date=dt_date.fromisoformat(start_date),
                end_date=dt_date.fromisoformat(end_date),
            )
            return success_response(message="AI foundation data retrieved.", data=ai_data)
        except Exception as e:
            return validation_error_response(errors={"ai_foundation": str(e)}, message="AI foundation data query failed.")

