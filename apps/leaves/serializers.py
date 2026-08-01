"""DRF Serializers for the Leave Management Foundation Engine."""

from rest_framework import serializers

from .models import (
    ApprovalDelegation,
    LeaveAccrualLog,
    LeaveApprovalStep,
    LeaveBalance,
    LeaveBalanceHistory,
    LeaveCarryForwardRecord,
    LeaveConfiguration,
    LeaveEvent,
    LeavePolicy,
    LeaveRequest,
    LeaveRequestHistory,
    LeaveType,
)


class LeaveTypeSerializer(serializers.ModelSerializer):
    organization_name = serializers.CharField(source="organization.name", read_only=True)

    class Meta:
        model = LeaveType
        fields = [
            "id",
            "organization",
            "organization_name",
            "name",
            "code",
            "category",
            "description",
            "is_paid",
            "is_encashable",
            "is_wfh_placeholder",
            "is_compensatory_off",
            "requires_attachment",
            "gender_suitability",
            "is_active",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "created_at", "updated_at"]


class LeavePolicySerializer(serializers.ModelSerializer):
    organization_name = serializers.CharField(source="organization.name", read_only=True)
    leave_type_name = serializers.CharField(source="leave_type.name", read_only=True)

    class Meta:
        model = LeavePolicy
        fields = [
            "id",
            "organization",
            "organization_name",
            "leave_type",
            "leave_type_name",
            "name",
            "code",
            "max_leave_per_year",
            "min_leave_per_request",
            "max_leave_per_request",
            "half_day_allowed",
            "hourly_leave_allowed",
            "negative_balance_allowed",
            "max_negative_balance",
            "carry_forward_allowed",
            "max_carry_forward_days",
            "carry_forward_percentage",
            "carry_forward_expiry_days",
            "notice_period_days",
            "max_consecutive_days",
            "min_gap_between_leaves_days",
            "attachment_required_threshold_days",
            "reset_period",
            "is_default",
            "is_active",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "created_at", "updated_at"]


class LeaveConfigurationSerializer(serializers.ModelSerializer):
    default_policy_name = serializers.CharField(source="default_policy.name", read_only=True)

    class Meta:
        model = LeaveConfiguration
        fields = [
            "id",
            "organization",
            "branch",
            "department",
            "designation",
            "default_policy",
            "default_policy_name",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "created_at", "updated_at"]


class LeaveBalanceSerializer(serializers.ModelSerializer):
    employee_name = serializers.CharField(source="employee.display_name", read_only=True)
    employee_code = serializers.CharField(source="employee.employee_id", read_only=True)
    leave_type_name = serializers.CharField(source="leave_type.name", read_only=True)
    leave_type_code = serializers.CharField(source="leave_type.code", read_only=True)

    class Meta:
        model = LeaveBalance
        fields = [
            "id",
            "employee",
            "employee_name",
            "employee_code",
            "organization",
            "leave_type",
            "leave_type_name",
            "leave_type_code",
            "policy",
            "opening_balance",
            "allocated_accrued",
            "used_balance",
            "pending_balance",
            "reserved_balance",
            "expired_balance",
            "carry_forward_balance",
            "available_balance",
            "last_accrual_date",
            "is_active",
            "is_locked",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "available_balance", "created_at", "updated_at"]


class LeaveBalanceHistorySerializer(serializers.ModelSerializer):
    leave_type_code = serializers.CharField(source="leave_type.code", read_only=True)

    class Meta:
        model = LeaveBalanceHistory
        fields = [
            "id",
            "leave_balance",
            "employee",
            "organization",
            "leave_type",
            "leave_type_code",
            "adjustment_type",
            "delta",
            "previous_available_balance",
            "new_available_balance",
            "reason",
            "actor_user_id",
            "actor_email",
            "created_at",
        ]
        read_only_fields = ["id", "created_at"]


class LeaveBalanceAdjustmentSerializer(serializers.Serializer):
    leave_balance_id = serializers.UUIDField()
    adjustment_type = serializers.ChoiceField(choices=["CREDIT", "DEBIT", "ACCRUAL", "EXPIRE", "CARRY_FORWARD", "MANUAL_CORRECTION"])
    delta = serializers.DecimalField(max_digits=5, decimal_places=2)
    reason = serializers.CharField()


class LeaveAccrualRunSerializer(serializers.Serializer):
    organization_id = serializers.UUIDField()
    accrual_frequency = serializers.ChoiceField(choices=["MONTHLY", "QUARTERLY", "YEARLY", "ANNIVERSARY"], default="MONTHLY")
    accrual_date = serializers.DateField(required=False, allow_null=True)


class LeaveEligibilityCheckSerializer(serializers.Serializer):
    employee_id = serializers.UUIDField()
    leave_type_id = serializers.UUIDField()
    requested_days = serializers.DecimalField(max_digits=4, decimal_places=2, default=1.00)


class LeaveCarryForwardRunSerializer(serializers.Serializer):
    organization_id = serializers.UUIDField()
    from_year = serializers.IntegerField()
    to_year = serializers.IntegerField()


class LeaveWorkingDaysCheckSerializer(serializers.Serializer):
    organization_id = serializers.UUIDField()
    start_date = serializers.DateField()
    end_date = serializers.DateField()
    employee_id = serializers.UUIDField(required=False, allow_null=True)


class LeaveEventSerializer(serializers.ModelSerializer):
    class Meta:
        model = LeaveEvent
        fields = ["id", "leave_balance", "event_type", "actor_user_id", "actor_email", "ip_address", "request_id", "previous_state", "new_state", "reason", "timestamp"]
        read_only_fields = ["id", "timestamp"]


# ── Leave Request & Approval Workflow Serializers ────────────────────────────


class LeaveApprovalStepSerializer(serializers.ModelSerializer):
    approver_name = serializers.CharField(source="approver.display_name", read_only=True)

    class Meta:
        model = LeaveApprovalStep
        fields = ["id", "level", "approver", "approver_name", "status", "comments", "decision_timestamp"]
        read_only_fields = ["id", "decision_timestamp"]


class LeaveRequestHistorySerializer(serializers.ModelSerializer):
    class Meta:
        model = LeaveRequestHistory
        fields = ["id", "action", "modification_type", "previous_state", "new_state", "comments", "actor_user_id", "actor_email", "created_at"]
        read_only_fields = ["id", "created_at"]


class LeaveRequestSerializer(serializers.ModelSerializer):
    employee_name = serializers.CharField(source="employee.display_name", read_only=True)
    employee_code = serializers.CharField(source="employee.employee_id", read_only=True)
    leave_type_name = serializers.CharField(source="leave_type.name", read_only=True)
    approver_name = serializers.CharField(source="approver.display_name", read_only=True)
    approval_steps = LeaveApprovalStepSerializer(many=True, read_only=True)
    history = LeaveRequestHistorySerializer(many=True, read_only=True)

    class Meta:
        model = LeaveRequest
        fields = [
            "id",
            "employee",
            "employee_name",
            "employee_code",
            "organization",
            "leave_type",
            "leave_type_name",
            "policy",
            "leave_balance",
            "start_date",
            "end_date",
            "total_days",
            "is_half_day",
            "half_day_period",
            "reason",
            "attachment_url",
            "status",
            "current_approval_level",
            "max_approval_levels",
            "approver",
            "approver_name",
            "rejection_reason",
            "cancellation_reason",
            "is_emergency",
            "is_past_leave",
            "approval_steps",
            "history",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "total_days", "status", "current_approval_level", "created_at", "updated_at"]


class ApprovalDelegationSerializer(serializers.ModelSerializer):
    delegator_name = serializers.CharField(source="delegator.display_name", read_only=True)
    delegatee_name = serializers.CharField(source="delegatee.display_name", read_only=True)

    class Meta:
        model = ApprovalDelegation
        fields = ["id", "organization", "delegator", "delegator_name", "delegatee", "delegatee_name", "start_date", "end_date", "is_active", "reason", "created_at"]
        read_only_fields = ["id", "created_at"]


class LeaveApplySerializer(serializers.Serializer):
    employee_id = serializers.UUIDField()
    leave_type_id = serializers.UUIDField()
    start_date = serializers.DateField()
    end_date = serializers.DateField()
    reason = serializers.CharField()
    is_half_day = serializers.BooleanField(default=False)
    half_day_period = serializers.ChoiceField(choices=["FIRST_HALF", "SECOND_HALF"], required=False, allow_null=True)
    attachment_url = serializers.URLField(required=False, allow_blank=True)
    is_emergency = serializers.BooleanField(default=False)
    is_draft = serializers.BooleanField(default=False)


class LeaveApprovalDecisionSerializer(serializers.Serializer):
    approver_employee_id = serializers.UUIDField()
    comments = serializers.CharField(required=False, allow_blank=True)
    rejection_reason = serializers.CharField(required=False, allow_blank=True)


class LeaveCancellationSerializer(serializers.Serializer):
    cancellation_reason = serializers.CharField()


class LeaveModificationSerializer(serializers.Serializer):
    new_start_date = serializers.DateField(required=False, allow_null=True)
    new_end_date = serializers.DateField(required=False, allow_null=True)
    new_reason = serializers.CharField(required=False, allow_blank=True)


class ApprovalDelegationCreateSerializer(serializers.Serializer):
    organization_id = serializers.UUIDField()
    delegator_id = serializers.UUIDField()
    delegatee_id = serializers.UUIDField()
    start_date = serializers.DateField()
    end_date = serializers.DateField()
    reason = serializers.CharField(required=False, allow_blank=True)


class LeaveCalendarRequestSerializer(serializers.Serializer):
    organization_id = serializers.UUIDField()
    start_date = serializers.DateField()
    end_date = serializers.DateField()
    scope = serializers.ChoiceField(choices=["EMPLOYEE", "TEAM", "DEPARTMENT", "BRANCH", "ORGANIZATION"], default="ORGANIZATION")
    target_id = serializers.UUIDField(required=False, allow_null=True)


# ── Leave Analytics & Compliance Engine Serializers ──────────────────────────


class LeaveAnalyticsRequestSerializer(serializers.Serializer):
    """Request serializer for scoped leave analytics queries."""
    organization_id = serializers.UUIDField()
    start_date = serializers.DateField()
    end_date = serializers.DateField()


class EmployeeLeaveAnalyticsRequestSerializer(serializers.Serializer):
    """Request serializer for employee-level leave analytics."""
    employee_id = serializers.UUIDField()


class LeaveKPIRequestSerializer(serializers.Serializer):
    """Request serializer for organization leave KPI calculation."""
    organization_id = serializers.UUIDField()
    start_date = serializers.DateField()
    end_date = serializers.DateField()


class LeaveComplianceRequestSerializer(serializers.Serializer):
    """Request serializer for compliance audit."""
    organization_id = serializers.UUIDField()
    start_date = serializers.DateField()
    end_date = serializers.DateField()


class ExecutiveDashboardRequestSerializer(serializers.Serializer):
    """Request serializer for executive leave dashboard."""
    organization_id = serializers.UUIDField()


class ManagerDashboardRequestSerializer(serializers.Serializer):
    """Request serializer for manager leave dashboard."""
    manager_id = serializers.UUIDField()


class LeaveForecastRequestSerializer(serializers.Serializer):
    """Request serializer for leave forecast data."""
    organization_id = serializers.UUIDField()


class LeaveExportRequestSerializer(serializers.Serializer):
    """Request serializer for leave CSV export generation."""
    organization_id = serializers.UUIDField()
    report_type = serializers.ChoiceField(choices=["UTILIZATION", "COMPLIANCE", "SUMMARY"], default="SUMMARY")
    start_date = serializers.DateField()
    end_date = serializers.DateField()


