"""DRF Serializers for the employees app."""

from rest_framework import serializers

from .models import (
    Certification,
    Education,
    EmergencyContact,
    Employee,
    EmployeeAuditEvent,
    EmployeeIdentifier,
    EmployeeProfile,
    EmployeeResignation,
    EmploymentHistory,
    Experience,
    ManagerAssignment,
    Skill,
    WorkforceAssignment,
)


class EmployeeProfileSerializer(serializers.ModelSerializer):
    class Meta:
        model = EmployeeProfile
        fields = [
            "id",
            "personal_email",
            "personal_phone",
            "current_address",
            "permanent_address",
            "city",
            "state",
            "country",
            "postal_code",
            "languages",
            "bio",
            "linkedin_url",
            "github_url",
            "website_url",
            "passport_number",
            "driving_license",
            "pan_number",
            "aadhaar_number",
            "tax_number",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "created_at", "updated_at"]


class EmployeeSerializer(serializers.ModelSerializer):
    organization_name = serializers.CharField(source="organization.name", read_only=True)
    branch_name = serializers.CharField(source="branch.name", read_only=True)
    department_name = serializers.CharField(source="department.name", read_only=True)
    designation_name = serializers.CharField(source="designation.name", read_only=True)
    reporting_manager_name = serializers.CharField(source="reporting_manager.display_name", read_only=True, allow_null=True)

    class Meta:
        model = Employee
        fields = [
            "id",
            "employee_id",
            "organization",
            "organization_name",
            "branch",
            "branch_name",
            "department",
            "department_name",
            "designation",
            "designation_name",
            "team",
            "reporting_manager",
            "reporting_manager_name",
            "user",
            "shift",
            "first_name",
            "last_name",
            "display_name",
            "official_email",
            "official_phone",
            "employment_type",
            "employment_status",
            "date_of_joining",
            "probation_period_months",
            "confirmation_date",
            "work_location",
            "photo",
            "gender",
            "date_of_birth",
            "blood_group",
            "nationality",
            "marital_status",
            "status",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "employee_id", "created_at", "updated_at"]


class EmployeeDetailSerializer(EmployeeSerializer):
    profile = EmployeeProfileSerializer(read_only=True)

    class Meta(EmployeeSerializer.Meta):
        fields = EmployeeSerializer.Meta.fields + ["profile"]


class EmployeeCreateSerializer(serializers.Serializer):
    organization_id = serializers.UUIDField()
    branch_id = serializers.UUIDField()
    department_id = serializers.UUIDField()
    designation_id = serializers.UUIDField()
    team_id = serializers.UUIDField(required=False, allow_null=True)
    reporting_manager_id = serializers.UUIDField(required=False, allow_null=True)
    shift_id = serializers.UUIDField(required=False, allow_null=True)
    first_name = serializers.CharField(max_length=150)
    last_name = serializers.CharField(max_length=150)
    official_email = serializers.EmailField()
    official_phone = serializers.CharField(max_length=50, required=False, allow_blank=True)
    date_of_joining = serializers.DateField()
    employment_type = serializers.CharField(default="FULL_TIME")
    employment_status = serializers.CharField(default="PROBATION")
    probation_period_months = serializers.IntegerField(default=3)
    work_location = serializers.CharField(required=False, allow_blank=True)
    gender = serializers.CharField(required=False, allow_blank=True)
    date_of_birth = serializers.DateField(required=False, allow_null=True)
    blood_group = serializers.CharField(required=False, allow_blank=True)
    nationality = serializers.CharField(required=False, allow_blank=True)
    marital_status = serializers.CharField(required=False, allow_blank=True)
    personal_email = serializers.EmailField(required=False, allow_blank=True)
    personal_phone = serializers.CharField(required=False, allow_blank=True)
    current_address = serializers.CharField(required=False, allow_blank=True)
    permanent_address = serializers.CharField(required=False, allow_blank=True)
    city = serializers.CharField(required=False, allow_blank=True)
    state = serializers.CharField(required=False, allow_blank=True)
    country = serializers.CharField(required=False, allow_blank=True)
    postal_code = serializers.CharField(required=False, allow_blank=True)
    pan_number = serializers.CharField(required=False, allow_blank=True)
    aadhaar_number = serializers.CharField(required=False, allow_blank=True)
    passport_number = serializers.CharField(required=False, allow_blank=True)


class EmployeeTransitionStatusSerializer(serializers.Serializer):
    target_status = serializers.CharField(max_length=50)
    reason = serializers.CharField(required=False, allow_blank=True)


class EmployeeConfirmSerializer(serializers.Serializer):
    confirmation_date = serializers.DateField(required=False, allow_null=True)
    remarks = serializers.CharField(required=False, allow_blank=True)


class EmployeeResignationSerializer(serializers.ModelSerializer):
    class Meta:
        model = EmployeeResignation
        fields = [
            "id",
            "employee",
            "resignation_date",
            "notice_period_days",
            "requested_exit_date",
            "approved_exit_date",
            "status",
            "reason",
            "comments",
            "processed_by_id",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "employee", "status", "created_at", "updated_at"]


class EmployeeResignationSubmitSerializer(serializers.Serializer):
    resignation_date = serializers.DateField()
    notice_period_days = serializers.IntegerField(default=30)
    requested_exit_date = serializers.DateField(required=False, allow_null=True)
    reason = serializers.CharField(required=False, allow_blank=True)


class EmployeeResignationApproveSerializer(serializers.Serializer):
    approved_exit_date = serializers.DateField(required=False, allow_null=True)
    comments = serializers.CharField(required=False, allow_blank=True)


class EmployeeTransferSerializer(serializers.Serializer):
    new_branch_id = serializers.UUIDField()
    new_department_id = serializers.UUIDField()
    effective_date = serializers.DateField()
    remarks = serializers.CharField(required=False, allow_blank=True)


class EmployeePromoteSerializer(serializers.Serializer):
    new_designation_id = serializers.UUIDField()
    effective_date = serializers.DateField()
    remarks = serializers.CharField(required=False, allow_blank=True)


class ManagerAssignmentSerializer(serializers.ModelSerializer):
    manager_name = serializers.CharField(source="manager.display_name", read_only=True)
    employee_name = serializers.CharField(source="employee.display_name", read_only=True)

    class Meta:
        model = ManagerAssignment
        fields = ["id", "employee", "employee_name", "manager", "manager_name", "manager_type", "is_active", "effective_date", "end_date", "created_at", "updated_at"]
        read_only_fields = ["id", "created_at", "updated_at"]


class AssignManagerSerializer(serializers.Serializer):
    manager_id = serializers.UUIDField()
    manager_type = serializers.CharField(default="PRIMARY")
    effective_date = serializers.DateField(required=False, allow_null=True)
    reason = serializers.CharField(required=False, allow_blank=True)


class BulkAssignManagerSerializer(serializers.Serializer):
    employee_ids = serializers.ListField(child=serializers.UUIDField())
    manager_id = serializers.UUIDField()
    manager_type = serializers.CharField(default="PRIMARY")
    effective_date = serializers.DateField(required=False, allow_null=True)


class AssignShiftSerializer(serializers.Serializer):
    shift_id = serializers.UUIDField()
    effective_date = serializers.DateField(required=False, allow_null=True)
    end_date = serializers.DateField(required=False, allow_null=True)
    is_temporary = serializers.BooleanField(default=False)
    reason = serializers.CharField(required=False, allow_blank=True)


class AssignWorkLocationSerializer(serializers.Serializer):
    work_location = serializers.CharField(max_length=255)
    location_type = serializers.CharField(default="OFFICE")
    effective_date = serializers.DateField(required=False, allow_null=True)
    reason = serializers.CharField(required=False, allow_blank=True)


class AssignTeamSerializer(serializers.Serializer):
    team_id = serializers.UUIDField()
    effective_date = serializers.DateField(required=False, allow_null=True)
    reason = serializers.CharField(required=False, allow_blank=True)


class WorkforceAssignmentSerializer(serializers.ModelSerializer):
    class Meta:
        model = WorkforceAssignment
        fields = [
            "id",
            "employee",
            "assignment_type",
            "effective_date",
            "end_date",
            "is_temporary",
            "previous_value",
            "new_value",
            "reason",
            "actor_user_id",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "created_at", "updated_at"]


class EmployeeAuditEventSerializer(serializers.ModelSerializer):
    class Meta:
        model = EmployeeAuditEvent
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


class EmergencyContactSerializer(serializers.ModelSerializer):
    class Meta:
        model = EmergencyContact
        fields = ["id", "employee", "name", "relationship", "phone", "email", "address", "priority", "created_at", "updated_at"]
        read_only_fields = ["id", "created_at", "updated_at"]


class EducationSerializer(serializers.ModelSerializer):
    class Meta:
        model = Education
        fields = ["id", "employee", "institution", "degree", "specialization", "start_date", "end_date", "grade", "created_at", "updated_at"]
        read_only_fields = ["id", "created_at", "updated_at"]


class ExperienceSerializer(serializers.ModelSerializer):
    class Meta:
        model = Experience
        fields = ["id", "employee", "company", "designation", "start_date", "end_date", "is_current_company", "description", "created_at", "updated_at"]
        read_only_fields = ["id", "created_at", "updated_at"]


class SkillSerializer(serializers.ModelSerializer):
    class Meta:
        model = Skill
        fields = ["id", "employee", "name", "category", "level", "years_of_experience", "created_at", "updated_at"]
        read_only_fields = ["id", "created_at", "updated_at"]


class CertificationSerializer(serializers.ModelSerializer):
    class Meta:
        model = Certification
        fields = ["id", "employee", "title", "provider", "issue_date", "expiry_date", "credential_id", "credential_url", "created_at", "updated_at"]
        read_only_fields = ["id", "created_at", "updated_at"]


class EmploymentHistorySerializer(serializers.ModelSerializer):
    class Meta:
        model = EmploymentHistory
        fields = ["id", "employee", "change_type", "effective_date", "previous_data", "new_data", "remarks", "created_at", "updated_at"]
        read_only_fields = ["id", "created_at", "updated_at"]
