"""Domain Event Bus interfaces for the Organization & Shift Rostering Engine."""

import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict

logger = logging.getLogger("nexora.events")


@dataclass
class BaseDomainEvent:
    """Base class for internal domain event payloads."""

    event_id: str
    event_type: str
    organization_id: str
    timestamp: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class OrganizationCreatedEvent(BaseDomainEvent):
    """Event published when a new organization is created or onboarded."""

    code: str = ""
    name: str = ""


@dataclass
class OrganizationActivatedEvent(BaseDomainEvent):
    """Event published when an organization is activated."""

    previous_status: str = ""


@dataclass
class OrganizationSuspendedEvent(BaseDomainEvent):
    """Event published when an organization is suspended."""

    reason: str = ""


@dataclass
class OrganizationArchivedEvent(BaseDomainEvent):
    """Event published when an organization is archived."""


@dataclass
class ShiftRosterAssignedEvent(BaseDomainEvent):
    """Published when a shift roster assignment is created or updated."""

    roster_id: str = ""
    employee_id: str = ""


@dataclass
class RosterPublishedEvent(BaseDomainEvent):
    """Published when a shift roster is published."""

    roster_id: str = ""
    period_type: str = "WEEKLY"


@dataclass
class RosterArchivedEvent(BaseDomainEvent):
    """Published when a shift roster is archived."""

    roster_id: str = ""


@dataclass
class ShiftRotatedEvent(BaseDomainEvent):
    """Published when automatic shift rotation is executed."""

    rotation_id: str = ""


@dataclass
class ShiftOverrideAppliedEvent(BaseDomainEvent):
    """Published when an employee shift assignment override is applied."""

    employee_id: str = ""
    date: str = ""


@dataclass
class ShiftSwapRequestedEvent(BaseDomainEvent):
    """Published when a peer-to-peer shift swap is requested."""

    swap_request_id: str = ""
    requester_id: str = ""
    target_id: str = ""


def publish_domain_event(event: BaseDomainEvent) -> None:
    """Publish an internal domain event (logs payload and prepares for Async Event Bus routing)."""
    logger.info(
        "Domain Event Published [%s] for Org %s: ID %s",
        event.event_type,
        event.organization_id,
        event.event_id,
    )
