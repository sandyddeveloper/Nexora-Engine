"""DRF Serializers for the Attendance Foundation & Processing Engine."""

from rest_framework import serializers

from .models import (
    AttendanceBreak,
    AttendanceConfiguration,
    AttendanceCorrectionRequest,
    AttendanceEvent,
    AttendancePolicy,
    AttendanceRecord,
    AttendanceSession,
)


class AttendancePolicySerializer(serializers.ModelSerializer):
    organization_name = serializers.CharField(source="organization.name", read_only=True)

    class Meta:
        model = AttendancePolicy
        fields = [
            "id",
            "organization",
            "organization_name",
            "name",
            "code",
            "grace_time_minutes",
            "late_threshold_minutes",
            "early_exit_threshold_minutes",
            "minimum_working_hours",
            "full_day_working_hours",
            "maximum_working_hours",
            "overtime_allowed",
            "half_day_allowed",
            "auto_checkout_enabled",
            "auto_checkout_time",
            "approval_required",
            "is_default",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "created_at", "updated_at"]


class AttendanceConfigurationSerializer(serializers.ModelSerializer):
    default_policy_name = serializers.CharField(source="default_policy.name", read_only=True)

    class Meta:
        model = AttendanceConfiguration
        fields = [
            "id",
            "organization",
            "branch",
            "department",
            "team",
            "default_policy",
            "default_policy_name",
            "allow_future_attendance",
            "allow_manual_entry",
            "allow_wfh_request",
            "lock_attendance_days",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "created_at", "updated_at"]


class AttendanceRecordSerializer(serializers.ModelSerializer):
    employee_name = serializers.CharField(source="employee.display_name", read_only=True)
    employee_code = serializers.CharField(source="employee.employee_id", read_only=True)
    organization_name = serializers.CharField(source="organization.name", read_only=True)
    branch_name = serializers.CharField(source="branch.name", read_only=True)
    department_name = serializers.CharField(source="department.name", read_only=True)

    class Meta:
        model = AttendanceRecord
        fields = [
            "id",
            "employee",
            "employee_name",
            "employee_code",
            "organization",
            "organization_name",
            "branch",
            "branch_name",
            "department",
            "department_name",
            "designation",
            "team",
            "shift",
            "policy",
            "attendance_date",
            "status",
            "source",
            "work_location",
            "approval_status",
            "working_hours",
            "break_hours",
            "overtime_hours",
            "is_night_shift",
            "is_locked",
            "remarks",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "created_at", "updated_at"]


class AttendanceRecordCreateSerializer(serializers.Serializer):
    employee_id = serializers.UUIDField()
    attendance_date = serializers.DateField()
    status = serializers.CharField(default="PRESENT")
    source = serializers.CharField(default="WEB")
    work_location = serializers.CharField(required=False, allow_blank=True)
    working_hours = serializers.DecimalField(max_digits=5, decimal_places=2, default=0.00)
    remarks = serializers.CharField(required=False, allow_blank=True)


class AttendanceRecordUpdateSerializer(serializers.Serializer):
    status = serializers.CharField(required=False)
    working_hours = serializers.DecimalField(max_digits=5, decimal_places=2, required=False)
    remarks = serializers.CharField(required=False, allow_blank=True)


class CheckInSerializer(serializers.Serializer):
    employee_id = serializers.UUIDField()
    check_in_time = serializers.DateTimeField(required=False, allow_null=True)
    source = serializers.CharField(default="WEB")
    work_location = serializers.CharField(required=False, allow_blank=True)
    remarks = serializers.CharField(required=False, allow_blank=True)


class CheckOutSerializer(serializers.Serializer):
    employee_id = serializers.UUIDField()
    check_out_time = serializers.DateTimeField(required=False, allow_null=True)
    force = serializers.BooleanField(default=False)
    remarks = serializers.CharField(required=False, allow_blank=True)


class BreakStartSerializer(serializers.Serializer):
    employee_id = serializers.UUIDField()
    break_type = serializers.CharField(default="LUNCH")
    start_time = serializers.DateTimeField(required=False, allow_null=True)
    is_paid = serializers.BooleanField(default=False)


class BreakEndSerializer(serializers.Serializer):
    employee_id = serializers.UUIDField()
    end_time = serializers.DateTimeField(required=False, allow_null=True)


class AttendanceBreakSerializer(serializers.ModelSerializer):
    class Meta:
        model = AttendanceBreak
        fields = ["id", "session", "break_type", "start_time", "end_time", "duration_minutes", "is_paid", "created_at", "updated_at"]
        read_only_fields = ["id", "created_at", "updated_at"]


class AttendanceSessionSerializer(serializers.ModelSerializer):
    breaks = AttendanceBreakSerializer(many=True, read_only=True)

    class Meta:
        model = AttendanceSession
        fields = ["id", "attendance_record", "check_in", "check_out", "session_duration_minutes", "is_auto_checked_out", "breaks", "created_at", "updated_at"]
        read_only_fields = ["id", "created_at", "updated_at"]


class AttendanceCorrectionRequestSerializer(serializers.ModelSerializer):
    requested_by_name = serializers.CharField(source="requested_by.display_name", read_only=True)

    class Meta:
        model = AttendanceCorrectionRequest
        fields = [
            "id",
            "attendance_record",
            "requested_by",
            "requested_by_name",
            "requested_check_in",
            "requested_check_out",
            "requested_status",
            "reason",
            "status",
            "processed_by_id",
            "processed_at",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "status", "processed_by_id", "processed_at", "created_at", "updated_at"]


class AttendanceCorrectionSubmitSerializer(serializers.Serializer):
    attendance_record_id = serializers.UUIDField()
    requested_by_id = serializers.UUIDField()
    requested_check_in = serializers.DateTimeField(required=False, allow_null=True)
    requested_check_out = serializers.DateTimeField(required=False, allow_null=True)
    requested_status = serializers.CharField(default="PRESENT")
    reason = serializers.CharField()


class AttendanceCorrectionProcessSerializer(serializers.Serializer):
    approve = serializers.BooleanField(default=True)


class AttendanceLockUnlockSerializer(serializers.Serializer):
    organization_id = serializers.UUIDField()
    date = serializers.DateField()


class BulkAttendanceImportSerializer(serializers.Serializer):
    organization_id = serializers.UUIDField()
    records = serializers.ListField(child=serializers.DictField())


class AttendanceEventSerializer(serializers.ModelSerializer):
    class Meta:
        model = AttendanceEvent
        fields = ["id", "attendance_record", "event_type", "actor_user_id", "actor_email", "ip_address", "request_id", "previous_state", "new_state", "reason", "timestamp"]
        read_only_fields = ["id", "timestamp"]


# ── Attendance Analytics & Compliance Serializers ─────────────────────────────


class AnalyticsRequestSerializer(serializers.Serializer):
    """Request serializer for hierarchical attendance analytics queries."""
    target_id = serializers.UUIDField(help_text="Target entity UUID (employee, team, department, branch, or organization).")
    start_date = serializers.DateField(help_text="Start date of analytics window.")
    end_date = serializers.DateField(help_text="End date of analytics window.")


class ComplianceRequestSerializer(serializers.Serializer):
    """Request serializer for compliance violation queries."""
    organization_id = serializers.UUIDField(help_text="Target organization UUID.")
    start_date = serializers.DateField(help_text="Start date of compliance window.")
    end_date = serializers.DateField(help_text="End date of compliance window.")


class DashboardRequestSerializer(serializers.Serializer):
    """Request serializer for executive dashboard analytics."""
    organization_id = serializers.UUIDField(help_text="Target organization UUID.")
    user_role = serializers.ChoiceField(
        choices=["EMPLOYEE", "MANAGER", "HR", "EXECUTIVE"],
        default="EXECUTIVE",
        help_text="Dashboard role scope.",
    )
    target_id = serializers.UUIDField(required=False, allow_null=True, help_text="Optional target entity UUID for scoped dashboards.")


class ExportCSVRequestSerializer(serializers.Serializer):
    """Request serializer for CSV attendance data export."""
    organization_id = serializers.UUIDField(help_text="Target organization UUID.")
    start_date = serializers.DateField(help_text="Export start date.")
    end_date = serializers.DateField(help_text="Export end date.")


class AIFoundationRequestSerializer(serializers.Serializer):
    """Request serializer for AI foundation data export."""
    organization_id = serializers.UUIDField(help_text="Target organization UUID.")
    start_date = serializers.DateField(help_text="AI data window start date.")
    end_date = serializers.DateField(help_text="AI data window end date.")

