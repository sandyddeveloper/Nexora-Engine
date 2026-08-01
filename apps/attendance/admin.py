"""Admin interface registration for the attendance app."""

from django.contrib import admin

from .models import (
    AttendanceBreak,
    AttendanceConfiguration,
    AttendanceCorrectionRequest,
    AttendanceEvent,
    AttendancePolicy,
    AttendanceRecord,
    AttendanceSession,
)


@admin.register(AttendancePolicy)
class AttendancePolicyAdmin(admin.ModelAdmin):
    list_display = ("name", "code", "organization", "grace_time_minutes", "is_default")
    list_filter = ("organization", "is_default", "overtime_allowed")
    search_fields = ("name", "code")


@admin.register(AttendanceConfiguration)
class AttendanceConfigurationAdmin(admin.ModelAdmin):
    list_display = ("organization", "branch", "department", "team", "default_policy")


@admin.register(AttendanceRecord)
class AttendanceRecordAdmin(admin.ModelAdmin):
    list_display = ("employee", "organization", "attendance_date", "status", "working_hours", "approval_status", "is_locked")
    list_filter = ("organization", "status", "approval_status", "is_locked", "attendance_date")
    search_fields = ("employee__employee_id", "employee__first_name", "employee__last_name")


@admin.register(AttendanceSession)
class AttendanceSessionAdmin(admin.ModelAdmin):
    list_display = ("attendance_record", "check_in", "check_out", "session_duration_minutes")


@admin.register(AttendanceBreak)
class AttendanceBreakAdmin(admin.ModelAdmin):
    list_display = ("session", "break_type", "start_time", "end_time", "duration_minutes", "is_paid")
    list_filter = ("break_type", "is_paid")


@admin.register(AttendanceCorrectionRequest)
class AttendanceCorrectionRequestAdmin(admin.ModelAdmin):
    list_display = ("attendance_record", "requested_by", "requested_status", "status", "created_at")
    list_filter = ("status", "created_at")


@admin.register(AttendanceEvent)
class AttendanceEventAdmin(admin.ModelAdmin):
    list_display = ("attendance_record", "event_type", "actor_email", "timestamp")
    list_filter = ("event_type", "timestamp")
