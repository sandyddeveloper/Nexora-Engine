"""Centralized default configuration data and transition rules for the Organization Business Rules Engine."""

# Lifecycle Finite State Machine Transition Matrix
# Key: Current Status -> Value: Set of Allowed Target Statuses
LIFECYCLE_TRANSITIONS = {
    "DRAFT": {"PENDING_VERIFICATION", "ACTIVE", "INACTIVE"},
    "PENDING_VERIFICATION": {"ACTIVE", "INACTIVE", "SUSPENDED"},
    "ACTIVE": {"SUSPENDED", "INACTIVE", "ARCHIVED"},
    "SUSPENDED": {"ACTIVE", "INACTIVE", "ARCHIVED"},
    "INACTIVE": {"ACTIVE", "ARCHIVED"},
    "ARCHIVED": set(),  # Restoration requires explicit restore_organization service workflow
}

# Default Onboarding Departments
DEFAULT_DEPARTMENTS = [
    {
        "code": "ENG",
        "name": "Engineering",
        "description": "Software development, IT infrastructure, and technical operations.",
        "ordering": 1,
    },
    {
        "code": "HR",
        "name": "Human Resources",
        "description": "Talent acquisition, employee relations, and HR administration.",
        "ordering": 2,
    },
    {
        "code": "FIN",
        "name": "Finance & Accounting",
        "description": "Financial planning, accounting, payroll, and auditing.",
        "ordering": 3,
    },
    {
        "code": "OPS",
        "name": "Operations",
        "description": "Business operations, logistics, and facilities management.",
        "ordering": 4,
    },
    {
        "code": "SALES",
        "name": "Sales & Business Development",
        "description": "Client acquisition, partnerships, and revenue growth.",
        "ordering": 5,
    },
    {
        "code": "SUP",
        "name": "Customer Support",
        "description": "Customer success, support desk, and client service delivery.",
        "ordering": 6,
    },
]

# Default Onboarding Shift Template
DEFAULT_SHIFT_CONFIG = {
    "code": "SHIFT-STD",
    "name": "Standard Morning Shift",
    "shift_type": "REGULAR",
    "start_time": "09:00:00",
    "end_time": "17:00:00",
    "grace_time_minutes": 15,
    "flexible_hours": False,
    "is_night_shift": False,
    "break_duration_minutes": 60,
    "working_hours": 8.00,
}

# Default Onboarding Holiday Calendar Entry
DEFAULT_HOLIDAY_CONFIG = {
    "name": "New Year's Day",
    "holiday_type": "PUBLIC",
    "description": "Global New Year holiday",
    "is_recurring": True,
}

# Default Subscription Quota Limits
DEFAULT_ORGANIZATION_LIMITS = {
    "max_branches": 10,
    "max_departments": 25,
    "max_teams": 50,
    "max_shifts": 20,
    "max_employees": 250,
    "max_storage_gb": 100,
    "max_api_calls_per_day": 10000,
    "max_projects": 50,
}

# Default Feature Flags Configuration
DEFAULT_FEATURE_FLAGS = {
    "attendance_enabled": True,
    "payroll_enabled": True,
    "crm_enabled": True,
    "projects_enabled": True,
    "documents_enabled": True,
    "ai_assistant_enabled": False,
    "automation_enabled": True,
    "api_access_enabled": True,
}
