"""Custom domain exception classes for the Leave Management Foundation Engine."""

from core.exceptions import NexoraError


class LeaveDomainError(NexoraError):
    """Base exception for all leave domain errors."""


class LeavePolicyValidationError(LeaveDomainError):
    """Raised when leave policy constraints or rules are violated."""


class LeaveBalanceError(LeaveDomainError):
    """Raised when leave balance operations (insufficient balance, duplicate balance) fail."""


class LeaveAccrualError(LeaveDomainError):
    """Raised when leave accrual calculations or processing fail."""


class LeaveEligibilityError(LeaveDomainError):
    """Raised when an employee fails eligibility criteria for a leave policy or balance."""


class LeaveCarryForwardError(LeaveDomainError):
    """Raised when year-end carry forward transfer rules fail validation."""


class LeaveConfigurationError(LeaveDomainError):
    """Raised when hierarchical leave configuration resolution encounters errors."""


class LeaveExpiryError(LeaveDomainError):
    """Raised when leave expiry calculations or execution fail."""
