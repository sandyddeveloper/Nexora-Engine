"""Custom exception classes for the attendance domain."""

from core.exceptions import NexoraError


class AttendanceDomainError(NexoraError):
    """Base exception for all attendance domain errors."""


class AttendanceDuplicateError(AttendanceDomainError):
    """Raised when attempting to create a duplicate attendance record for an employee on the same date."""


class AttendancePolicyValidationError(AttendanceDomainError):
    """Raised when attendance policy rules or constraints are violated."""


class AttendanceLockedError(AttendanceDomainError):
    """Raised when attempting to mutate a locked attendance record."""


class AttendanceConfigurationError(AttendanceDomainError):
    """Raised when attendance configuration inheritance or hierarchy resolution fails."""


class AttendanceCheckInError(AttendanceDomainError):
    """Raised when check-in validation constraints fail."""


class AttendanceCheckOutError(AttendanceDomainError):
    """Raised when check-out validation constraints fail."""


class AttendanceBreakError(AttendanceDomainError):
    """Raised when break start/end sequence constraints fail."""


class AttendanceCorrectionError(AttendanceDomainError):
    """Raised when correction request submission or approval workflow fails."""


class AttendanceBulkImportError(AttendanceDomainError):
    """Raised when bulk import transactional processing encounters validation errors."""


class AttendanceAnalyticsError(AttendanceDomainError):
    """Raised when attendance analytics aggregation or KPI calculation encounters invalid data."""


class AttendanceComplianceError(AttendanceDomainError):
    """Raised when compliance violation detection or scoring encounters calculation errors."""


class AttendanceReportExportError(AttendanceDomainError):
    """Raised when attendance report export (CSV/JSON) generation fails."""

