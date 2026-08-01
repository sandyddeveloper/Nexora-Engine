"""Domain event dataclasses and publisher for the Payroll Foundation Engine."""

import logging
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone

logger = logging.getLogger("nexora.payroll.events")


@dataclass
class BasePayrollEvent:
    """Base payload for all payroll domain events."""

    event_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    event_type: str = "BASE_PAYROLL_EVENT"
    timestamp: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    organization_id: str = ""


@dataclass
class SalaryStructureCreated(BasePayrollEvent):
    """Published when a new salary template or employee salary structure is created."""

    structure_id: str = ""
    employee_id: str = ""
    ctc_amount: float = 0.0


@dataclass
class SalaryStructureUpdated(BasePayrollEvent):
    """Published when an employee salary structure is updated or versioned."""

    structure_id: str = ""
    employee_id: str = ""
    version: int = 1


@dataclass
class PayrollPolicyCreated(BasePayrollEvent):
    """Published when a new organization or entity payroll policy is created."""

    policy_id: str = ""
    policy_name: str = ""


@dataclass
class PayrollProfileCreated(BasePayrollEvent):
    """Published when an employee payroll profile is established."""

    profile_id: str = ""
    employee_id: str = ""


@dataclass
class PayrollConfigurationChanged(BasePayrollEvent):
    """Published when payroll statutory or organization configuration defaults are updated."""

    configuration_type: str = ""


@dataclass
class SalaryRevisionCreated(BasePayrollEvent):
    """Published when an employee salary increment or revision is recorded."""

    revision_id: str = ""
    employee_id: str = ""
    previous_ctc: float = 0.0
    new_ctc: float = 0.0


@dataclass
class PayrollRunCreated(BasePayrollEvent):
    """Published when a new payroll run execution container is created."""

    run_id: str = ""
    cycle_id: str = ""


@dataclass
class PayrollCalculated(BasePayrollEvent):
    """Published when payroll calculation is completed for a run."""

    run_id: str = ""
    total_employees: int = 0
    total_gross: float = 0.0
    total_net: float = 0.0


@dataclass
class PayrollValidated(BasePayrollEvent):
    """Published when payroll run calculations are validated."""

    run_id: str = ""


@dataclass
class PayrollApproved(BasePayrollEvent):
    """Published when a approval step is recorded for a payroll run."""

    run_id: str = ""
    approval_level: str = ""
    approver_id: str = ""


@dataclass
class PayrollFinalized(BasePayrollEvent):
    """Published when a payroll run is finalized and locked."""

    run_id: str = ""
    total_net_disbursement: float = 0.0


@dataclass
class PayrollLocked(BasePayrollEvent):
    """Published when attendance, leave, and payroll data is locked for a period."""

    run_id: str = ""


@dataclass
class PayrollReopened(BasePayrollEvent):
    """Published when a finalized or approved payroll run is reopened for adjustments."""

    run_id: str = ""
    reason: str = ""


@dataclass
class PayrollRolledBack(BasePayrollEvent):
    """Published when a payroll run calculation is rolled back."""

    run_id: str = ""
    reason: str = ""


@dataclass
class PayslipGenerated(BasePayrollEvent):
    """Published when a payslip is generated for an employee."""

    payslip_id: str = ""
    employee_id: str = ""
    run_id: str = ""
    net_salary: float = 0.0


@dataclass
class PayslipDownloaded(BasePayrollEvent):
    """Published when an employee or admin downloads a payslip."""

    payslip_id: str = ""
    employee_id: str = ""
    downloaded_by_user_id: str = ""


@dataclass
class SalaryRevised(BasePayrollEvent):
    """Published when an employee salary structure is revised."""

    employee_id: str = ""
    previous_ctc: float = 0.0
    new_ctc: float = 0.0


@dataclass
class CompensationUpdated(BasePayrollEvent):
    """Published when an employee compensation history ledger is updated."""

    employee_id: str = ""
    effective_date: str = ""


@dataclass
class RetroAdjustmentCreated(BasePayrollEvent):
    """Published when a retroactive arrears or recovery adjustment is created."""

    adjustment_id: str = ""
    employee_id: str = ""
    category: str = ""
    amount: float = 0.0


@dataclass
class PayrollDistributed(BasePayrollEvent):
    """Published when salary disbursement status is updated for a payroll run."""

    run_id: str = ""
    distribution_method: str = ""
    status: str = ""


@dataclass
class ComplianceCalculated(BasePayrollEvent):
    """Published when compliance calculations complete for a payroll run."""

    run_id: str = ""
    compliance_status: str = ""
    total_exceptions: int = 0


@dataclass
class ComplianceValidated(BasePayrollEvent):
    """Published when statutory compliance checks are validated."""

    run_id: str = ""
    is_compliant: bool = True


@dataclass
class TaxRuleCreated(BasePayrollEvent):
    """Published when a statutory tax rule configuration is defined."""

    rule_id: str = ""
    country_code: str = ""
    rule_code: str = ""


@dataclass
class ContributionUpdated(BasePayrollEvent):
    """Published when statutory contribution rules are updated."""

    organization_id: str = ""
    effective_date: str = ""


@dataclass
class ComplianceReportGenerated(BasePayrollEvent):
    """Published when a statutory compliance report is generated."""

    report_id: str = ""
    report_type: str = ""


@dataclass
class PayrollAnalyticsGenerated(BasePayrollEvent):
    """Published when periodic payroll analytics snapshots are generated."""

    snapshot_id: str = ""
    period_name: str = ""


@dataclass
class PayrollDashboardGenerated(BasePayrollEvent):
    """Published when an executive dashboard payload is generated."""

    dashboard_type: str = ""


@dataclass
class PayrollReportGenerated(BasePayrollEvent):
    """Published when a payroll analytics export report is compiled."""

    report_type: str = ""


@dataclass
class PayrollForecastPrepared(BasePayrollEvent):
    """Published when historical payroll trend datasets are prepared for AI forecasting."""

    granularity: str = ""


@dataclass
class PayrollExportGenerated(BasePayrollEvent):
    """Published when payroll data is exported."""

    export_format: str = ""


@dataclass
class AnalyticsCacheInvalidated(BasePayrollEvent):
    """Published when analytics caches are invalidated."""

    reason: str = ""






def publish_payroll_event(event: BasePayrollEvent) -> None:
    """Publish an internal payroll domain event."""
    logger.info(
        "Payroll Event Published [%s] for Org %s: Event ID %s",
        event.event_type,
        event.organization_id,
        event.event_id,
    )
