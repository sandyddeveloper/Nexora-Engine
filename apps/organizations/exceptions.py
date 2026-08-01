"""Custom exceptions for the Organization & Shift Rostering Engine."""

from core.exceptions import NexoraError


class OrganizationEngineError(NexoraError):
    """Base exception for all Organization Business Engine errors."""


class InvalidLifecycleTransitionError(OrganizationEngineError):
    """Raised when an illegal FSM lifecycle state transition is attempted."""


class OrganizationLimitExceededError(OrganizationEngineError):
    """Raised when a subscription quota threshold limit is exceeded."""


class FeatureFlagDisabledError(OrganizationEngineError):
    """Raised when an operation requires a disabled organization feature flag."""


class BusinessRuleValidationError(OrganizationEngineError):
    """Raised when a domain business rule constraint is violated."""


class CircularDependencyError(BusinessRuleValidationError):
    """Raised when a parent-child hierarchy loop is detected."""


class ShiftRosterError(OrganizationEngineError):
    """Raised when a shift roster creation, publication, or state transition constraint fails."""


class ShiftRotationError(OrganizationEngineError):
    """Raised when a shift rotation pattern execution fails."""


class ShiftOverlapError(OrganizationEngineError):
    """Raised when overlapping shift roster assignments are detected."""


class ShiftSwapError(OrganizationEngineError):
    """Raised when a shift swap request validation fails."""
