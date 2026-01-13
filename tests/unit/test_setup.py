"""
Basic tests to verify the testing infrastructure is working.
"""
import pytest
from hypothesis import given, strategies as st


class TestSetup:
    """Verify testing infrastructure is properly configured."""

    def test_django_settings_loaded(self):
        """Verify Django settings are accessible."""
        from django.conf import settings
        assert settings.DEBUG is not None
        # Allow either PostgreSQL (production) or SQLite (testing)
        allowed_engines = [
            'django.db.backends.postgresql',
            'django.db.backends.sqlite3',
        ]
        assert settings.DATABASES['default']['ENGINE'] in allowed_engines

    def test_hypothesis_available(self):
        """Verify Hypothesis is properly configured."""
        from hypothesis import settings as h_settings
        profile = h_settings.get_profile("default")
        assert profile.max_examples >= 100


class TestHypothesisIntegration:
    """Verify Hypothesis property-based testing works."""

    @given(st.integers())
    def test_integers_are_integers(self, x: int):
        """Simple property test to verify Hypothesis integration."""
        assert isinstance(x, int)

    @given(st.text(min_size=1))
    def test_non_empty_strings(self, s: str):
        """Verify string generation works."""
        assert len(s) >= 1
