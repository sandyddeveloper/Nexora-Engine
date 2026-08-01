"""Domain event definitions for the Leave Management Foundation Engine."""

import logging
from dataclasses import dataclass
from typing import Any, Dict

logger = logging.getLogger("nexora.leaves.events")


@dataclass
class BaseLeaveEvent:
    """Base dataclass for all leave domain events."""

    event_id: str
    event_type: str
    organization_id: str
    employee_id: str = ""
    leave_type_id: str = ""
    timestamp: str = ""
    metadata: Dict[str, Any] = None


@dataclass
class LeavePolicyCreated(BaseLeaveEvent):
    """Published when a new LeavePolicy is configured."""

    policy_name: str = ""
    policy_code: str = ""


@dataclass
class LeaveBalanceInitialized(BaseLeaveEvent):
    """Published when an employee's LeaveBalance is initialized."""

    leave_category: str = ""
    opening_balance: float = 0.0


@dataclass
class LeaveBalanceAdjusted(BaseLeaveEvent):
    """Published when an employee's LeaveBalance is credited, debited, or corrected."""

    adjustment_type: str = "CREDIT"
    amount: float = 0.0
    new_available_balance: float = 0.0


@dataclass
class LeaveAccrued(BaseLeaveEvent):
    """Published when periodic leave accrual is credited to an employee balance."""

    accrual_frequency: str = "MONTHLY"
    accrued_amount: float = 0.0


@dataclass
class LeaveExpired(BaseLeaveEvent):
    """Published when unutilized leave balances lapse or expire."""

    expired_amount: float = 0.0


@dataclass
class LeaveCarryForwardCompleted(BaseLeaveEvent):
    """Published when year-end carry forward transfer completes for an employee."""

    carried_forward_amount: float = 0.0


@dataclass
class LeaveConfigurationChanged(BaseLeaveEvent):
    """Published when hierarchical LeaveConfiguration settings are mutated."""

    configuration_id: str = ""


@dataclass
class LeaveRequested(BaseLeaveEvent):
    """Published when an employee applies for leave."""

    request_id: str = ""
    start_date: str = ""
    end_date: str = ""
    total_days: float = 0.0


@dataclass
class LeaveSubmitted(BaseLeaveEvent):
    """Published when a draft leave request is submitted for approval."""

    request_id: str = ""
    approver_id: str = ""


@dataclass
class LeaveApproved(BaseLeaveEvent):
    """Published when a leave request is approved."""

    request_id: str = ""
    approver_id: str = ""
    level: str = ""


@dataclass
class LeaveRejected(BaseLeaveEvent):
    """Published when a leave request is rejected."""

    request_id: str = ""
    rejection_reason: str = ""


@dataclass
class LeaveCancelled(BaseLeaveEvent):
    """Published when a leave request is cancelled and balance restored."""

    request_id: str = ""
    cancellation_reason: str = ""


@dataclass
class LeaveWithdrawn(BaseLeaveEvent):
    """Published when a leave request is withdrawn by employee."""

    request_id: str = ""


@dataclass
class LeaveModified(BaseLeaveEvent):
    """Published when a leave request is modified."""

    request_id: str = ""
    modification_type: str = ""


@dataclass
class LeaveReturned(BaseLeaveEvent):
    """Published when a request is returned to employee for correction."""

    request_id: str = ""


@dataclass
class LeaveEscalated(BaseLeaveEvent):
    """Published when an approval request is escalated due to timeout."""

    request_id: str = ""
    new_approver_id: str = ""


@dataclass
class LeaveAnalyticsGenerated(BaseLeaveEvent):
    """Published when leave analytics metrics are generated for an entity scope."""

    scope: str = ""
    target_id: str = ""


@dataclass
class LeaveReportGenerated(BaseLeaveEvent):
    """Published when a leave report is compiled."""

    report_type: str = ""
    format: str = ""


@dataclass
class LeaveComplianceCalculated(BaseLeaveEvent):
    """Published when organization leave compliance score and risk indicators are calculated."""

    compliance_score: float = 100.0
    total_violations: int = 0


@dataclass
class LeaveDashboardRefreshed(BaseLeaveEvent):
    """Published when an executive or manager leave dashboard dataset is refreshed."""

    dashboard_type: str = ""


@dataclass
class LeaveExportGenerated(BaseLeaveEvent):
    """Published when leave data export file (CSV/Excel/PDF) is generated."""

    export_format: str = ""
    file_name: str = ""


@dataclass
class AnalyticsCacheInvalidated(BaseLeaveEvent):
    """Published when leave analytics cache is purged following state mutations."""

    reason: str = ""




def publish_leave_event(event: BaseLeaveEvent) -> None:
    """Publish an internal leave domain event."""
    logger.info(
        "Leave Event Published [%s] for Org %s (Employee: %s, LeaveType: %s): Event ID %s",
        event.event_type,
        event.organization_id,
        event.employee_id or "N/A",
        event.leave_type_id or "N/A",
        event.event_id,
    )
