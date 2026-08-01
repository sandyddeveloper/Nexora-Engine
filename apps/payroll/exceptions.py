"""Domain exception classes for the Payroll Foundation Engine."""


class PayrollDomainError(Exception):
    """Base exception for all payroll domain errors."""

    pass


class PayrollValidationError(PayrollDomainError):
    """Raised when payroll policy, calculation, or profile validation fails."""

    pass


class PayrollProfileNotFoundError(PayrollDomainError):
    """Raised when an employee payroll profile is missing."""

    pass


class SalaryStructureError(PayrollDomainError):
    """Raised when salary structure composition or single-active rules are violated."""

    pass


class PayrollPolicyValidationError(PayrollDomainError):
    """Raised when payroll policy configuration rules fail."""

    pass
