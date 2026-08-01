"""Text choices enums for the Leave Management Foundation Engine."""

from django.db import models
from django.utils.translation import gettext_lazy as _


class LeaveCategory(models.TextChoices):
    ANNUAL = "ANNUAL", _("Annual Leave")
    CASUAL = "CASUAL", _("Casual Leave")
    SICK = "SICK", _("Sick Leave")
    EARNED = "EARNED", _("Earned Leave")
    COMPENSATORY_OFF = "COMPENSATORY_OFF", _("Compensatory Off")
    MATERNITY = "MATERNITY", _("Maternity Leave")
    PATERNITY = "PATERNITY", _("Paternity Leave")
    MARRIAGE = "MARRIAGE", _("Marriage Leave")
    BEREAVEMENT = "BEREAVEMENT", _("Bereavement Leave")
    OPTIONAL_HOLIDAY = "OPTIONAL_HOLIDAY", _("Optional Holiday")
    UNPAID = "UNPAID", _("Unpaid Leave / Loss of Pay")
    WORK_FROM_HOME = "WORK_FROM_HOME", _("Work From Home Placeholder")
    CUSTOM = "CUSTOM", _("Custom Leave Category")


class AccrualFrequency(models.TextChoices):
    MONTHLY = "MONTHLY", _("Monthly Accrual")
    QUARTERLY = "QUARTERLY", _("Quarterly Accrual")
    YEARLY = "YEARLY", _("Yearly Accrual")
    ANNIVERSARY = "ANNIVERSARY", _("Anniversary Date Accrual")
    MANUAL = "MANUAL", _("Manual Ad-Hoc Accrual")


class AccrualMethod(models.TextChoices):
    FRONT_LOADED = "FRONT_LOADED", _("Front Loaded at Beginning of Period")
    PRO_RATA = "PRO_RATA", _("Pro-Rata Earned Over Time")


class ResetPeriod(models.TextChoices):
    CALENDAR_YEAR = "CALENDAR_YEAR", _("Calendar Year (Jan 1 - Dec 31)")
    FINANCIAL_YEAR = "FINANCIAL_YEAR", _("Financial Year (Apr 1 - Mar 31)")
    ANNIVERSARY = "ANNIVERSARY", _("Employee Joining Anniversary")


class BalanceAdjustmentType(models.TextChoices):
    CREDIT = "CREDIT", _("Credit Adjustment")
    DEBIT = "DEBIT", _("Debit Adjustment")
    ACCRUAL = "ACCRUAL", _("Periodic Accrual Credit")
    EXPIRE = "EXPIRE", _("Lapsed / Expired Balance")
    CARRY_FORWARD = "CARRY_FORWARD", _("Carry Forward Transfer")
    MANUAL_CORRECTION = "MANUAL_CORRECTION", _("Administrative Manual Correction")
    INITIALIZATION = "INITIALIZATION", _("Initial Opening Balance Setup")


class LeaveRequestStatus(models.TextChoices):
    DRAFT = "DRAFT", _("Draft Request")
    SUBMITTED = "SUBMITTED", _("Submitted for Approval")
    PENDING = "PENDING", _("Pending Approver Decision")
    APPROVED = "APPROVED", _("Approved Leave")
    REJECTED = "REJECTED", _("Rejected Leave")
    CANCELLED = "CANCELLED", _("Cancelled Leave")
    WITHDRAWN = "WITHDRAWN", _("Withdrawn by Employee")
    EXPIRED = "EXPIRED", _("Workflow Expired")
    RETURNED_FOR_CORRECTION = "RETURNED_FOR_CORRECTION", _("Returned to Employee for Revision")


class HalfDayPeriod(models.TextChoices):
    FIRST_HALF = "FIRST_HALF", _("First Half of Working Day")
    SECOND_HALF = "SECOND_HALF", _("Second Half of Working Day")


class ApprovalLevel(models.TextChoices):
    LEVEL_1_MANAGER = "LEVEL_1_MANAGER", _("Level 1 Reporting Manager")
    LEVEL_2_HR = "LEVEL_2_HR", _("Level 2 HR Business Partner")
    LEVEL_3_ADMIN = "LEVEL_3_ADMIN", _("Level 3 Organization Executive/Admin")


class ModificationType(models.TextChoices):
    DATE_CHANGE = "DATE_CHANGE", _("Leave Date Range Modified")
    LEAVE_TYPE_CHANGE = "LEAVE_TYPE_CHANGE", _("Leave Category Modified")
    REASON_CHANGE = "REASON_CHANGE", _("Reason / Metadata Modified")

