"""Custom managers for the employees app."""

from apps.common.models import SoftDeleteManager


class EmployeeManager(SoftDeleteManager):
    """Custom manager for Employee model providing domain query shortcuts."""

    def active_employees(self):
        """Return employees with ACTIVE status."""
        return self.get_queryset().filter(employment_status="ACTIVE")

    def for_organization(self, organization_id):
        """Filter employees by organization."""
        return self.get_queryset().filter(organization_id=organization_id)
