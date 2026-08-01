"""Django admin registrations for the Leave Management Foundation Engine."""

from django.contrib import admin

from .models import (
    ApprovalDelegation,
    LeaveAccrualLog,
    LeaveAccrualRule,
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


@admin.register(LeaveType)
class LeaveTypeAdmin(admin.ModelAdmin):
    list_display = ["name", "code", "category", "organization", "is_paid", "is_active"]
    list_filter = ["category", "is_paid", "is_active", "organization"]
    search_fields = ["name", "code"]
    ordering = ["name"]


@admin.register(LeavePolicy)
class LeavePolicyAdmin(admin.ModelAdmin):
    list_display = ["name", "code", "leave_type", "organization", "max_leave_per_year", "is_default", "is_active"]
    list_filter = ["is_default", "is_active", "reset_period", "organization"]
    search_fields = ["name", "code"]
    ordering = ["name"]


@admin.register(LeaveConfiguration)
class LeaveConfigurationAdmin(admin.ModelAdmin):
    list_display = ["organization", "branch", "department", "designation", "default_policy"]
    list_filter = ["organization"]
    ordering = ["organization"]


@admin.register(LeaveBalance)
class LeaveBalanceAdmin(admin.ModelAdmin):
    list_display = ["employee", "leave_type", "available_balance", "used_balance", "is_active", "is_locked"]
    list_filter = ["is_active", "is_locked", "organization"]
    search_fields = ["employee__employee_id", "employee__first_name"]
    ordering = ["employee"]


@admin.register(LeaveBalanceHistory)
class LeaveBalanceHistoryAdmin(admin.ModelAdmin):
    list_display = ["employee", "leave_type", "adjustment_type", "delta", "new_available_balance", "created_at"]
    list_filter = ["adjustment_type"]
    ordering = ["-created_at"]


@admin.register(LeaveAccrualRule)
class LeaveAccrualRuleAdmin(admin.ModelAdmin):
    list_display = ["policy", "accrual_frequency", "accrual_method", "accrual_amount", "max_accrual_cap"]
    list_filter = ["accrual_frequency", "accrual_method"]


@admin.register(LeaveAccrualLog)
class LeaveAccrualLogAdmin(admin.ModelAdmin):
    list_display = ["employee", "leave_type", "accrual_date", "accrued_amount", "accrual_frequency", "status"]
    list_filter = ["accrual_frequency", "status"]
    ordering = ["-accrual_date"]


@admin.register(LeaveCarryForwardRecord)
class LeaveCarryForwardRecordAdmin(admin.ModelAdmin):
    list_display = ["employee", "leave_type", "from_year", "to_year", "carried_forward_amount", "lapsed_amount"]
    ordering = ["-created_at"]


@admin.register(LeaveEvent)
class LeaveEventAdmin(admin.ModelAdmin):
    list_display = ["event_type", "organization", "actor_user_id", "timestamp"]
    list_filter = ["event_type"]
    ordering = ["-timestamp"]


@admin.register(LeaveRequest)
class LeaveRequestAdmin(admin.ModelAdmin):
    list_display = ["employee", "leave_type", "start_date", "end_date", "total_days", "status", "approver"]
    list_filter = ["status", "is_half_day", "is_emergency", "organization"]
    search_fields = ["employee__employee_id", "employee__first_name", "reason"]
    ordering = ["-created_at"]


@admin.register(LeaveApprovalStep)
class LeaveApprovalStepAdmin(admin.ModelAdmin):
    list_display = ["leave_request", "level", "approver", "status", "decision_timestamp"]
    list_filter = ["level", "status"]
    ordering = ["created_at"]


@admin.register(LeaveRequestHistory)
class LeaveRequestHistoryAdmin(admin.ModelAdmin):
    list_display = ["leave_request", "action", "modification_type", "actor_email", "created_at"]
    list_filter = ["action"]
    ordering = ["-created_at"]


@admin.register(ApprovalDelegation)
class ApprovalDelegationAdmin(admin.ModelAdmin):
    list_display = ["organization", "delegator", "delegatee", "start_date", "end_date", "is_active"]
    list_filter = ["is_active", "organization"]
    ordering = ["-start_date"]

