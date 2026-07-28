"""Custom exception definitions."""


class NexoraError(Exception):
    """Base exception for Nexora Engine."""


class ValidationError(NexoraError):
    """Raised when request data is invalid."""
