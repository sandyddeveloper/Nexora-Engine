"""Domain choice enums for the Payroll Foundation Engine."""

from django.db import models
from django.utils.translation import gettext_lazy as _


class ComponentType(models.TextChoices):
    EARNING = "EARNING", _("Earning Component")
    DEDUCTION = "DEDUCTION", _("Deduction Component")
    STATUTORY = "STATUTORY", _("Statutory Component")
    REIMBURSEMENT = "REIMBURSEMENT", _("Reimbursement Component")


class CalculationType(models.TextChoices):
    FIXED = "FIXED", _("Fixed Amount")
    PERCENTAGE_OF_BASIC = "PERCENTAGE_OF_BASIC", _("Percentage of Basic Salary")
    PERCENTAGE_OF_CTC = "PERCENTAGE_OF_CTC", _("Percentage of Cost to Company (CTC)")
    PERCENTAGE_OF_GROSS = "PERCENTAGE_OF_GROSS", _("Percentage of Gross Salary")
    FORMULA = "FORMULA", _("Custom Formula Expression")


class PayFrequency(models.TextChoices):
    MONTHLY = "MONTHLY", _("Monthly Cycle")
    BIWEEKLY = "BIWEEKLY", _("Biweekly Cycle (Every 2 Weeks)")
    WEEKLY = "WEEKLY", _("Weekly Cycle")
    FORTNIGHTLY = "FORTNIGHTLY", _("Fortnightly Cycle (Semi-Monthly)")
    CUSTOM = "CUSTOM", _("Custom Cycle Schedule")


class TaxRegime(models.TextChoices):
    OLD_REGIME = "OLD_REGIME", _("Old Tax Regime (With Exemptions/Deductions)")
    NEW_REGIME = "NEW_REGIME", _("New Concessional Tax Regime")
    EXEMPTED = "EXEMPTED", _("Tax Exempted Category")


class PayrollStatus(models.TextChoices):
    DRAFT = "DRAFT", _("Draft Profile")
    ACTIVE = "ACTIVE", _("Active Payroll Employee")
    SUSPENDED = "SUSPENDED", _("Suspended from Payroll Processing")
    INACTIVE = "INACTIVE", _("Inactive Payroll Status")


class AdjustmentType(models.TextChoices):
    FIXED = "FIXED", _("Fixed Adjustment Amount")
    PERCENTAGE = "PERCENTAGE", _("Percentage Adjustment")


class PayrollRunStatus(models.TextChoices):
    DRAFT = "DRAFT", _("Draft Payroll Run")
    CALCULATED = "CALCULATED", _("Calculated Salaries")
    VALIDATED = "VALIDATED", _("Validated Calculation")
    APPROVED = "APPROVED", _("Approved by Authorized Personnel")
    FINALIZED = "FINALIZED", _("Finalized & Locked")
    LOCKED = "LOCKED", _("Period Locked")
    REOPENED = "REOPENED", _("Reopened for Corrections")
    ROLLED_BACK = "ROLLED_BACK", _("Rolled Back Run")


class PayrollItemStatus(models.TextChoices):
    PENDING = "PENDING", _("Pending Calculation")
    CALCULATED = "CALCULATED", _("Salary Calculated Successfully")
    ERROR = "ERROR", _("Calculation Error Encountered")
    APPROVED = "APPROVED", _("Salary Approved")
    PAID = "PAID", _("Salary Disbursed")


class PayrollApprovalLevel(models.TextChoices):
    LEVEL_1_FINANCE = "LEVEL_1_FINANCE", _("Level 1 - Finance Review")
    LEVEL_2_HR = "LEVEL_2_HR", _("Level 2 - HR Authorization")
    LEVEL_3_MANAGEMENT = "LEVEL_3_MANAGEMENT", _("Level 3 - Executive Management Signoff")


class PayslipType(models.TextChoices):
    MONTHLY = "MONTHLY", _("Standard Monthly Payslip")
    OFF_CYCLE = "OFF_CYCLE", _("Off-Cycle Salary Disbursement")
    CORRECTION = "CORRECTION", _("Correction / Adjustment Payslip")
    FINAL_SETTLEMENT = "FINAL_SETTLEMENT", _("Full & Final Settlement Payslip")


class PayslipStatus(models.TextChoices):
    GENERATED = "GENERATED", _("Generated Payslip")
    PUBLISHED = "PUBLISHED", _("Published to ESS Portal")
    REVOKED = "REVOKED", _("Revoked Payslip")
    ARCHIVED = "ARCHIVED", _("Archived Payslip")


class DistributionMethod(models.TextChoices):
    BANK_TRANSFER = "BANK_TRANSFER", _("Direct Bank Wire Transfer")
    CASH = "CASH", _("Cash Payment")
    CHEQUE = "CHEQUE", _("Bank Cheque Disbursement")
    WALLET = "WALLET", _("Digital Wallet Transfer")
    UPI = "UPI", _("Unified Payments Interface (UPI)")


class DistributionStatus(models.TextChoices):
    PENDING = "PENDING", _("Pending Disbursement")
    SCHEDULED = "SCHEDULED", _("Scheduled for Bank Batch")
    COMPLETED = "COMPLETED", _("Disbursement Completed Successfully")
    FAILED = "FAILED", _("Disbursement Transfer Failed")
    CANCELLED = "CANCELLED", _("Disbursement Cancelled")


class AdjustmentCategory(models.TextChoices):
    ARREARS = "ARREARS", _("Salary Arrears Addition")
    RECOVERY = "RECOVERY", _("Salary Recovery Deduction")
    SALARY_DIFFERENCE = "SALARY_DIFFERENCE", _("Salary Revision Difference")
    ATTENDANCE_CORRECTION = "ATTENDANCE_CORRECTION", _("Attendance Regularization Impact")
    LEAVE_ADJUSTMENT = "LEAVE_ADJUSTMENT", _("Unpaid Leave LOP Adjustment")
    MANUAL = "MANUAL", _("Manual Ad-Hoc Adjustment")


class ComplianceReportType(models.TextChoices):
    TAX_SUMMARY = "TAX_SUMMARY", _("Tax Deduction & Slab Summary Report")
    CONTRIBUTION_SUMMARY = "CONTRIBUTION_SUMMARY", _("Statutory Contribution Breakdown Report")
    PAYROLL_COMPLIANCE = "PAYROLL_COMPLIANCE", _("Payroll Run Statutory Compliance Check")
    ORG_COMPLIANCE = "ORG_COMPLIANCE", _("Organization Overall Statutory Audit")
    AUDIT_REPORT = "AUDIT_REPORT", _("Payroll Lock & Adjustment Audit Trail")


class ComplianceExceptionSeverity(models.TextChoices):
    INFO = "INFO", _("Informational Advisory")
    WARNING = "WARNING", _("Non-Blocking Advisory Warning")
    ERROR = "ERROR", _("Blocking Compliance Error")
    CRITICAL = "CRITICAL", _("Critical Statutory Violation")


class ComplianceStatus(models.TextChoices):
    COMPLIANT = "COMPLIANT", _("Fully Compliant")
    NON_COMPLIANT = "NON_COMPLIANT", _("Non-Compliant / Errors Found")
    FLAGGED = "FLAGGED", _("Flagged for HR Review")
    OVERRIDDEN = "OVERRIDDEN", _("Compliance Exception Overridden")


class StatutoryFilingType(models.TextChoices):
    MONTHLY_TAX_RETURN = "MONTHLY_TAX_RETURN", _("Monthly Tax Deduction Return")
    PF_ECR_FILING = "PF_ECR_FILING", _("Provident Fund Electronic Challan Return")
    ESI_RETURNS = "ESI_RETURNS", _("Employee State Insurance Return")
    ANNUAL_TAX_CERTIFICATE = "ANNUAL_TAX_CERTIFICATE", _("Annual Employee Tax Statement (Form 16/W2)")


class DashboardType(models.TextChoices):
    CEO = "CEO", _("CEO Executive Financial Dashboard")
    HR = "HR", _("HR Compensation & Headcount Dashboard")
    FINANCE = "FINANCE", _("Finance Tax & Disbursement Dashboard")
    PAYROLL = "PAYROLL", _("Payroll Run Operations Dashboard")
    ORGANIZATION = "ORGANIZATION", _("Organization-Wide Payroll Summary")
    BRANCH = "BRANCH", _("Branch Location Cost Dashboard")
    DEPARTMENT = "DEPARTMENT", _("Departmental Cost Center Dashboard")


class AnalyticsGranularity(models.TextChoices):
    DAILY = "DAILY", _("Daily Metrics")
    MONTHLY = "MONTHLY", _("Monthly Metrics")
    QUARTERLY = "QUARTERLY", _("Quarterly Metrics")
    YEARLY = "YEARLY", _("Yearly Metrics")




