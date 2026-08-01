"""Centralized default configuration data and FSM transition matrix for the Employee Lifecycle Engine."""

# Maximum allowed depth for reporting manager organizational tree traversal
MAX_HIERARCHY_DEPTH = 10

# Employee Lifecycle Finite State Machine (FSM) Transition Matrix
# Key: Current Status -> Value: Set of Allowed Target Statuses
EMPLOYEE_LIFECYCLE_TRANSITIONS = {
    "CANDIDATE": {"OFFER_RELEASED", "JOINED", "TERMINATED"},
    "OFFER_RELEASED": {"JOINED", "CANDIDATE", "TERMINATED"},
    "JOINED": {"PROBATION", "CONFIRMED", "ACTIVE", "TERMINATED"},
    "PROBATION": {"CONFIRMED", "ACTIVE", "NOTICE_PERIOD", "RESIGNED", "TERMINATED"},
    "CONFIRMED": {
        "ACTIVE",
        "TRANSFERRED",
        "PROMOTED",
        "ON_LEAVE",
        "SUSPENDED",
        "RESIGNED",
        "NOTICE_PERIOD",
        "TERMINATED",
    },
    "ACTIVE": {
        "TRANSFERRED",
        "PROMOTED",
        "ON_LEAVE",
        "SUSPENDED",
        "RESIGNED",
        "NOTICE_PERIOD",
        "TERMINATED",
    },
    "TRANSFERRED": {"ACTIVE", "PROMOTED", "ON_LEAVE", "SUSPENDED", "RESIGNED", "TERMINATED"},
    "PROMOTED": {"ACTIVE", "TRANSFERRED", "ON_LEAVE", "SUSPENDED", "RESIGNED", "TERMINATED"},
    "ON_LEAVE": {"ACTIVE", "RESIGNED", "TERMINATED"},
    "SUSPENDED": {"ACTIVE", "RESIGNED", "TERMINATED"},
    "RESIGNED": {"NOTICE_PERIOD", "EXITED", "ACTIVE"},  # ACTIVE allows withdrawal
    "NOTICE_PERIOD": {"EXITED", "ACTIVE"},  # ACTIVE allows withdrawal
    "EXITED": {"ARCHIVED", "JOINED"},  # JOINED allows rehire
    "ARCHIVED": {"ACTIVE", "JOINED"},  # Restore or rehire
}
