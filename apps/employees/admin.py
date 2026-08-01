"""Admin interface registration for the employees app."""

from django.contrib import admin

from .models import (
    Certification,
    Education,
    EmergencyContact,
    Employee,
    EmployeeIdentifier,
    EmployeeProfile,
    EmploymentHistory,
    Experience,
    ManagerAssignment,
    Skill,
    WorkforceAssignment,
)


@admin.register(Employee)
class EmployeeAdmin(admin.ModelAdmin):
    list_display = ("employee_id", "first_name", "last_name", "official_email", "organization", "department", "designation", "employment_status")
    list_filter = ("organization", "branch", "department", "employment_status", "employment_type")
    search_fields = ("employee_id", "first_name", "last_name", "official_email")
    readonly_fields = ("employee_id", "created_at", "updated_at")


@admin.register(ManagerAssignment)
class ManagerAssignmentAdmin(admin.ModelAdmin):
    list_display = ("employee", "manager", "manager_type", "is_active", "effective_date")
    list_filter = ("manager_type", "is_active")


@admin.register(WorkforceAssignment)
class WorkforceAssignmentAdmin(admin.ModelAdmin):
    list_display = ("employee", "assignment_type", "effective_date", "end_date", "is_temporary")
    list_filter = ("assignment_type", "is_temporary")


@admin.register(EmployeeProfile)
class EmployeeProfileAdmin(admin.ModelAdmin):
    list_display = ("employee", "personal_email", "personal_phone", "city", "country")
    search_fields = ("employee__employee_id", "personal_email", "pan_number", "aadhaar_number")


@admin.register(EmergencyContact)
class EmergencyContactAdmin(admin.ModelAdmin):
    list_display = ("name", "relationship", "phone", "employee", "priority")
    list_filter = ("priority", "relationship")


@admin.register(Education)
class EducationAdmin(admin.ModelAdmin):
    list_display = ("degree", "institution", "employee", "start_date", "end_date", "grade")


@admin.register(Experience)
class ExperienceAdmin(admin.ModelAdmin):
    list_display = ("company", "designation", "employee", "start_date", "end_date", "is_current_company")


@admin.register(Skill)
class SkillAdmin(admin.ModelAdmin):
    list_display = ("name", "category", "level", "years_of_experience", "employee")
    list_filter = ("level", "category")


@admin.register(Certification)
class CertificationAdmin(admin.ModelAdmin):
    list_display = ("title", "provider", "employee", "issue_date", "expiry_date")


@admin.register(EmployeeIdentifier)
class EmployeeIdentifierAdmin(admin.ModelAdmin):
    list_display = ("identifier_type", "identifier_number", "issuing_country", "employee")


@admin.register(EmploymentHistory)
class EmploymentHistoryAdmin(admin.ModelAdmin):
    list_display = ("employee", "change_type", "effective_date", "created_at")
    list_filter = ("change_type", "effective_date")
