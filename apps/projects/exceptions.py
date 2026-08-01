"""Custom domain exception classes for projects app."""

from core.exceptions import NexoraError


class ProjectEngineError(NexoraError):
    """Base exception for all Project Management Engine errors."""

    message = "An error occurred in the Project Management Engine."


class ProjectNotFoundError(ProjectEngineError):
    """Raised when a requested project or member entity does not exist."""

    message = "The requested project record was not found."


class ProjectValidationError(ProjectEngineError):
    """Raised when domain validation rules are violated."""

    message = "Project validation error."


class ProjectLifecycleError(ProjectEngineError):
    """Raised when an illegal project state transition is attempted."""

    message = "Illegal project lifecycle state transition."


class ProjectPermissionDeniedError(ProjectEngineError):
    """Raised when an unauthorized project action is requested."""

    message = "Permission denied for this project action."
