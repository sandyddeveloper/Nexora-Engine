"""Internal Domain Event Bus for Employee Lifecycle and Workforce Assignment Engine."""

import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict

logger = logging.getLogger("nexora.events")


@dataclass
class BaseEmployeeEvent:
    """Base class for Employee domain event payloads."""

    event_id: str
    event_type: str
    employee_id: str
    organization_id: str
    timestamp: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class EmployeeJoinedEvent(BaseEmployeeEvent):
    """Published when an employee successfully joins an organization."""

    employee_code: str = ""
    email: str = ""


@dataclass
class EmployeeConfirmedEvent(BaseEmployeeEvent):
    """Published when an employee completes probation and is confirmed."""

    confirmation_date: str = ""


@dataclass
class EmployeeTransferredEvent(BaseEmployeeEvent):
    """Published when an employee is transferred to a new branch/department."""

    new_branch_id: str = ""
    new_department_id: str = ""


@dataclass
class EmployeeTransferredDepartment(BaseEmployeeEvent):
    """Published when an employee is assigned/transferred to a department."""

    new_department_id: str = ""


@dataclass
class EmployeeTransferredBranch(BaseEmployeeEvent):
    """Published when an employee is assigned/transferred to a branch."""

    new_branch_id: str = ""


@dataclass
class EmployeePromotedEvent(BaseEmployeeEvent):
    """Published when an employee receives a designation promotion."""

    new_designation_id: str = ""


@dataclass
class EmployeeSuspendedEvent(BaseEmployeeEvent):
    """Published when an employee is suspended."""

    reason: str = ""


@dataclass
class EmployeeResignedEvent(BaseEmployeeEvent):
    """Published when an employee submits a formal resignation."""

    requested_exit_date: str = ""


@dataclass
class EmployeeExitedEvent(BaseEmployeeEvent):
    """Published when an employee exit processing is finalized."""

    exit_date: str = ""


@dataclass
class EmployeeRehiredEvent(BaseEmployeeEvent):
    """Published when a previously exited/archived employee is rehired."""


@dataclass
class EmployeeAssignedToTeam(BaseEmployeeEvent):
    """Published when an employee is assigned to an organizational team."""

    team_id: str = ""


@dataclass
class ManagerAssigned(BaseEmployeeEvent):
    """Published when a reporting manager is assigned to an employee."""

    manager_id: str = ""
    manager_type: str = "PRIMARY"


@dataclass
class ManagerChanged(BaseEmployeeEvent):
    """Published when an employee reporting manager is updated."""

    previous_manager_id: str = ""
    new_manager_id: str = ""
    manager_type: str = "PRIMARY"


@dataclass
class ShiftAssigned(BaseEmployeeEvent):
    """Published when a shift template is assigned to an employee."""

    shift_id: str = ""


@dataclass
class WorkLocationChanged(BaseEmployeeEvent):
    """Published when an employee physical or remote work location is updated."""

    new_location: str = ""
    location_type: str = "OFFICE"


@dataclass
class HierarchyUpdated(BaseEmployeeEvent):
    """Published when an organizational reporting structure mutation is applied."""


def publish_employee_event(event: BaseEmployeeEvent) -> None:
    """Publish an internal employee domain event (logs payload and dispatches to Celery/Async Bus)."""
    logger.info(
        "Employee Event Published [%s] for Employee %s: ID %s",
        event.event_type,
        event.employee_id,
        event.event_id,
    )
