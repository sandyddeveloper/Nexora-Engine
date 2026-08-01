"""Custom exception classes for the employees domain."""

from core.exceptions import NexoraError


class EmployeeDomainError(NexoraError):
    """Base exception for all employee domain errors."""


class InvalidEmployeeLifecycleTransitionError(EmployeeDomainError):
    """Raised when an illegal employee FSM state transition is attempted."""


class EmployeeResignationError(EmployeeDomainError):
    """Raised when an invalid resignation mutation is attempted."""


class CircularReportingError(EmployeeDomainError):
    """Raised when an employee reporting manager assignment creates a circular loop."""


class MaxHierarchyDepthExceededError(EmployeeDomainError):
    """Raised when organizational reporting hierarchy depth exceeds the maximum threshold limit."""


class EmployeeHierarchyError(EmployeeDomainError):
    """Raised when hierarchy constraints between Organization, Branch, Dept, Designation, Team are broken."""


class WorkforceAssignmentError(EmployeeDomainError):
    """Raised when a workforce shift, location, or team assignment constraint is violated."""


class InvalidManagerTypeError(EmployeeDomainError):
    """Raised when an invalid manager assignment type is specified."""


class WorkforceLocationError(EmployeeDomainError):
    """Raised when an invalid work location assignment mutation is attempted."""
