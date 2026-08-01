"""Custom model managers for the organizations app."""

from apps.common.models import SoftDeleteManager


class OrganizationManager(SoftDeleteManager):
    """Custom manager for Organization queries."""

    def active(self):
        return self.get_queryset().filter(status="ACTIVE")


class BranchManager(SoftDeleteManager):
    """Custom manager for Branch queries."""

    def active(self):
        return self.get_queryset().filter(status="ACTIVE")


class DepartmentManager(SoftDeleteManager):
    """Custom manager for Department queries."""

    def active(self):
        return self.get_queryset().filter(status="ACTIVE")


class DesignationManager(SoftDeleteManager):
    """Custom manager for Designation queries."""

    def active(self):
        return self.get_queryset().filter(status="ACTIVE")


class TeamManager(SoftDeleteManager):
    """Custom manager for Team queries."""

    def active(self):
        return self.get_queryset().filter(status="ACTIVE")


class ShiftManager(SoftDeleteManager):
    """Custom manager for Shift queries."""

    def active(self):
        return self.get_queryset().filter(status="ACTIVE")


class HolidayCalendarManager(SoftDeleteManager):
    """Custom manager for HolidayCalendar queries."""

    def active(self):
        return self.get_queryset().filter(status="ACTIVE")
