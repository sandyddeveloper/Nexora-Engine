"""Internal Domain Event Bus for the Attendance Foundation & Processing Engine."""

import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict

logger = logging.getLogger("nexora.attendance.events")


@dataclass
class BaseAttendanceEvent:
    """Base class for Attendance domain event payloads."""

    event_id: str
    event_type: str
    attendance_record_id: str
    employee_id: str
    organization_id: str
    timestamp: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class AttendanceRecordCreated(BaseAttendanceEvent):
    """Published when an attendance record is created."""

    attendance_date: str = ""
    status: str = "PRESENT"


@dataclass
class AttendancePolicyAssigned(BaseAttendanceEvent):
    """Published when an attendance policy is assigned."""

    policy_id: str = ""


@dataclass
class AttendanceConfigurationChanged(BaseAttendanceEvent):
    """Published when attendance configuration settings are mutated."""

    configuration_id: str = ""


@dataclass
class AttendanceLocked(BaseAttendanceEvent):
    """Published when attendance records are locked for processing/payroll."""

    lock_date: str = ""


@dataclass
class AttendanceUnlocked(BaseAttendanceEvent):
    """Published when attendance records are unlocked for adjustments."""

    unlock_date: str = ""


@dataclass
class AttendanceDeleted(BaseAttendanceEvent):
    """Published when an attendance record is soft deleted."""


@dataclass
class AttendanceCorrected(BaseAttendanceEvent):
    """Published when an attendance record is modified by an administrator/manager."""

    previous_status: str = ""
    new_status: str = ""


@dataclass
class AttendanceImported(BaseAttendanceEvent):
    """Published when attendance data is bulk imported from biometric/device source."""

    batch_id: str = ""


@dataclass
class EmployeeCheckedIn(BaseAttendanceEvent):
    """Published when an employee successfully checks in."""

    check_in_time: str = ""
    source: str = "WEB"


@dataclass
class EmployeeCheckedOut(BaseAttendanceEvent):
    """Published when an employee successfully checks out."""

    check_out_time: str = ""
    working_duration_minutes: int = 0


@dataclass
class BreakStarted(BaseAttendanceEvent):
    """Published when an employee starts a break session."""

    break_type: str = "LUNCH"
    start_time: str = ""


@dataclass
class BreakEnded(BaseAttendanceEvent):
    """Published when an employee ends a break session."""

    break_type: str = "LUNCH"
    end_time: str = ""
    duration_minutes: int = 0


@dataclass
class AttendanceCalculated(BaseAttendanceEvent):
    """Published when daily attendance metrics (hours, status, late/early) are calculated."""

    working_hours: str = "0.00"
    calculated_status: str = "PRESENT"


@dataclass
class MissedPunchDetected(BaseAttendanceEvent):
    """Published when an incomplete punch (missing check-out/check-in) is flagged."""

    missing_type: str = "CHECK_OUT"


@dataclass
class AttendanceCorrectionSubmitted(BaseAttendanceEvent):
    """Published when an employee submits an attendance correction request."""

    correction_request_id: str = ""


@dataclass
class AttendanceCorrectionProcessed(BaseAttendanceEvent):
    """Published when a manager approves or rejects an attendance correction request."""

    correction_request_id: str = ""
    approval_status: str = "APPROVED"


@dataclass
class AttendanceAnalyticsGenerated(BaseAttendanceEvent):
    """Published when attendance analytics summary calculations are compiled."""

    level: str = "ORGANIZATION"
    target_id: str = ""


@dataclass
class AttendanceReportGenerated(BaseAttendanceEvent):
    """Published when an attendance report is compiled."""

    report_type: str = "SUMMARY"


@dataclass
class ComplianceCalculated(BaseAttendanceEvent):
    """Published when organizational compliance metrics and risk flags are calculated."""

    compliance_score: float = 100.0


@dataclass
class DashboardRefreshed(BaseAttendanceEvent):
    """Published when executive dashboard analytics caches are refreshed."""

    dashboard_role: str = "EXECUTIVE"


@dataclass
class AttendanceExportGenerated(BaseAttendanceEvent):
    """Published when an attendance report export file (CSV/JSON) is generated."""

    format: str = "CSV"


def publish_attendance_event(event: BaseAttendanceEvent) -> None:
    """Publish an internal attendance domain event."""
    logger.info(
        "Attendance Event Published [%s] for Record %s (Employee %s): ID %s",
        event.event_type,
        event.attendance_record_id,
        event.employee_id,
        event.event_id,
    )
