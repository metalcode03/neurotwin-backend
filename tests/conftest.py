"""
Pytest configuration and shared fixtures for NeuroTwin tests.
"""
import pytest
from hypothesis import settings, Verbosity

from hypothesis import HealthCheck

# Configure Hypothesis for property-based testing
# Minimum 100 iterations per property test as per design document
settings.register_profile(
    "default",
    max_examples=100,
    verbosity=Verbosity.normal,
    deadline=None,
    suppress_health_check=[HealthCheck.function_scoped_fixture],
)
settings.register_profile(
    "ci",
    max_examples=100,
    verbosity=Verbosity.quiet,
    deadline=None,
    suppress_health_check=[HealthCheck.function_scoped_fixture],
)
settings.register_profile(
    "debug",
    max_examples=5,
    verbosity=Verbosity.verbose,
    deadline=None,
    suppress_health_check=[HealthCheck.function_scoped_fixture],
)
settings.load_profile("default")


@pytest.fixture
def api_client():
    """Provide a Django REST Framework API client for testing."""
    from rest_framework.test import APIClient
    return APIClient()
