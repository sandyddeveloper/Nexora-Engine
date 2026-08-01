"""Django admin interface registrations for organizations & shift rostering app."""

from django.contrib import admin

from .models import (
    Branch,
    Department,
    Designation,
    HolidayCalendar,
    Organization,
    OrganizationSetting,
    Shift,
    ShiftRoster,
    ShiftRosterAssignment,
    ShiftRotation,
    ShiftSwapRequest,
    Team,
)


@admin.register(Organization)
class OrganizationAdmin(admin.ModelAdmin):
    list_display = ("name", "code", "organization_type", "status", "created_at")
    list_filter = ("status", "organization_type", "country")
    search_fields = ("name", "code", "legal_name", "email")
    readonly_fields = ("code", "id", "created_at", "updated_at")


@admin.register(Branch)
class BranchAdmin(admin.ModelAdmin):
    list_display = ("name", "code", "organization", "city", "is_headquarters", "status")
    list_filter = ("status", "is_headquarters", "country")
    search_fields = ("name", "code", "city", "organization__name")


@admin.register(Department)
class DepartmentAdmin(admin.ModelAdmin):
    list_display = ("name", "code", "organization", "branch", "ordering", "status")
    list_filter = ("status", "organization")
    search_fields = ("name", "code", "organization__name", "branch__name")


@admin.register(Designation)
class DesignationAdmin(admin.ModelAdmin):
    list_display = ("name", "code", "organization", "grade", "level", "status")
    list_filter = ("status", "level", "grade")
    search_fields = ("name", "code", "organization__name")


@admin.register(Team)
class TeamAdmin(admin.ModelAdmin):
    list_display = ("name", "code", "organization", "branch", "department", "status")
    list_filter = ("status", "organization")
    search_fields = ("name", "code", "department__name")


@admin.register(Shift)
class ShiftAdmin(admin.ModelAdmin):
    list_display = ("name", "code", "organization", "shift_type", "start_time", "end_time", "status")
    list_filter = ("status", "shift_type", "is_night_shift", "flexible_hours")
    search_fields = ("name", "code", "organization__name")


@admin.register(ShiftRoster)
class ShiftRosterAdmin(admin.ModelAdmin):
    list_display = ("name", "code", "organization", "period_type", "start_date", "end_date", "status", "version")
    list_filter = ("status", "period_type", "organization")
    search_fields = ("name", "code")


@admin.register(ShiftRosterAssignment)
class ShiftRosterAssignmentAdmin(admin.ModelAdmin):
    list_display = ("roster", "employee", "shift", "date", "is_override")
    list_filter = ("is_override", "date")
    search_fields = ("employee__employee_id", "employee__first_name", "shift__code")


@admin.register(ShiftRotation)
class ShiftRotationAdmin(admin.ModelAdmin):
    list_display = ("name", "code", "organization", "rotation_type", "cycle_days")
    list_filter = ("rotation_type", "organization")


@admin.register(ShiftSwapRequest)
class ShiftSwapRequestAdmin(admin.ModelAdmin):
    list_display = ("requester", "target_employee", "requester_date", "target_date", "status")
    list_filter = ("status",)


@admin.register(HolidayCalendar)
class HolidayCalendarAdmin(admin.ModelAdmin):
    list_display = ("name", "organization", "branch", "holiday_date", "holiday_type", "status")
    list_filter = ("status", "holiday_type", "is_recurring")
