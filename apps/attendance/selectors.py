"""Read-only query selector functions for the Attendance Foundation Engine."""

import datetime
import uuid
from typing import Optional

from django.db import models
from django.db.models import Count, QuerySet

from .models import (
    AttendanceBreak,
    AttendanceConfiguration,
    AttendanceCorrectionRequest,
    AttendanceEvent,
    AttendancePolicy,
    AttendanceRecord,
    AttendanceSession,
    AttendanceStatus,
    CorrectionStatus,
)


def get_attendance_policy(*, policy_id: str | uuid.UUID) -> Optional[AttendancePolicy]:
    """Retrieve an AttendancePolicy by UUID primary key."""
    try:
        return AttendancePolicy.objects.select_related("organization").get(id=policy_id)
    except AttendancePolicy.DoesNotExist:
        return None


def get_default_attendance_policy(*, organization_id: str | uuid.UUID) -> Optional[AttendancePolicy]:
    """Retrieve default AttendancePolicy for an organization."""
    try:
        return AttendancePolicy.objects.get(organization_id=organization_id, is_default=True)
    except AttendancePolicy.DoesNotExist:
        return AttendancePolicy.objects.filter(organization_id=organization_id).first()


def get_effective_attendance_configuration(
    *,
    organization_id: str | uuid.UUID,
    branch_id: str | uuid.UUID | None = None,
    department_id: str | uuid.UUID | None = None,
    team_id: str | uuid.UUID | None = None,
) -> Optional[AttendanceConfiguration]:
    """Resolve hierarchical AttendanceConfiguration (Team -> Department -> Branch -> Organization default)."""
    # 1. Team Level
    if team_id:
        cfg = AttendanceConfiguration.objects.filter(
            organization_id=organization_id, team_id=team_id
        ).select_related("default_policy").first()
        if cfg:
            return cfg

    # 2. Department Level
    if department_id:
        cfg = AttendanceConfiguration.objects.filter(
            organization_id=organization_id, department_id=department_id, team__isnull=True
        ).select_related("default_policy").first()
        if cfg:
            return cfg

    # 3. Branch Level
    if branch_id:
        cfg = AttendanceConfiguration.objects.filter(
            organization_id=organization_id, branch_id=branch_id, department__isnull=True, team__isnull=True
        ).select_related("default_policy").first()
        if cfg:
            return cfg

    # 4. Organization Level
    return AttendanceConfiguration.objects.filter(
        organization_id=organization_id, branch__isnull=True, department__isnull=True, team__isnull=True
    ).select_related("default_policy").first()


def get_attendance_record(*, record_id: str | uuid.UUID) -> Optional[AttendanceRecord]:
    """Retrieve an AttendanceRecord by UUID primary key with related metadata."""
    try:
        return AttendanceRecord.objects.select_related(
            "employee", "organization", "branch", "department", "designation", "team", "shift", "policy"
        ).get(id=record_id)
    except AttendanceRecord.DoesNotExist:
        return None


def get_employee_daily_attendance(
    *, employee_id: str | uuid.UUID, attendance_date: datetime.date
) -> Optional[AttendanceRecord]:
    """Retrieve an employee's AttendanceRecord for a specific calendar date."""
    try:
        return AttendanceRecord.objects.select_related("policy", "shift").get(
            employee_id=employee_id, attendance_date=attendance_date
        )
    except AttendanceRecord.DoesNotExist:
        return None


def list_attendance_records(
    *,
    organization_id: str | uuid.UUID,
    start_date: datetime.date | None = None,
    end_date: datetime.date | None = None,
    employee_id: str | uuid.UUID | None = None,
    branch_id: str | uuid.UUID | None = None,
    department_id: str | uuid.UUID | None = None,
    status: str | None = None,
) -> QuerySet[AttendanceRecord]:
    """Retrieve filtered QuerySet of AttendanceRecord instances with query optimization."""
    qs = AttendanceRecord.objects.filter(organization_id=organization_id).select_related(
        "employee", "branch", "department", "designation", "policy"
    )

    if start_date:
        qs = qs.filter(attendance_date__gte=start_date)
    if end_date:
        qs = qs.filter(attendance_date__lte=end_date)
    if employee_id:
        qs = qs.filter(employee_id=employee_id)
    if branch_id:
        qs = qs.filter(branch_id=branch_id)
    if department_id:
        qs = qs.filter(department_id=department_id)
    if status:
        qs = qs.filter(status=status)

    return qs.order_by("-attendance_date", "employee__first_name")


def get_attendance_summary(*, organization_id: str | uuid.UUID, attendance_date: datetime.date) -> dict:
    """Return aggregated count of attendance statuses for an organization on a given date."""
    counts = (
        AttendanceRecord.objects.filter(organization_id=organization_id, attendance_date=attendance_date)
        .values("status")
        .annotate(total=Count("id"))
    )

    summary = {item["status"]: item["total"] for item in counts}
    summary["total_records"] = sum(summary.values())
    return summary


def get_active_session(*, employee_id: str | uuid.UUID) -> Optional[AttendanceSession]:
    """Retrieve an employee's currently active (open check-in without check-out) session."""
    return (
        AttendanceSession.objects.filter(
            attendance_record__employee_id=employee_id, check_out__isnull=True
        )
        .select_related("attendance_record", "attendance_record__policy", "attendance_record__shift")
        .order_by("-check_in")
        .first()
    )


def get_active_break(*, session_id: str | uuid.UUID) -> Optional[AttendanceBreak]:
    """Retrieve currently active (open break start without break end) break interval."""
    return AttendanceBreak.objects.filter(session_id=session_id, end_time__isnull=True).order_by("-start_time").first()


def list_pending_corrections(*, organization_id: str | uuid.UUID) -> QuerySet[AttendanceCorrectionRequest]:
    """Retrieve list of pending attendance correction requests for an organization."""
    return AttendanceCorrectionRequest.objects.filter(
        attendance_record__organization_id=organization_id, status=CorrectionStatus.PENDING
    ).select_related("attendance_record", "attendance_record__employee", "requested_by")


def get_missed_punches(*, organization_id: str | uuid.UUID, attendance_date: datetime.date) -> QuerySet[AttendanceRecord]:
    """Retrieve attendance records for a given date with incomplete check-out (open sessions)."""
    return AttendanceRecord.objects.filter(
        organization_id=organization_id,
        attendance_date=attendance_date,
        sessions__check_out__isnull=True,
    ).distinct().select_related("employee", "branch", "department")


# ── Attendance Analytics & Compliance Selectors ────────────────────────────────


def _compute_kpis(qs: QuerySet[AttendanceRecord], total_days: int) -> dict:
    """Compute standardized KPI metrics from an AttendanceRecord QuerySet and calendar span."""
    from django.db.models import Avg, Sum

    aggregates = qs.aggregate(
        total_records=Count("id"),
        present_count=Count("id", filter=models.Q(status=AttendanceStatus.PRESENT)),
        absent_count=Count("id", filter=models.Q(status=AttendanceStatus.ABSENT)),
        half_day_count=Count("id", filter=models.Q(status=AttendanceStatus.HALF_DAY)),
        late_count=Count("id", filter=models.Q(status=AttendanceStatus.LATE)),
        early_exit_count=Count("id", filter=models.Q(status=AttendanceStatus.EARLY_EXIT)),
        wfh_count=Count("id", filter=models.Q(status=AttendanceStatus.WORK_FROM_HOME)),
        leave_count=Count("id", filter=models.Q(status=AttendanceStatus.LEAVE)),
        avg_working_hours=Avg("working_hours"),
        avg_overtime_hours=Avg("overtime_hours"),
        total_working_hours=Sum("working_hours"),
        total_overtime_hours=Sum("overtime_hours"),
    )

    total_records = aggregates["total_records"] or 0
    present = aggregates["present_count"] or 0
    absent = aggregates["absent_count"] or 0
    late = aggregates["late_count"] or 0
    early_exit = aggregates["early_exit_count"] or 0

    denominator = max(total_records, 1)

    attendance_pct = round((present / denominator) * 100, 2)
    absence_pct = round((absent / denominator) * 100, 2)
    late_pct = round((late / denominator) * 100, 2)
    early_exit_pct = round((early_exit / denominator) * 100, 2)

    # Attendance Score (0-100): 100 - (absence% + late%/2 + early_exit%/2)
    attendance_score = round(max(0, min(100, 100.0 - absence_pct - (late_pct / 2) - (early_exit_pct / 2))), 2)

    # Compliance Score (0-100): 100 - (late% + early_exit% + overtime risk penalty)
    overtime_penalty = min(10.0, float(aggregates["total_overtime_hours"] or 0) * 0.5)
    compliance_score = round(max(0, min(100, 100.0 - late_pct - early_exit_pct - overtime_penalty)), 2)

    return {
        "total_records": total_records,
        "total_calendar_days": total_days,
        "present_count": present,
        "absent_count": absent,
        "half_day_count": aggregates["half_day_count"] or 0,
        "late_count": late,
        "early_exit_count": early_exit,
        "wfh_count": aggregates["wfh_count"] or 0,
        "leave_count": aggregates["leave_count"] or 0,
        "attendance_percentage": attendance_pct,
        "absence_percentage": absence_pct,
        "late_percentage": late_pct,
        "early_exit_percentage": early_exit_pct,
        "avg_working_hours": round(float(aggregates["avg_working_hours"] or 0), 2),
        "avg_overtime_hours": round(float(aggregates["avg_overtime_hours"] or 0), 2),
        "total_working_hours": round(float(aggregates["total_working_hours"] or 0), 2),
        "total_overtime_hours": round(float(aggregates["total_overtime_hours"] or 0), 2),
        "attendance_score": attendance_score,
        "compliance_score": compliance_score,
    }


def get_employee_attendance_analytics(
    *,
    employee_id: str | uuid.UUID,
    start_date: datetime.date,
    end_date: datetime.date,
) -> dict:
    """Generate attendance KPI analytics for a single employee within a date window."""
    qs = AttendanceRecord.objects.filter(
        employee_id=employee_id,
        attendance_date__gte=start_date,
        attendance_date__lte=end_date,
    )
    total_days = (end_date - start_date).days + 1
    kpis = _compute_kpis(qs, total_days)
    kpis["level"] = "EMPLOYEE"
    kpis["target_id"] = str(employee_id)
    kpis["start_date"] = start_date.isoformat()
    kpis["end_date"] = end_date.isoformat()
    return kpis


def get_team_attendance_analytics(
    *,
    team_id: str | uuid.UUID,
    start_date: datetime.date,
    end_date: datetime.date,
) -> dict:
    """Generate aggregated attendance KPI analytics for a team within a date window."""
    qs = AttendanceRecord.objects.filter(
        team_id=team_id,
        attendance_date__gte=start_date,
        attendance_date__lte=end_date,
    )
    total_days = (end_date - start_date).days + 1
    kpis = _compute_kpis(qs, total_days)
    kpis["level"] = "TEAM"
    kpis["target_id"] = str(team_id)
    kpis["start_date"] = start_date.isoformat()
    kpis["end_date"] = end_date.isoformat()
    return kpis


def get_department_attendance_analytics(
    *,
    department_id: str | uuid.UUID,
    start_date: datetime.date,
    end_date: datetime.date,
) -> dict:
    """Generate aggregated attendance KPI analytics for a department within a date window."""
    qs = AttendanceRecord.objects.filter(
        department_id=department_id,
        attendance_date__gte=start_date,
        attendance_date__lte=end_date,
    )
    total_days = (end_date - start_date).days + 1
    kpis = _compute_kpis(qs, total_days)
    kpis["level"] = "DEPARTMENT"
    kpis["target_id"] = str(department_id)
    kpis["start_date"] = start_date.isoformat()
    kpis["end_date"] = end_date.isoformat()
    return kpis


def get_branch_attendance_analytics(
    *,
    branch_id: str | uuid.UUID,
    start_date: datetime.date,
    end_date: datetime.date,
) -> dict:
    """Generate aggregated attendance KPI analytics for a branch within a date window."""
    qs = AttendanceRecord.objects.filter(
        branch_id=branch_id,
        attendance_date__gte=start_date,
        attendance_date__lte=end_date,
    )
    total_days = (end_date - start_date).days + 1
    kpis = _compute_kpis(qs, total_days)
    kpis["level"] = "BRANCH"
    kpis["target_id"] = str(branch_id)
    kpis["start_date"] = start_date.isoformat()
    kpis["end_date"] = end_date.isoformat()
    return kpis


def get_organization_attendance_analytics(
    *,
    organization_id: str | uuid.UUID,
    start_date: datetime.date,
    end_date: datetime.date,
) -> dict:
    """Generate aggregated attendance KPI analytics for an entire organization within a date window."""
    qs = AttendanceRecord.objects.filter(
        organization_id=organization_id,
        attendance_date__gte=start_date,
        attendance_date__lte=end_date,
    )
    total_days = (end_date - start_date).days + 1
    kpis = _compute_kpis(qs, total_days)
    kpis["level"] = "ORGANIZATION"
    kpis["target_id"] = str(organization_id)
    kpis["start_date"] = start_date.isoformat()
    kpis["end_date"] = end_date.isoformat()
    return kpis


def get_compliance_violations(
    *,
    organization_id: str | uuid.UUID,
    start_date: datetime.date,
    end_date: datetime.date,
) -> dict:
    """Detect and aggregate compliance violations across an organization for a date window."""
    base_qs = AttendanceRecord.objects.filter(
        organization_id=organization_id,
        attendance_date__gte=start_date,
        attendance_date__lte=end_date,
    ).select_related("employee", "policy")

    late_violations = base_qs.filter(status=AttendanceStatus.LATE)
    early_exit_violations = base_qs.filter(status=AttendanceStatus.EARLY_EXIT)
    excessive_overtime = base_qs.filter(overtime_hours__gt=4)
    excessive_hours = base_qs.filter(working_hours__gt=12)

    late_list = list(
        late_violations.values(
            "id", "employee__employee_id", "employee__first_name", "employee__last_name",
            "attendance_date", "working_hours",
        )[:50]
    )
    early_exit_list = list(
        early_exit_violations.values(
            "id", "employee__employee_id", "employee__first_name", "employee__last_name",
            "attendance_date", "working_hours",
        )[:50]
    )
    overtime_list = list(
        excessive_overtime.values(
            "id", "employee__employee_id", "employee__first_name", "employee__last_name",
            "attendance_date", "overtime_hours",
        )[:50]
    )
    excessive_hours_list = list(
        excessive_hours.values(
            "id", "employee__employee_id", "employee__first_name", "employee__last_name",
            "attendance_date", "working_hours",
        )[:50]
    )

    total_violations = late_violations.count() + early_exit_violations.count() + excessive_overtime.count() + excessive_hours.count()
    total_records = base_qs.count()
    compliance_rate = round(((max(total_records, 1) - total_violations) / max(total_records, 1)) * 100, 2)

    return {
        "organization_id": str(organization_id),
        "start_date": start_date.isoformat(),
        "end_date": end_date.isoformat(),
        "total_records": total_records,
        "total_violations": total_violations,
        "compliance_rate": compliance_rate,
        "late_arrival_violations": {"count": late_violations.count(), "records": late_list},
        "early_exit_violations": {"count": early_exit_violations.count(), "records": early_exit_list},
        "excessive_overtime_violations": {"count": excessive_overtime.count(), "records": overtime_list},
        "excessive_hours_violations": {"count": excessive_hours.count(), "records": excessive_hours_list},
    }


def get_dashboard_analytics(
    *,
    organization_id: str | uuid.UUID,
    user_role: str = "EXECUTIVE",
    target_id: str | uuid.UUID | None = None,
) -> dict:
    """Generate executive dashboard analytics payload optimized for a specific user role."""
    import datetime as dt

    today = dt.date.today()
    month_start = today.replace(day=1)
    week_start = today - dt.timedelta(days=today.weekday())

    # Today's snapshot
    today_qs = AttendanceRecord.objects.filter(organization_id=organization_id, attendance_date=today)
    today_summary = {
        item["status"]: item["total"]
        for item in today_qs.values("status").annotate(total=Count("id"))
    }
    today_summary["total_employees_logged"] = sum(today_summary.values())

    # Monthly KPIs
    monthly_qs = AttendanceRecord.objects.filter(
        organization_id=organization_id,
        attendance_date__gte=month_start,
        attendance_date__lte=today,
    )
    monthly_days = (today - month_start).days + 1
    monthly_kpis = _compute_kpis(monthly_qs, monthly_days)

    # Weekly KPIs
    weekly_qs = AttendanceRecord.objects.filter(
        organization_id=organization_id,
        attendance_date__gte=week_start,
        attendance_date__lte=today,
    )
    weekly_days = (today - week_start).days + 1
    weekly_kpis = _compute_kpis(weekly_qs, weekly_days)

    # Daily trend (last 7 days)
    daily_trend = []
    for i in range(7):
        d = today - dt.timedelta(days=i)
        day_qs = AttendanceRecord.objects.filter(organization_id=organization_id, attendance_date=d)
        day_counts = {item["status"]: item["total"] for item in day_qs.values("status").annotate(total=Count("id"))}
        daily_trend.append({"date": d.isoformat(), "present": day_counts.get("PRESENT", 0), "absent": day_counts.get("ABSENT", 0), "late": day_counts.get("LATE", 0)})

    return {
        "organization_id": str(organization_id),
        "dashboard_role": user_role,
        "generated_at": today.isoformat(),
        "today_snapshot": today_summary,
        "monthly_kpis": monthly_kpis,
        "weekly_kpis": weekly_kpis,
        "daily_trend": daily_trend,
    }


def get_ai_analytics_foundation_data(
    *,
    organization_id: str | uuid.UUID,
    start_date: datetime.date,
    end_date: datetime.date,
) -> dict:
    """Generate structured AI foundation data vectors for workforce analytics and anomaly detection."""
    from django.db.models import Avg, Sum

    base_qs = AttendanceRecord.objects.filter(
        organization_id=organization_id,
        attendance_date__gte=start_date,
        attendance_date__lte=end_date,
    )

    # Per-employee behavioral vectors
    employee_vectors = list(
        base_qs.values("employee_id", "employee__employee_id", "employee__first_name", "employee__last_name")
        .annotate(
            total_records=Count("id"),
            present_count=Count("id", filter=models.Q(status=AttendanceStatus.PRESENT)),
            absent_count=Count("id", filter=models.Q(status=AttendanceStatus.ABSENT)),
            late_count=Count("id", filter=models.Q(status=AttendanceStatus.LATE)),
            early_exit_count=Count("id", filter=models.Q(status=AttendanceStatus.EARLY_EXIT)),
            avg_working_hours=Avg("working_hours"),
            total_overtime=Sum("overtime_hours"),
        )
        .order_by("-absent_count", "-late_count")[:100]
    )

    # Burnout risk: high overtime + high working hours
    burnout_risk = list(
        base_qs.values("employee_id", "employee__employee_id")
        .annotate(
            avg_hours=Avg("working_hours"),
            total_overtime=Sum("overtime_hours"),
        )
        .filter(avg_hours__gt=10)
        .order_by("-avg_hours")[:50]
    )

    # Absenteeism patterns
    absenteeism = list(
        base_qs.filter(status=AttendanceStatus.ABSENT)
        .values("employee_id", "employee__employee_id")
        .annotate(absent_days=Count("id"))
        .filter(absent_days__gte=3)
        .order_by("-absent_days")[:50]
    )

    return {
        "organization_id": str(organization_id),
        "start_date": start_date.isoformat(),
        "end_date": end_date.isoformat(),
        "employee_behavioral_vectors": employee_vectors,
        "burnout_risk_signals": burnout_risk,
        "absenteeism_patterns": absenteeism,
        "total_employees_analyzed": len(employee_vectors),
    }


