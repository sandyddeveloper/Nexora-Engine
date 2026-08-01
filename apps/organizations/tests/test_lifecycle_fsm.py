"""Unit tests for Organization Lifecycle FSM state transitions."""

from django.test import TestCase

from apps.organizations.exceptions import InvalidLifecycleTransitionError
from apps.organizations.models import OrganizationStatus
from apps.organizations.services import (
    create_organization,
    transition_organization_status,
)


class OrganizationLifecycleFSMTests(TestCase):
    """Test suite for lifecycle state machine transition validation."""

    def setUp(self):
        self.org = create_organization(name="FSM Test Org", status=OrganizationStatus.DRAFT)

    def test_valid_lifecycle_transitions(self):
        # DRAFT -> PENDING_VERIFICATION
        self.org = transition_organization_status(
            organization=self.org, target_status=OrganizationStatus.PENDING_VERIFICATION
        )
        self.assertEqual(self.org.status, OrganizationStatus.PENDING_VERIFICATION)

        # PENDING_VERIFICATION -> ACTIVE
        self.org = transition_organization_status(
            organization=self.org, target_status=OrganizationStatus.ACTIVE
        )
        self.assertEqual(self.org.status, OrganizationStatus.ACTIVE)

        # ACTIVE -> SUSPENDED
        self.org = transition_organization_status(
            organization=self.org, target_status=OrganizationStatus.SUSPENDED, reason="Non-payment"
        )
        self.assertEqual(self.org.status, OrganizationStatus.SUSPENDED)

    def test_invalid_lifecycle_transition_raises_error(self):
        # Direct DRAFT -> ARCHIVED should fail
        with self.assertRaises(InvalidLifecycleTransitionError):
            transition_organization_status(
                organization=self.org, target_status=OrganizationStatus.ARCHIVED
            )
