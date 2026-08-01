"""Thin REST API views for the Payroll Foundation Engine."""

from drf_spectacular.utils import OpenApiResponse, extend_schema, extend_schema_view
from rest_framework.permissions import IsAuthenticated
from rest_framework.views import APIView

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
    AnalyticsSnapshotCreateSerializer,
    CompensationHistorySerializer,
    ComplianceExceptionSerializer,
    ComplianceOverrideRequestSerializer,
    ComplianceReportCreateSerializer,
    ComplianceReportSerializer,
    ComplianceRuleConfigSerializer,
    ComplianceValidateRequestSerializer,
    DashboardRefreshRequestSerializer,
    EmployeePayrollProfileSerializer,
    EmployeeSalaryStructureSerializer,
    GovernmentFilingCreateSerializer,
    GovernmentFilingRecordSerializer,
    PayrollActionReasonSerializer,
    PayrollAnalyticsSnapshotSerializer,
    PayrollApprovalRequestSerializer,
    PayrollApprovalSerializer,
    PayrollCycleSerializer,
    PayrollExecutiveDashboardSerializer,
    PayrollItemSerializer,
    PayrollPolicySerializer,
    PayrollRunCreateSerializer,
    PayrollRunSerializer,
    PayslipBulkGenerateSerializer,
    PayslipSerializer,
    RetroactiveAdjustmentCreateSerializer,
    RetroactiveAdjustmentSerializer,
    SalaryAssignmentSerializer,
    SalaryComponentSerializer,
    SalaryDistributionCreateSerializer,
    SalaryDistributionSerializer,
    SalaryRevisionHistorySerializer,
    SalaryTemplateSerializer,
    WorkforceCostIntelligenceSerializer,
)


@extend_schema_view(
    get=extend_schema(
        tags=["Payroll Components"],
        summary="List Salary Components",
        description="Retrieve all active salary component definitions for an organization.",
    ),
    post=extend_schema(
        tags=["Payroll Components"],
        summary="Create Salary Component",
        description="Define a new master salary component (Basic, HRA, PF, Allowance, etc.).",
    ),
)
class SalaryComponentListCreateAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        organization_id = request.query_params.get("organization_id")
        if not organization_id:
            return validation_error_response(message="organization_id query parameter is required.")

        components = selectors.list_salary_components(organization_id=organization_id)
        return success_response(
            message="Salary components retrieved.",
            data=SalaryComponentSerializer(components, many=True).data,
        )

    def post(self, request):
        serializer = SalaryComponentSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        org = get_organization(organization_id=data["organization"].id)
        if not org:
            return not_found_response(message="Organization not found.")

        try:
            component = services.create_salary_component(
                organization=org,
                name=data["name"],
                code=data["code"],
                component_type=data.get("component_type", "EARNING"),
                calculation_type=data.get("calculation_type", "FIXED"),
                default_amount_percentage=data.get("default_amount_percentage", 0.0),
                formula_expression=data.get("formula_expression", ""),
                is_taxable=data.get("is_taxable", True),
                is_recurring=data.get("is_recurring", True),
                is_statutory=data.get("is_statutory", False),
            )
            return created_response(
                message="Salary component created successfully.",
                data=SalaryComponentSerializer(component).data,
            )
        except Exception as e:
            return validation_error_response(errors={"component": str(e)}, message="Component creation failed.")


@extend_schema_view(
    get=extend_schema(
        tags=["Payroll Templates"],
        summary="List Salary Templates",
        description="Retrieve master salary templates for an organization.",
    ),
    post=extend_schema(
        tags=["Payroll Templates"],
        summary="Create Salary Template",
        description="Define a reusable master salary structure template.",
    ),
)
class SalaryTemplateListCreateAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        organization_id = request.query_params.get("organization_id")
        if not organization_id:
            return validation_error_response(message="organization_id query parameter is required.")

        templates = selectors.list_salary_templates(organization_id=organization_id)
        return success_response(
            message="Salary templates retrieved.",
            data=SalaryTemplateSerializer(templates, many=True).data,
        )

    def post(self, request):
        serializer = SalaryTemplateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        org = get_organization(organization_id=data["organization"].id)
        if not org:
            return not_found_response(message="Organization not found.")

        try:
            template = services.create_salary_template(
                organization=org,
                name=data["name"],
                code=data["code"],
                description=data.get("description", ""),
                currency=data.get("currency", "INR"),
            )
            return created_response(
                message="Salary template created successfully.",
                data=SalaryTemplateSerializer(template).data,
            )
        except Exception as e:
            return validation_error_response(errors={"template": str(e)}, message="Template creation failed.")


@extend_schema(
    tags=["Employee Payroll Profiles"],
    summary="Employee Payroll Profile Detail / Create",
    description="Retrieve or create employee master payroll profile.",
)
class EmployeePayrollProfileAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        employee_id = request.query_params.get("employee_id")
        if not employee_id:
            return validation_error_response(message="employee_id query parameter is required.")

        profile = selectors.get_employee_payroll_profile(employee_id=employee_id)
        if not profile:
            return not_found_response(message="Payroll profile not found for employee.")

        return success_response(
            message="Employee payroll profile retrieved.",
            data=EmployeePayrollProfileSerializer(profile).data,
        )

    def post(self, request):
        serializer = EmployeePayrollProfileSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        emp = get_employee(employee_id=data["employee"].id)
        if not emp:
            return not_found_response(message="Employee not found.")

        try:
            profile = services.create_employee_payroll_profile(
                employee=emp,
                status=data.get("status", "ACTIVE"),
                tax_regime=data.get("tax_regime", "NEW_REGIME"),
                pf_account_number=data.get("pf_account_number", ""),
                esi_account_number=data.get("esi_account_number", ""),
                pan_number=data.get("pan_number", ""),
                bank_account_number_placeholder=data.get("bank_account_number_placeholder", ""),
                bank_ifsc_placeholder=data.get("bank_ifsc_placeholder", ""),
                is_pf_eligible=data.get("is_pf_eligible", True),
                is_esi_eligible=data.get("is_esi_eligible", True),
            )
            return created_response(
                message="Employee payroll profile created successfully.",
                data=EmployeePayrollProfileSerializer(profile).data,
            )
        except Exception as e:
            return validation_error_response(errors={"profile": str(e)}, message="Profile creation failed.")


@extend_schema(
    tags=["Salary Assignments"],
    summary="Assign / Revise Salary Structure",
    description="Assign or revise salary structure for an employee, enforcing single active structure and versioning.",
)
class SalaryAssignAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        serializer = SalaryAssignmentSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        emp = get_employee(employee_id=data["employee_id"])
        if not emp:
            return not_found_response(message="Employee not found.")

        tmpl = None
        if data.get("salary_template_id"):
            tmpl = selectors.get_salary_template(template_id=data["salary_template_id"])

        try:
            structure = services.assign_employee_salary_structure(
                employee=emp,
                annual_ctc=data["annual_ctc"],
                effective_date=data["effective_date"],
                salary_template=tmpl,
                components_breakup=data.get("components_breakup", []),
                currency=data.get("currency", "INR"),
                revision_reason=data.get("revision_reason", "Salary Assignment"),
            )
            return created_response(
                message="Salary structure assigned successfully.",
                data=EmployeeSalaryStructureSerializer(structure).data,
            )
        except Exception as e:
            return validation_error_response(errors={"salary_assignment": str(e)}, message="Salary assignment failed.")


@extend_schema(
    tags=["Salary Assignments"],
    summary="Get Active Salary Structure",
    description="Retrieve the current active salary structure for an employee.",
)
class ActiveSalaryStructureAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        employee_id = request.query_params.get("employee_id")
        if not employee_id:
            return validation_error_response(message="employee_id query parameter is required.")

        structure = selectors.get_active_salary_structure(employee_id=employee_id)
        if not structure:
            return not_found_response(message="No active salary structure found for employee.")

        return success_response(
            message="Active salary structure retrieved.",
            data=EmployeeSalaryStructureSerializer(structure).data,
        )


@extend_schema(
    tags=["Salary Assignments"],
    summary="List Salary Revision History",
    description="Retrieve historical salary revisions for an employee.",
)
class SalaryRevisionHistoryAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        employee_id = request.query_params.get("employee_id")
        if not employee_id:
            return validation_error_response(message="employee_id query parameter is required.")

        revisions = selectors.list_salary_revision_history(employee_id=employee_id)
        return success_response(
            message="Salary revision history retrieved.",
            data=SalaryRevisionHistorySerializer(revisions, many=True).data,
        )


@extend_schema_view(
    get=extend_schema(
        tags=["Payroll Policies"],
        summary="List Payroll Policies",
        description="Retrieve payroll policies for an organization.",
    ),
    post=extend_schema(
        tags=["Payroll Policies"],
        summary="Create Payroll Policy",
        description="Create a new payroll cutoff and payday policy.",
    ),
)
class PayrollPolicyListCreateAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        organization_id = request.query_params.get("organization_id")
        if not organization_id:
            return validation_error_response(message="organization_id query parameter is required.")

        policies = selectors.list_payroll_policies(organization_id=organization_id)
        return success_response(
            message="Payroll policies retrieved.",
            data=PayrollPolicySerializer(policies, many=True).data,
        )

    def post(self, request):
        serializer = PayrollPolicySerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        org = get_organization(organization_id=data["organization"].id)
        if not org:
            return not_found_response(message="Organization not found.")

        try:
            policy = services.create_payroll_policy(
                organization=org,
                name=data["name"],
                code=data["code"],
                branch=data.get("branch"),
                department=data.get("department"),
                designation=data.get("designation"),
                cutoff_day_of_month=data.get("cutoff_day_of_month", 25),
                pay_day_of_month=data.get("pay_day_of_month", 30),
                is_default=data.get("is_default", False),
            )
            return created_response(
                message="Payroll policy created successfully.",
                data=PayrollPolicySerializer(policy).data,
            )
        except Exception as e:
            return validation_error_response(errors={"policy": str(e)}, message="Policy creation failed.")


@extend_schema_view(
    get=extend_schema(
        tags=["Payroll Cycles"],
        summary="List Payroll Cycles",
        description="Retrieve payroll execution cycles for an organization.",
    ),
    post=extend_schema(
        tags=["Payroll Cycles"],
        summary="Create Payroll Cycle",
        description="Schedule a new payroll execution cycle.",
    ),
)
class PayrollCycleListCreateAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        organization_id = request.query_params.get("organization_id")
        if not organization_id:
            return validation_error_response(message="organization_id query parameter is required.")

        cycles = selectors.list_payroll_cycles(organization_id=organization_id)
        return success_response(
            message="Payroll cycles retrieved.",
            data=PayrollCycleSerializer(cycles, many=True).data,
        )

    def post(self, request):
        serializer = PayrollCycleSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        org = get_organization(organization_id=data["organization"].id)
        if not org:
            return not_found_response(message="Organization not found.")

        try:
            cycle = services.create_payroll_cycle(
                organization=org,
                name=data["name"],
                start_date=data["start_date"],
                end_date=data["end_date"],
                cutoff_date=data["cutoff_date"],
                processing_date=data["processing_date"],
                payment_date=data["payment_date"],
                frequency=data.get("frequency", "MONTHLY"),
            )
            return created_response(
                message="Payroll cycle created successfully.",
                data=PayrollCycleSerializer(cycle).data,
            )
        except Exception as e:
            return validation_error_response(errors={"cycle": str(e)}, message="Cycle creation failed.")


# ── Payroll Processing & Run Engine Views ───────────────────────────────────


@extend_schema_view(
    get=extend_schema(
        tags=["Payroll Runs"],
        summary="List Payroll Runs",
        description="Retrieve all payroll processing runs for an organization.",
    ),
    post=extend_schema(
        tags=["Payroll Runs"],
        summary="Create Payroll Run",
        description="Initialize a new draft payroll run container for a cycle.",
    ),
)
class PayrollRunListCreateAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        organization_id = request.query_params.get("organization_id")
        if not organization_id:
            return validation_error_response(message="organization_id query parameter is required.")

        runs = selectors.list_payroll_runs(organization_id=organization_id)
        return success_response(
            message="Payroll runs retrieved.",
            data=PayrollRunSerializer(runs, many=True).data,
        )

    def post(self, request):
        serializer = PayrollRunCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        org = get_organization(organization_id=data["organization_id"])
        if not org:
            return not_found_response(message="Organization not found.")

        try:
            cycle = selectors.list_payroll_cycles(organization_id=org.id).get(id=data["payroll_cycle_id"])
            run = services.create_payroll_run(
                organization=org,
                payroll_cycle=cycle,
                name=data["name"],
            )
            return created_response(
                message="Payroll run created successfully.",
                data=PayrollRunSerializer(run).data,
            )
        except Exception as e:
            return validation_error_response(errors={"run": str(e)}, message="Payroll run creation failed.")


@extend_schema(
    tags=["Payroll Runs"],
    summary="Calculate Payroll Run",
    description="Execute salary calculations for all active employees in a payroll run.",
)
class PayrollRunCalculateAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, pk):
        run = selectors.get_payroll_run(run_id=pk)
        if not run:
            return not_found_response(message="Payroll run not found.")

        try:
            calculated_run = services.calculate_payroll_run(payroll_run=run)
            return success_response(
                message="Payroll calculation completed successfully.",
                data=PayrollRunSerializer(calculated_run).data,
            )
        except Exception as e:
            return validation_error_response(errors={"calculation": str(e)}, message="Payroll calculation failed.")


@extend_schema(
    tags=["Payroll Runs"],
    summary="Validate Payroll Run",
    description="Validate calculated payroll items for errors or negative net salaries.",
)
class PayrollRunValidateAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, pk):
        run = selectors.get_payroll_run(run_id=pk)
        if not run:
            return not_found_response(message="Payroll run not found.")

        try:
            validated_run = services.validate_payroll_run(payroll_run=run)
            return success_response(
                message="Payroll run validated successfully.",
                data=PayrollRunSerializer(validated_run).data,
            )
        except Exception as e:
            return validation_error_response(errors={"validation": str(e)}, message="Payroll validation failed.")


@extend_schema(
    tags=["Payroll Runs"],
    summary="Approve Payroll Run",
    description="Record an approval step (Finance/HR/Management) for a payroll run.",
)
class PayrollRunApproveAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, pk):
        run = selectors.get_payroll_run(run_id=pk)
        if not run:
            return not_found_response(message="Payroll run not found.")

        serializer = PayrollApprovalRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        approver = get_employee(employee_id=data["approver_id"])
        if not approver:
            return not_found_response(message="Approver employee record not found.")

        try:
            approved_run = services.approve_payroll_run(
                payroll_run=run,
                approver=approver,
                level=data["level"],
                comments=data.get("comments", ""),
            )
            return success_response(
                message="Payroll run approved successfully.",
                data=PayrollRunSerializer(approved_run).data,
            )
        except Exception as e:
            return validation_error_response(errors={"approval": str(e)}, message="Payroll approval failed.")


@extend_schema(
    tags=["Payroll Runs"],
    summary="Finalize Payroll Run",
    description="Finalize and lock a payroll run after all approvals are complete.",
)
class PayrollRunFinalizeAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, pk):
        run = selectors.get_payroll_run(run_id=pk)
        if not run:
            return not_found_response(message="Payroll run not found.")

        try:
            finalized_run = services.finalize_payroll_run(payroll_run=run)
            services.lock_payroll_period(
                organization=run.organization,
                payroll_run=finalized_run,
                locked_by_user_id=str(request.user.id),
            )
            return success_response(
                message="Payroll run finalized and locked successfully.",
                data=PayrollRunSerializer(finalized_run).data,
            )
        except Exception as e:
            return validation_error_response(errors={"finalization": str(e)}, message="Payroll finalization failed.")


@extend_schema(
    tags=["Payroll Runs"],
    summary="Reopen Payroll Run",
    description="Reopen a finalized or locked payroll run for authorized modifications.",
)
class PayrollRunReopenAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, pk):
        run = selectors.get_payroll_run(run_id=pk)
        if not run:
            return not_found_response(message="Payroll run not found.")

        serializer = PayrollActionReasonSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        try:
            reopened_run = services.reopen_payroll_run(
                payroll_run=run,
                reason=serializer.validated_data["reason"],
            )
            return success_response(
                message="Payroll run reopened successfully.",
                data=PayrollRunSerializer(reopened_run).data,
            )
        except Exception as e:
            return validation_error_response(errors={"reopen": str(e)}, message="Reopening payroll failed.")


@extend_schema(
    tags=["Payroll Runs"],
    summary="Rollback Payroll Run",
    description="Roll back a payroll run calculation and reset state.",
)
class PayrollRunRollbackAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, pk):
        run = selectors.get_payroll_run(run_id=pk)
        if not run:
            return not_found_response(message="Payroll run not found.")

        serializer = PayrollActionReasonSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        try:
            rolled_back_run = services.rollback_payroll_run(
                payroll_run=run,
                reason=serializer.validated_data["reason"],
            )
            return success_response(
                message="Payroll run rolled back successfully.",
                data=PayrollRunSerializer(rolled_back_run).data,
            )
        except Exception as e:
            return validation_error_response(errors={"rollback": str(e)}, message="Payroll rollback failed.")


@extend_schema(
    tags=["Payroll Items"],
    summary="List Payroll Items for a Run",
    description="Retrieve detailed per-employee calculated salary lines for a payroll run.",
)
class PayrollRunItemsAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, pk):
        run = selectors.get_payroll_run(run_id=pk)
        if not run:
            return not_found_response(message="Payroll run not found.")

        items = selectors.list_payroll_items(run_id=pk)
        summary = selectors.get_payroll_run_summary(run_id=pk)

        return success_response(
            message="Payroll run items retrieved.",
            data={
                "summary": summary,
                "items": PayrollItemSerializer(items, many=True).data,
            },
        )


# ── Payslip, Distribution & Compensation Views ───────────────────────────────


@extend_schema(
    tags=["Payslips"],
    summary="Bulk Generate Payslips",
    description="Bulk generate immutable payslips for all calculated items in a finalized payroll run.",
)
class PayslipGenerateBulkAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        serializer = PayslipBulkGenerateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        run_id = serializer.validated_data["payroll_run_id"]

        run = selectors.get_payroll_run(run_id=run_id)
        if not run:
            return not_found_response(message="Payroll run not found.")

        try:
            payslips = services.generate_payslips_for_run(payroll_run=run)
            return created_response(
                message=f"Generated {len(payslips)} payslips for payroll run.",
                data=PayslipSerializer(payslips, many=True).data,
            )
        except Exception as e:
            return validation_error_response(errors={"payslip_generation": str(e)}, message="Payslip generation failed.")


@extend_schema(
    tags=["Employee Self-Service Payslips"],
    summary="ESS Payslip History",
    description="Retrieve employee self-service payslip history for the authenticated employee.",
)
class ESSPayslipListAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        employee_id = request.query_params.get("employee_id")
        if not employee_id:
            return validation_error_response(message="employee_id query parameter is required.")

        payslips = selectors.list_employee_payslips(employee_id=employee_id)
        return success_response(
            message="Employee payslips retrieved.",
            data=PayslipSerializer(payslips, many=True).data,
        )


@extend_schema(
    tags=["Payslips"],
    summary="Payslip Detail",
    description="Retrieve detailed payslip with component breakup.",
)
class PayslipDetailAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, pk):
        payslip = selectors.get_payslip(payslip_id=pk)
        if not payslip:
            return not_found_response(message="Payslip not found.")

        return success_response(
            message="Payslip details retrieved.",
            data=PayslipSerializer(payslip).data,
        )


@extend_schema(
    tags=["Payslips"],
    summary="Download Payslip (CSV/Secure Token)",
    description="Download payslip export content using secure download token or ID.",
)
class PayslipDownloadAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, pk):
        payslip = selectors.get_payslip(payslip_id=pk)
        if not payslip:
            token = request.query_params.get("token")
            if token:
                payslip = selectors.get_payslip_by_token(download_token=token)

        if not payslip:
            return not_found_response(message="Payslip not found or invalid download token.")

        services.record_payslip_download_audit(payslip=payslip, user_id=str(request.user.id))
        csv_content = services.export_payslip_csv(payslip=payslip)

        from django.http import HttpResponse
        response = HttpResponse(csv_content, content_type="text/csv")
        response["Content-Disposition"] = f'attachment; filename="payslip_{payslip.payslip_number}.csv"'
        return response


@extend_schema_view(
    get=extend_schema(
        tags=["Salary Distributions"],
        summary="List Salary Distributions",
        description="Retrieve salary distribution records for a payroll run.",
    ),
    post=extend_schema(
        tags=["Salary Distributions"],
        summary="Schedule Salary Distribution",
        description="Schedule a salary disbursement batch for a finalized payroll run.",
    ),
)
class SalaryDistributionListCreateAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        payroll_run_id = request.query_params.get("payroll_run_id")
        if not payroll_run_id:
            return validation_error_response(message="payroll_run_id query parameter is required.")

        dists = selectors.list_salary_distributions(payroll_run_id=payroll_run_id)
        return success_response(
            message="Salary distributions retrieved.",
            data=SalaryDistributionSerializer(dists, many=True).data,
        )

    def post(self, request):
        serializer = SalaryDistributionCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        run = selectors.get_payroll_run(run_id=data["payroll_run_id"])
        if not run:
            return not_found_response(message="Payroll run not found.")

        try:
            dist = services.create_salary_distribution(
                payroll_run=run,
                method=data.get("method", "BANK_TRANSFER"),
                scheduled_date=data["scheduled_date"],
            )
            return created_response(
                message="Salary distribution scheduled successfully.",
                data=SalaryDistributionSerializer(dist).data,
            )
        except Exception as e:
            return validation_error_response(errors={"distribution": str(e)}, message="Salary distribution failed.")


@extend_schema_view(
    get=extend_schema(
        tags=["Retroactive Adjustments"],
        summary="List Retroactive Adjustments",
        description="Retrieve arrears and recovery adjustment entries for an employee.",
    ),
    post=extend_schema(
        tags=["Retroactive Adjustments"],
        summary="Create Retroactive Adjustment",
        description="Create an arrears or recovery adjustment record for an employee.",
    ),
)
class RetroactiveAdjustmentListCreateAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        employee_id = request.query_params.get("employee_id")
        if not employee_id:
            return validation_error_response(message="employee_id query parameter is required.")

        adjustments = selectors.list_retroactive_adjustments(employee_id=employee_id)
        return success_response(
            message="Retroactive adjustments retrieved.",
            data=RetroactiveAdjustmentSerializer(adjustments, many=True).data,
        )

    def post(self, request):
        serializer = RetroactiveAdjustmentCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        emp = get_employee(employee_id=data["employee_id"])
        if not emp:
            return not_found_response(message="Employee not found.")

        try:
            adj = services.create_retroactive_adjustment(
                employee=emp,
                category=data.get("category", "ARREARS"),
                amount=data["amount"],
                effective_date=data["effective_date"],
                reason=data["reason"],
            )
            return created_response(
                message="Retroactive adjustment created successfully.",
                data=RetroactiveAdjustmentSerializer(adj).data,
            )
        except Exception as e:
            return validation_error_response(errors={"adjustment": str(e)}, message="Retroactive adjustment failed.")


@extend_schema(
    tags=["Employee Compensation"],
    summary="Get Employee Compensation History",
    description="Retrieve historical total compensation snapshots for an employee.",
)
class CompensationHistoryAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        employee_id = request.query_params.get("employee_id")
        if not employee_id:
            return validation_error_response(message="employee_id query parameter is required.")

        history = selectors.get_employee_compensation_history(employee_id=employee_id)
        return success_response(
            message="Compensation history retrieved.",
            data=CompensationHistorySerializer(history, many=True).data,
        )


# ── Payroll Compliance & Statutory Views ────────────────────────────────────


@extend_schema_view(
    get=extend_schema(
        tags=["Payroll Compliance"],
        summary="List Compliance Rule Configs",
        description="Retrieve pluggable statutory compliance rule configurations for an organization.",
    ),
    post=extend_schema(
        tags=["Payroll Compliance"],
        summary="Create Compliance Rule Config",
        description="Define a new statutory compliance rule configuration.",
    ),
)
class ComplianceRuleConfigListCreateAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        organization_id = request.query_params.get("organization_id")
        if not organization_id:
            return validation_error_response(message="organization_id query parameter is required.")

        country_code = request.query_params.get("country_code", "")
        configs = selectors.list_compliance_rule_configs(organization_id=organization_id, country_code=country_code)
        return success_response(
            message="Compliance rule configurations retrieved.",
            data=ComplianceRuleConfigSerializer(configs, many=True).data,
        )

    def post(self, request):
        serializer = ComplianceRuleConfigSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        config = serializer.save()
        return created_response(
            message="Compliance rule configuration created successfully.",
            data=ComplianceRuleConfigSerializer(config).data,
        )


@extend_schema(
    tags=["Payroll Compliance"],
    summary="Validate Payroll Statutory Compliance",
    description="Execute statutory compliance checks (minimum wage, negative net salary, cap limits) for a calculated payroll run.",
)
class ComplianceValidateAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        serializer = ComplianceValidateRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        run_id = serializer.validated_data["payroll_run_id"]

        run = selectors.get_payroll_run(run_id=run_id)
        if not run:
            return not_found_response(message="Payroll run not found.")

        try:
            exceptions = services.validate_payroll_compliance(payroll_run=run)
            return success_response(
                message=f"Compliance validation executed. {len(exceptions)} exceptions recorded.",
                data={
                    "total_exceptions": len(exceptions),
                    "exceptions": ComplianceExceptionSerializer(exceptions, many=True).data,
                },
            )
        except Exception as e:
            return validation_error_response(errors={"compliance": str(e)}, message="Compliance validation failed.")


@extend_schema_view(
    get=extend_schema(
        tags=["Payroll Compliance"],
        summary="List Compliance Exceptions",
        description="Retrieve compliance exception flags for a payroll run.",
    ),
    post=extend_schema(
        tags=["Payroll Compliance"],
        summary="Override Compliance Exception",
        description="Perform authorized manual override for a statutory compliance exception.",
    ),
)
class ComplianceExceptionListOverrideAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        payroll_run_id = request.query_params.get("payroll_run_id")
        if not payroll_run_id:
            return validation_error_response(message="payroll_run_id query parameter is required.")

        exceptions = selectors.list_compliance_exceptions(payroll_run_id=payroll_run_id)
        return success_response(
            message="Compliance exceptions retrieved.",
            data=ComplianceExceptionSerializer(exceptions, many=True).data,
        )

    def post(self, request):
        serializer = ComplianceOverrideRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        try:
            ex = selectors.ComplianceException.objects.get(id=data["exception_id"])
            overridden = services.override_compliance_exception(
                exception=ex,
                user_id=str(request.user.id),
                override_reason=data["override_reason"],
            )
            return success_response(
                message="Compliance exception overridden successfully.",
                data=ComplianceExceptionSerializer(overridden).data,
            )
        except selectors.ComplianceException.DoesNotExist:
            return not_found_response(message="Compliance exception not found.")


@extend_schema_view(
    get=extend_schema(
        tags=["Payroll Compliance"],
        summary="List Compliance Reports",
        description="Retrieve statutory compliance reports for an organization.",
    ),
    post=extend_schema(
        tags=["Payroll Compliance"],
        summary="Generate Compliance Report",
        description="Generate statutory tax summary or contribution breakdown report.",
    ),
)
class ComplianceReportListGenerateAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        organization_id = request.query_params.get("organization_id")
        if not organization_id:
            return validation_error_response(message="organization_id query parameter is required.")

        reports = selectors.list_compliance_reports(organization_id=organization_id)
        return success_response(
            message="Compliance reports retrieved.",
            data=ComplianceReportSerializer(reports, many=True).data,
        )

    def post(self, request):
        serializer = ComplianceReportCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        org = get_organization(organization_id=data["organization_id"])
        if not org:
            return not_found_response(message="Organization not found.")

        try:
            report = services.generate_compliance_report(
                organization=org,
                report_type=data.get("report_type", "TAX_SUMMARY"),
                title=data["title"],
                start_date=data["start_date"],
                end_date=data["end_date"],
            )
            return created_response(
                message="Compliance report generated successfully.",
                data=ComplianceReportSerializer(report).data,
            )
        except Exception as e:
            return validation_error_response(errors={"report": str(e)}, message="Compliance report generation failed.")


@extend_schema_view(
    get=extend_schema(
        tags=["Government Filings"],
        summary="List Government Filing Records",
        description="Retrieve statutory government filing records for an organization.",
    ),
    post=extend_schema(
        tags=["Government Filings"],
        summary="Create Government Filing Record",
        description="Record a monthly tax return or PF/ESI filing batch.",
    ),
)
class GovernmentFilingListCreateAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        organization_id = request.query_params.get("organization_id")
        if not organization_id:
            return validation_error_response(message="organization_id query parameter is required.")

        filings = selectors.list_government_filings(organization_id=organization_id)
        return success_response(
            message="Government filing records retrieved.",
            data=GovernmentFilingRecordSerializer(filings, many=True).data,
        )

    def post(self, request):
        serializer = GovernmentFilingCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        org = get_organization(organization_id=data["organization_id"])
        if not org:
            return not_found_response(message="Organization not found.")

        try:
            filing = services.create_government_filing_record(
                organization=org,
                filing_type=data.get("filing_type", "MONTHLY_TAX_RETURN"),
                period_name=data["period_name"],
                total_tax_amount=data["total_tax_amount"],
                total_contribution_amount=data["total_contribution_amount"],
                filing_reference_number=data.get("filing_reference_number", ""),
            )
            return created_response(
                message="Government filing record created successfully.",
                data=GovernmentFilingRecordSerializer(filing).data,
            )
        except Exception as e:
            return validation_error_response(errors={"filing": str(e)}, message="Government filing creation failed.")


# ── Payroll Analytics, Executive Reporting & Cost Intelligence Views ─────────


@extend_schema_view(
    get=extend_schema(
        tags=["Payroll Analytics"],
        summary="Get Payroll Summary Analytics",
        description="Retrieve pre-aggregated or real-time payroll summary analytics across daily, monthly, quarterly, or yearly granularities.",
    ),
    post=extend_schema(
        tags=["Payroll Analytics"],
        summary="Generate Analytics Snapshot",
        description="Generate and persist periodic analytics snapshot metrics record.",
    ),
)
class PayrollAnalyticsSummaryAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        organization_id = request.query_params.get("organization_id")
        if not organization_id:
            return validation_error_response(message="organization_id query parameter is required.")

        period_name = request.query_params.get("period_name", "")
        granularity = request.query_params.get("granularity", "MONTHLY")

        analytics = selectors.get_payroll_summary_analytics(
            organization_id=organization_id,
            period_name=period_name,
            granularity=granularity,
        )
        return success_response(message="Payroll summary analytics retrieved.", data=analytics)

    def post(self, request):
        serializer = AnalyticsSnapshotCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        org = get_organization(organization_id=data["organization_id"])
        if not org:
            return not_found_response(message="Organization not found.")

        try:
            snapshot = services.generate_payroll_analytics_snapshot(
                organization=org,
                period_name=data["period_name"],
                granularity=data.get("granularity", "MONTHLY"),
            )
            return created_response(
                message="Payroll analytics snapshot generated successfully.",
                data=PayrollAnalyticsSnapshotSerializer(snapshot).data,
            )
        except Exception as e:
            return validation_error_response(errors={"snapshot": str(e)}, message="Analytics snapshot generation failed.")


@extend_schema(
    tags=["Payroll Analytics"],
    summary="Get Workforce Cost Intelligence",
    description="Retrieve departmental, branch, and designation workforce cost intelligence metrics.",
)
class WorkforceCostIntelligenceAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        organization_id = request.query_params.get("organization_id")
        if not organization_id:
            return validation_error_response(message="organization_id query parameter is required.")

        cost_data = selectors.get_workforce_cost_intelligence(organization_id=organization_id)
        return success_response(message="Workforce cost intelligence metrics retrieved.", data=cost_data)


@extend_schema(
    tags=["Payroll Analytics"],
    summary="Get Executive KPIs",
    description="Retrieve high-level key performance indicators (total cost, avg salary, median salary, completion rate) for executive dashboards.",
)
class ExecutiveKPIsAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        organization_id = request.query_params.get("organization_id")
        if not organization_id:
            return validation_error_response(message="organization_id query parameter is required.")

        kpis = selectors.get_executive_kpis(organization_id=organization_id)
        return success_response(message="Executive KPIs retrieved.", data=kpis)


@extend_schema_view(
    get=extend_schema(
        tags=["Executive Dashboards"],
        summary="Get Executive Dashboard Metrics",
        description="Retrieve pre-compiled executive dashboard payload tailored for CEO, HR, or Finance views.",
    ),
    post=extend_schema(
        tags=["Executive Dashboards"],
        summary="Refresh Executive Dashboard",
        description="Refresh and persist executive dashboard metrics payload.",
    ),
)
class ExecutiveDashboardAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        organization_id = request.query_params.get("organization_id")
        if not organization_id:
            return validation_error_response(message="organization_id query parameter is required.")

        dashboard_type = request.query_params.get("dashboard_type", "CEO")
        dash_data = selectors.get_executive_dashboard_metrics(
            organization_id=organization_id,
            dashboard_type=dashboard_type,
        )
        return success_response(message=f"Executive dashboard metrics ({dashboard_type}) retrieved.", data=dash_data)

    def post(self, request):
        serializer = DashboardRefreshRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        org = get_organization(organization_id=data["organization_id"])
        if not org:
            return not_found_response(message="Organization not found.")

        try:
            dash = services.generate_executive_dashboard(
                organization=org,
                dashboard_type=data.get("dashboard_type", "CEO"),
            )
            return success_response(
                message="Executive dashboard refreshed successfully.",
                data=PayrollExecutiveDashboardSerializer(dash).data,
            )
        except Exception as e:
            return validation_error_response(errors={"dashboard": str(e)}, message="Dashboard refresh failed.")


@extend_schema(
    tags=["Payroll Forecast Readiness"],
    summary="Get Forecast Dataset",
    description="Extract clean, noise-free historical payroll trend data prepared for future machine learning and budget forecasting modules.",
)
class PayrollForecastDataAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        organization_id = request.query_params.get("organization_id")
        if not organization_id:
            return validation_error_response(message="organization_id query parameter is required.")

        dataset = selectors.get_payroll_forecast_dataset(organization_id=organization_id)
        return success_response(message="Payroll forecast dataset retrieved.", data=dataset)


@extend_schema(
    tags=["Payroll Reporting"],
    summary="Export Payroll Register Report",
    description="Generate and download CSV payroll register export report.",
)
class PayrollExportReportAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        organization_id = request.query_params.get("organization_id")
        if not organization_id:
            return validation_error_response(message="organization_id query parameter is required.")

        org = get_organization(organization_id=organization_id)
        if not org:
            return not_found_response(message="Organization not found.")

        period_name = request.query_params.get("period_name", "")
        csv_data = services.export_payroll_register_report(organization=org, period_name=period_name)

        from django.http import HttpResponse
        response = HttpResponse(csv_data, content_type="text/csv")
        response["Content-Disposition"] = f'attachment; filename="payroll_register_{org.code}.csv"'
        return response




