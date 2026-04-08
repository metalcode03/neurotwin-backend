"""
Pytest configuration for automation app tests.

Provides shared fixtures and configuration for all test modules.
"""

import pytest
from django.conf import settings


@pytest.fixture(scope='session')
def django_db_setup():
    """Configure test database settings."""
    settings.DATABASES['default'] = {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': ':memory:',
    }


@pytest.fixture(autouse=True)
def enable_db_access_for_all_tests(db):
    """Enable database access for all tests."""
    pass


@pytest.fixture(scope='session')
def mock_encryption_key():
    """Mock encryption key for testing."""
    import os
    from cryptography.fernet import Fernet
    
    # Generate different Fernet keys for each auth type
    oauth_key = Fernet.generate_key()
    meta_key = Fernet.generate_key()
    api_key_key = Fernet.generate_key()
    
    # Set environment variables for the session with different keys
    os.environ['OAUTH_ENCRYPTION_KEY'] = oauth_key.decode()
    os.environ['META_ENCRYPTION_KEY'] = meta_key.decode()
    os.environ['API_KEY_ENCRYPTION_KEY'] = api_key_key.decode()
    
    return {
        'oauth': oauth_key,
        'meta': meta_key,
        'api_key': api_key_key
    }
