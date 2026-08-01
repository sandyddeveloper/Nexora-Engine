"""DRF Serializers for the organizations app."""

from rest_framework import serializers

from .models import (
    Branch,
    Department,
    Designation,
    HolidayCalendar,
    Organization,
    OrganizationAuditEvent,
    OrganizationFeatureFlag,
    OrganizationLimit,
    OrganizationSetting,
    Shift,
    ShiftRoster,
    ShiftRosterAssignment,
    ShiftRotation,
    ShiftSwapRequest,
    Team,
)


class OrganizationSettingSerializer(serializers.ModelSerializer):
    class Meta:
        model = OrganizationSetting
        fields = [
            "id",
            "attendance_mode",
            "leave_approval_levels",
            "working_days_mask",
            "weekend_days_mask",
            "default_shift",
            "default_language",
            "default_currency",
            "default_timezone",
            "notification_config",
            "security_config",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "created_at", "updated_at"]


class OrganizationLimitSerializer(serializers.ModelSerializer):
    class Meta:
        model = OrganizationLimit
        fields = [
            "id",
            "max_branches",
            "max_departments",
            "max_teams",
            "max_shifts",
            "max_employees",
            "max_storage_gb",
            "max_api_calls_per_day",
            "max_projects",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "created_at", "updated_at"]


class OrganizationFeatureFlagSerializer(serializers.ModelSerializer):
    class Meta:
        model = OrganizationFeatureFlag
        fields = [
            "id",
            "attendance_enabled",
            "payroll_enabled",
            "crm_enabled",
            "projects_enabled",
            "documents_enabled",
            "ai_assistant_enabled",
            "automation_enabled",
            "api_access_enabled",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "created_at", "updated_at"]


class OrganizationAuditEventSerializer(serializers.ModelSerializer):
    class Meta:
        model = OrganizationAuditEvent
        fields = [
            "id",
            "event_type",
            "user_id",
            "user_email",
            "ip_address",
            "request_id",
            "previous_state",
            "new_state",
            "metadata",
            "timestamp",
        ]
        read_only_fields = ["id", "timestamp"]


class ShiftRosterSerializer(serializers.ModelSerializer):
    class Meta:
        model = ShiftRoster
        fields = [
            "id",
            "organization",
            "name",
            "code",
            "period_type",
            "start_date",
            "end_date",
            "status",
            "version",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "status", "version", "created_at", "updated_at"]


class ShiftRosterAssignmentSerializer(serializers.ModelSerializer):
    employee_name = serializers.CharField(source="employee.display_name", read_only=True)
    shift_name = serializers.CharField(source="shift.name", read_only=True)
    shift_code = serializers.CharField(source="shift.code", read_only=True)

    class Meta:
        model = ShiftRosterAssignment
        fields = [
            "id",
            "roster",
            "employee",
            "employee_name",
            "shift",
            "shift_name",
            "shift_code",
            "date",
            "is_override",
            "override_reason",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "created_at", "updated_at"]


class AssignRosterShiftSerializer(serializers.Serializer):
    employee_id = serializers.UUIDField()
    shift_id = serializers.UUIDField()
    date = serializers.DateField()
    is_override = serializers.BooleanField(default=False)
    override_reason = serializers.CharField(required=False, allow_blank=True)


class BulkAssignTeamRosterShiftSerializer(serializers.Serializer):
    team_id = serializers.UUIDField()
    shift_id = serializers.UUIDField()
    start_date = serializers.DateField()
    end_date = serializers.DateField()


class ShiftOverrideSerializer(serializers.Serializer):
    employee_id = serializers.UUIDField()
    shift_id = serializers.UUIDField()
    date = serializers.DateField()
    reason = serializers.CharField()


class ShiftSwapRequestSerializer(serializers.ModelSerializer):
    requester_name = serializers.CharField(source="requester.display_name", read_only=True)
    target_name = serializers.CharField(source="target_employee.display_name", read_only=True)

    class Meta:
        model = ShiftSwapRequest
        fields = [
            "id",
            "requester",
            "requester_name",
            "target_employee",
            "target_name",
            "requester_date",
            "target_date",
            "status",
            "reason",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "status", "created_at", "updated_at"]



class OrganizationSerializer(serializers.ModelSerializer):
    class Meta:
        model = Organization
        fields = [
            "id",
            "name",
            "legal_name",
            "code",
            "registration_number",
            "tax_number",
            "gst_number",
            "email",
            "phone",
            "website",
            "logo",
            "industry",
            "organization_type",
            "currency",
            "language",
            "timezone",
            "date_format",
            "time_format",
            "fiscal_year_start",
            "country",
            "state",
            "city",
            "address",
            "postal_code",
            "status",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "code", "created_at", "updated_at"]


class OrganizationDetailSerializer(OrganizationSerializer):
    setting = OrganizationSettingSerializer(read_only=True)
    limit = OrganizationLimitSerializer(read_only=True)
    feature_flag = OrganizationFeatureFlagSerializer(read_only=True)

    class Meta(OrganizationSerializer.Meta):
        fields = OrganizationSerializer.Meta.fields + ["setting", "limit", "feature_flag"]


class OrganizationOnboardSerializer(serializers.Serializer):
    name = serializers.CharField(max_length=255)
    legal_name = serializers.CharField(max_length=255, required=False, allow_blank=True)
    registration_number = serializers.CharField(max_length=100, required=False, allow_blank=True)
    tax_number = serializers.CharField(max_length=100, required=False, allow_blank=True)
    gst_number = serializers.CharField(max_length=100, required=False, allow_blank=True)
    email = serializers.EmailField(required=False, allow_blank=True)
    phone = serializers.CharField(max_length=50, required=False, allow_blank=True)
    website = serializers.URLField(max_length=255, required=False, allow_blank=True)
    industry = serializers.CharField(max_length=100, required=False, allow_blank=True)
    country = serializers.CharField(max_length=100, required=False, allow_blank=True)
    state = serializers.CharField(max_length=100, required=False, allow_blank=True)
    city = serializers.CharField(max_length=100, required=False, allow_blank=True)
    address = serializers.CharField(required=False, allow_blank=True)
    postal_code = serializers.CharField(max_length=20, required=False, allow_blank=True)


class OrganizationTransitionStatusSerializer(serializers.Serializer):
    target_status = serializers.CharField(max_length=50)
    reason = serializers.CharField(required=False, allow_blank=True)


class BranchSerializer(serializers.ModelSerializer):
    organization_id = serializers.UUIDField(source="organization.id", read_only=True)

    class Meta:
        model = Branch
        fields = [
            "id",
            "organization_id",
            "code",
            "name",
            "email",
            "phone",
            "address",
            "city",
            "state",
            "country",
            "postal_code",
            "latitude",
            "longitude",
            "timezone",
            "is_headquarters",
            "status",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "created_at", "updated_at"]


class BranchCreateSerializer(serializers.Serializer):
    code = serializers.CharField(max_length=50)
    name = serializers.CharField(max_length=255)
    email = serializers.EmailField(required=False, allow_blank=True)
    phone = serializers.CharField(max_length=50, required=False, allow_blank=True)
    address = serializers.CharField(required=False, allow_blank=True)
    city = serializers.CharField(max_length=100, required=False, allow_blank=True)
    state = serializers.CharField(max_length=100, required=False, allow_blank=True)
    country = serializers.CharField(max_length=100, required=False, allow_blank=True)
    postal_code = serializers.CharField(max_length=20, required=False, allow_blank=True)
    latitude = serializers.DecimalField(max_digits=10, decimal_places=7, required=False, allow_null=True)
    longitude = serializers.DecimalField(max_digits=10, decimal_places=7, required=False, allow_null=True)
    timezone = serializers.CharField(max_length=100, default="UTC")
    is_headquarters = serializers.BooleanField(default=False)
    status = serializers.CharField(default="ACTIVE")


class DepartmentSerializer(serializers.ModelSerializer):
    branch_name = serializers.CharField(source="branch.name", read_only=True)
    parent_department_name = serializers.CharField(source="parent_department.name", read_only=True, allow_null=True)

    class Meta:
        model = Department
        fields = [
            "id",
            "organization",
            "branch",
            "branch_name",
            "parent_department",
            "parent_department_name",
            "name",
            "code",
            "description",
            "ordering",
            "status",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "created_at", "updated_at"]


class DesignationSerializer(serializers.ModelSerializer):
    department_name = serializers.CharField(source="department.name", read_only=True, allow_null=True)

    class Meta:
        model = Designation
        fields = [
            "id",
            "organization",
            "department",
            "department_name",
            "name",
            "code",
            "grade",
            "level",
            "description",
            "status",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "created_at", "updated_at"]


class TeamSerializer(serializers.ModelSerializer):
    branch_name = serializers.CharField(source="branch.name", read_only=True)
    department_name = serializers.CharField(source="department.name", read_only=True)

    class Meta:
        model = Team
        fields = [
            "id",
            "organization",
            "branch",
            "branch_name",
            "department",
            "department_name",
            "name",
            "code",
            "description",
            "status",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "created_at", "updated_at"]


class ShiftSerializer(serializers.ModelSerializer):
    class Meta:
        model = Shift
        fields = [
            "id",
            "organization",
            "name",
            "code",
            "shift_type",
            "start_time",
            "end_time",
            "grace_time_minutes",
            "flexible_hours",
            "is_night_shift",
            "break_duration_minutes",
            "working_hours",
            "status",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "created_at", "updated_at"]


class HolidayCalendarSerializer(serializers.ModelSerializer):
    branch_name = serializers.CharField(source="branch.name", read_only=True, allow_null=True)

    class Meta:
        model = HolidayCalendar
        fields = [
            "id",
            "organization",
            "branch",
            "branch_name",
            "name",
            "holiday_date",
            "holiday_type",
            "description",
            "is_recurring",
            "status",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "created_at", "updated_at"]
