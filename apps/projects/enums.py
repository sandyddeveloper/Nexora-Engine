"""Choice enums for Enterprise Project Management Foundation Engine."""

from django.db import models
from django.utils.translation import gettext_lazy as _


class ProjectType(models.TextChoices):
    INTERNAL = "INTERNAL", _("Internal Operational Project")
    CLIENT = "CLIENT", _("Client External Project")
    DEPARTMENT = "DEPARTMENT", _("Departmental Initiative")
    RESEARCH = "RESEARCH", _("Research & Development")
    MAINTENANCE = "MAINTENANCE", _("System & Operations Maintenance")
    AUTOMATION = "AUTOMATION", _("Process Automation Project")
    AI = "AI", _("Artificial Intelligence Initiative")
    CUSTOM = "CUSTOM", _("Custom Project Type")


class ProjectCategory(models.TextChoices):
    SOFTWARE = "SOFTWARE", _("Software Engineering")
    MARKETING = "MARKETING", _("Marketing Campaign")
    HR = "HR", _("Human Resources Initiative")
    FINANCE = "FINANCE", _("Finance & Accounting")
    OPERATIONS = "OPERATIONS", _("Business Operations")
    INFRASTRUCTURE = "INFRASTRUCTURE", _("IT Infrastructure")
    RESEARCH = "RESEARCH", _("Research & Innovation")
    CLIENT_DELIVERY = "CLIENT_DELIVERY", _("Client Delivery Services")
    CUSTOM = "CUSTOM", _("Custom Category")


class ProjectStatus(models.TextChoices):
    DRAFT = "DRAFT", _("Draft Proposal")
    PLANNING = "PLANNING", _("Project Planning")
    APPROVED = "APPROVED", _("Approved for Execution")
    IN_PROGRESS = "IN_PROGRESS", _("In Progress")
    ON_HOLD = "ON_HOLD", _("On Hold / Paused")
    COMPLETED = "COMPLETED", _("Completed Successfully")
    CANCELLED = "CANCELLED", _("Cancelled")
    ARCHIVED = "ARCHIVED", _("Archived")


class ProjectPriority(models.TextChoices):
    LOW = "LOW", _("Low Priority")
    MEDIUM = "MEDIUM", _("Medium Priority")
    HIGH = "HIGH", _("High Priority")
    URGENT = "URGENT", _("Urgent Priority")
    CRITICAL = "CRITICAL", _("Critical Enterprise Priority")


class ProjectRiskLevel(models.TextChoices):
    LOW = "LOW", _("Low Risk")
    MEDIUM = "MEDIUM", _("Medium Risk")
    HIGH = "HIGH", _("High Risk")
    CRITICAL = "CRITICAL", _("Critical Risk")


class ProjectVisibility(models.TextChoices):
    PRIVATE = "PRIVATE", _("Private to Assigned Members")
    INTERNAL = "INTERNAL", _("Visible to Department")
    ORGANIZATION = "ORGANIZATION", _("Visible to Entire Organization")
    CLIENT = "CLIENT", _("Visible to Client Stakeholders")


class ProjectMemberRole(models.TextChoices):
    OWNER = "OWNER", _("Project Executive Owner")
    MANAGER = "MANAGER", _("Project Manager")
    TEAM_LEAD = "TEAM_LEAD", _("Technical / Team Lead")
    DEVELOPER = "DEVELOPER", _("Software Engineer / Developer")
    QA = "QA", _("Quality Assurance Specialist")
    DESIGNER = "DESIGNER", _("UI/UX Designer")
    BUSINESS_ANALYST = "BUSINESS_ANALYST", _("Business Analyst")
    OBSERVER = "OBSERVER", _("Stakeholder / Observer")
    CUSTOM = "CUSTOM", _("Custom Project Role")


class TaskType(models.TextChoices):
    EPIC = "EPIC", _("Epic Parent Container")
    STORY = "STORY", _("User Story")
    TASK = "TASK", _("Standard Work Task")
    SUBTASK = "SUBTASK", _("Subtask Work Unit")
    BUG = "BUG", _("Defect / Software Bug")
    ISSUE = "ISSUE", _("Operational Issue")
    FEATURE = "FEATURE", _("Feature Request")
    SPIKE = "SPIKE", _("Technical Research Spike")
    RESEARCH = "RESEARCH", _("Research Initiative")
    IMPROVEMENT = "IMPROVEMENT", _("System Improvement")
    CUSTOM = "CUSTOM", _("Custom Task Type")


class TaskStatus(models.TextChoices):
    BACKLOG = "BACKLOG", _("Backlog")
    TODO = "TODO", _("To Do")
    IN_PROGRESS = "IN_PROGRESS", _("In Progress")
    IN_REVIEW = "IN_REVIEW", _("Under Peer Review")
    BLOCKED = "BLOCKED", _("Blocked by Dependency")
    DONE = "DONE", _("Completed / Done")
    CANCELLED = "CANCELLED", _("Cancelled")
    ARCHIVED = "ARCHIVED", _("Archived")


class TaskSeverity(models.TextChoices):
    TRIVIAL = "TRIVIAL", _("Trivial Impact")
    MINOR = "MINOR", _("Minor Impact")
    MAJOR = "MAJOR", _("Major Impact")
    CRITICAL = "CRITICAL", _("Critical Impact")
    BLOCKER = "BLOCKER", _("System Blocker")


class DependencyType(models.TextChoices):
    FINISH_TO_START = "FINISH_TO_START", _("Finish-to-Start (FS)")
    START_TO_START = "START_TO_START", _("Start-to-Start (SS)")
    FINISH_TO_FINISH = "FINISH_TO_FINISH", _("Finish-to-Finish (FF)")
    START_TO_FINISH = "START_TO_FINISH", _("Start-to-Finish (SF)")


class AssignmentRole(models.TextChoices):
    ASSIGNEE = "ASSIGNEE", _("Primary Assignee")
    REVIEWER = "REVIEWER", _("Peer Reviewer")
    APPROVER = "APPROVER", _("Final Approver")
    OBSERVER = "OBSERVER", _("Stakeholder Observer")


class SprintType(models.TextChoices):
    REGULAR = "REGULAR", _("Regular Scrum Sprint")
    ITERATION = "ITERATION", _("Development Iteration")
    RELEASE = "RELEASE", _("Release Stabilization Sprint")
    PLANNING = "PLANNING", _("PI / Sprint Planning")
    HARDENING = "HARDENING", _("Security / Hardening Sprint")
    CUSTOM = "CUSTOM", _("Custom Sprint")


class SprintStatus(models.TextChoices):
    DRAFT = "DRAFT", _("Draft / Unplanned")
    PLANNING = "PLANNING", _("In Planning")
    ACTIVE = "ACTIVE", _("Active / In Progress")
    COMPLETED = "COMPLETED", _("Completed")
    CANCELLED = "CANCELLED", _("Cancelled")


class BoardType(models.TextChoices):
    SCRUM = "SCRUM", _("Scrum Board")
    KANBAN = "KANBAN", _("Kanban Board")
    HYBRID = "HYBRID", _("Scrumban / Hybrid Board")


class EstimationScale(models.TextChoices):
    FIBONACCI = "FIBONACCI", _("Fibonacci Scale (1, 2, 3, 5, 8, 13, 21)")
    T_SHIRT = "T_SHIRT", _("T-Shirt Sizes (XS, S, M, L, XL)")
    HOURS = "HOURS", _("Direct Hourly Effort")
    CUSTOM = "CUSTOM", _("Custom Scale")


class TimeEntryType(models.TextChoices):
    MANUAL = "MANUAL", _("Manual Worklog Entry")
    TIMER = "TIMER", _("Live Start/Stop Timer")
    BULK_IMPORT = "BULK_IMPORT", _("Bulk Import Entry")


class BillableType(models.TextChoices):
    BILLABLE = "BILLABLE", _("Client Billable Hours")
    NON_BILLABLE = "NON_BILLABLE", _("Non-Billable Work")
    INTERNAL = "INTERNAL", _("Internal Project Hours")
    TRAINING = "TRAINING", _("Professional Development / Training")
    MEETING = "MEETING", _("Client / Internal Meeting")
    RESEARCH = "RESEARCH", _("R&D Research Hours")


class TimesheetPeriod(models.TextChoices):
    DAILY = "DAILY", _("Daily Timesheet")
    WEEKLY = "WEEKLY", _("Weekly Timesheet")
    BIWEEKLY = "BIWEEKLY", _("Biweekly Timesheet")
    MONTHLY = "MONTHLY", _("Monthly Timesheet")


class TimesheetStatus(models.TextChoices):
    DRAFT = "DRAFT", _("Draft")
    SUBMITTED = "SUBMITTED", _("Submitted for Approval")
    APPROVED = "APPROVED", _("Approved by Manager")
    REJECTED = "REJECTED", _("Rejected")
    LOCKED = "LOCKED", _("Locked for Payroll / Invoicing")


class OvertimeCategory(models.TextChoices):
    REGULAR_HOURS = "REGULAR_HOURS", _("Standard Work Hours")
    DAILY_OVERTIME = "DAILY_OVERTIME", _("Daily Overtime")
    WEEKLY_OVERTIME = "WEEKLY_OVERTIME", _("Weekly Overtime")
    WEEKEND_OVERTIME = "WEEKEND_OVERTIME", _("Weekend Overtime")
    HOLIDAY_OVERTIME = "HOLIDAY_OVERTIME", _("Public Holiday Overtime")


class AllocationType(models.TextChoices):
    PROJECT = "PROJECT", _("Project Allocation")
    TASK = "TASK", _("Task Allocation")
    TEAM = "TEAM", _("Team Level Reservation")
    BENCH = "BENCH", _("Bench Reservation")
    TRAINING = "TRAINING", _("Training Allocation")


class AllocationStatus(models.TextChoices):
    RESERVED = "RESERVED", _("Soft Reserved")
    ACTIVE = "ACTIVE", _("Active Hard Allocation")
    COMPLETED = "COMPLETED", _("Completed Allocation")
    CANCELLED = "CANCELLED", _("Cancelled Allocation")


class ResourceAvailabilityState(models.TextChoices):
    AVAILABLE = "AVAILABLE", _("Fully Available")
    BUSY = "BUSY", _("Fully Allocated / Busy")
    ON_LEAVE = "ON_LEAVE", _("On Approved Leave")
    HOLIDAY = "HOLIDAY", _("Public Holiday")
    TRAINING = "TRAINING", _("In Training")
    MEETING = "MEETING", _("In Meetings")
    RESERVED = "RESERVED", _("Soft Reserved")


class WorkloadStatus(models.TextChoices):
    UNDERUTILIZED = "UNDERUTILIZED", _("Underutilized (< 50% capacity)")
    OPTIMAL = "OPTIMAL", _("Optimal Utilization (50% - 100% capacity)")
    OVERALLOCATED = "OVERALLOCATED", _("Overallocated (> 100% capacity)")


class PortfolioType(models.TextChoices):
    STRATEGIC = "STRATEGIC", _("Strategic Initiative Portfolio")
    TECHNOLOGY = "TECHNOLOGY", _("Technology & IT Portfolio")
    CLIENT = "CLIENT", _("Client Delivery Portfolio")
    DEPARTMENT = "DEPARTMENT", _("Departmental Portfolio")
    BUSINESS_UNIT = "BUSINESS_UNIT", _("Business Unit Portfolio")
    REGIONAL = "REGIONAL", _("Regional Operations Portfolio")
    CUSTOM = "CUSTOM", _("Custom Portfolio")


class PortfolioStatus(models.TextChoices):
    PLANNING = "PLANNING", _("In Planning")
    ACTIVE = "ACTIVE", _("Active Portfolio")
    ON_HOLD = "ON_HOLD", _("On Hold")
    COMPLETED = "COMPLETED", _("Completed")
    ARCHIVED = "ARCHIVED", _("Archived")


class ProgramStatus(models.TextChoices):
    DRAFT = "DRAFT", _("Draft")
    ACTIVE = "ACTIVE", _("Active Program")
    IN_REVIEW = "IN_REVIEW", _("In Executive Review")
    COMPLETED = "COMPLETED", _("Completed")
    CANCELLED = "CANCELLED", _("Cancelled")


class HealthStatus(models.TextChoices):
    GREEN = "GREEN", _("On Track / Low Risk (Green)")
    AMBER = "AMBER", _("At Risk / Moderate Variance (Amber)")
    RED = "RED", _("Critical Risk / High Variance (Red)")


class RiskLevel(models.TextChoices):
    LOW = "LOW", _("Low Severity Risk")
    MEDIUM = "MEDIUM", _("Medium Severity Risk")
    HIGH = "HIGH", _("High Severity Risk")
    CRITICAL = "CRITICAL", _("Critical Enterprise Risk")


class RiskStatus(models.TextChoices):
    IDENTIFIED = "IDENTIFIED", _("Risk Identified")
    ASSESSING = "ASSESSING", _("Under Assessment")
    MITIGATING = "MITIGATING", _("Mitigation Plan Active")
    CLOSED = "CLOSED", _("Risk Closed / Resolved")
    ESCALATED = "ESCALATED", _("Escalated to Executive PMO")





