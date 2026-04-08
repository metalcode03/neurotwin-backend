# Multi-Auth Integration System Tests

Comprehensive test suite for the multi-auth integration system, covering OAuth, Meta, and API Key authentication strategies.

## Test Structure

```
apps/automation/tests/
├── conftest.py                      # Shared pytest fixtures
├── test_auth_strategies.py          # Unit tests for auth strategies
├── test_installation_flows.py       # Integration tests for complete flows
├── test_backward_compatibility.py   # Backward compatibility tests
└── README.md                        # This file
```

## Test Coverage

### Unit Tests (test_auth_strategies.py)
- **OAuthStrategy**: Authorization URL generation, token exchange, refresh, revocation, HTTPS validation
- **MetaStrategy**: Meta Business flow, long-lived tokens, business details retrieval
- **APIKeyStrategy**: API key validation, no-op refresh/revoke
- **AuthStrategyFactory**: Strategy creation, custom strategy registration
- **TokenEncryption**: Encryption/decryption round-trip, security validation

**Requirements Covered**: 20.1, 20.2, 20.3, 20.4

### Integration Tests (test_installation_flows.py)
- **OAuth Flow**: Complete end-to-end installation with mock provider
- **Meta Flow**: Complete end-to-end installation with Meta API mocks
- **API Key Flow**: Complete end-to-end installation with validation
- **Edge Cases**: Duplicate prevention, expired sessions, credential revocation

**Requirements Covered**: 20.6

### Backward Compatibility Tests (test_backward_compatibility.py)
- **Legacy OAuth Integrations**: Existing integrations continue to work
- **Migration Compatibility**: auth_type defaults, field renames, indexes
- **Data Integrity**: No data loss during migrations
- **Service Layer**: Legacy types work with new services

**Requirements Covered**: 15.3, 15.5, 20.7

## Running Tests

### Run All Tests
```bash
# Using pytest
uv run pytest apps/automation/tests/

# With verbose output
uv run pytest apps/automation/tests/ -v

# Run specific test file
uv run pytest apps/automation/tests/test_auth_strategies.py
```

### Run Specific Test Classes
```bash
# Run OAuth strategy tests only
uv run pytest apps/automation/tests/test_auth_strategies.py::TestOAuthStrategy

# Run Meta installation flow tests
uv run pytest apps/automation/tests/test_installation_flows.py::TestMetaInstallationFlow
```

### Run with Coverage
```bash
# Generate coverage report
uv run pytest apps/automation/tests/ --cov=apps.automation.services --cov=apps.automation.utils --cov-report=html --cov-report=term

# View coverage report
open htmlcov/index.html  # macOS
xdg-open htmlcov/index.html  # Linux
start htmlcov/index.html  # Windows
```

### Run Async Tests
All async tests are marked with `@pytest.mark.asyncio` and will run automatically with pytest-asyncio.

## Coverage Requirements

The test suite aims for **90% code coverage** on authentication-related code:

- `apps/automation/services/auth_strategy.py`
- `apps/automation/services/oauth_strategy.py`
- `apps/automation/services/meta_strategy.py`
- `apps/automation/services/api_key_strategy.py`
- `apps/automation/services/auth_strategy_factory.py`
- `apps/automation/services/auth_client.py`
- `apps/automation/services/installation.py`
- `apps/automation/utils/encryption.py`

**Requirement**: 20.8

## Test Dependencies

Required packages (should be in pyproject.toml):
```toml
[tool.poetry.dev-dependencies]
pytest = "^7.4.0"
pytest-django = "^4.5.0"
pytest-asyncio = "^0.21.0"
pytest-cov = "^4.1.0"
pytest-mock = "^3.11.0"
```

## Fixtures

### User Fixtures
- `user`: Creates test user for authentication tests

### Integration Type Fixtures
- `oauth_integration_type`: OAuth integration type with encrypted secrets
- `meta_integration_type`: Meta integration type with encrypted secrets
- `api_key_integration_type`: API Key integration type

### Integration Fixtures
- `oauth_integration`: Complete OAuth integration with tokens
- `legacy_oauth_integration`: Legacy OAuth integration for compatibility tests

## Mocking External Services

All external API calls are mocked using `unittest.mock.patch`:

```python
# OAuth token exchange
with patch('apps.automation.services.auth_client.AuthClient.exchange_oauth_code',
           new_callable=AsyncMock, return_value=mock_token_data):
    result = await strategy.complete_authentication(...)

# Meta business details
with patch('apps.automation.services.auth_client.AuthClient.get_meta_business_details',
           new_callable=AsyncMock, return_value=mock_business_data):
    result = await strategy.complete_authentication(...)

# API key validation
with patch('apps.automation.services.auth_client.AuthClient.validate_api_key',
           new_callable=AsyncMock, return_value=True):
    result = await strategy.complete_authentication(...)
```

## Test Database

Tests use an in-memory SQLite database configured in `conftest.py`:
- Fast execution
- Isolated from production data
- Automatically cleaned up after tests

## Continuous Integration

### GitHub Actions Example
```yaml
name: Tests

on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - uses: actions/setup-python@v4
        with:
          python-version: '3.13'
      - name: Install dependencies
        run: |
          pip install uv
          uv sync
      - name: Run tests with coverage
        run: |
          uv run pytest apps/automation/tests/ --cov=apps.automation --cov-report=xml
      - name: Upload coverage
        uses: codecov/codecov-action@v3
```

## Troubleshooting

### Import Errors
If you encounter import errors, ensure Django settings are configured:
```bash
export DJANGO_SETTINGS_MODULE=neurotwin.settings
```

### Async Test Failures
Ensure pytest-asyncio is installed and async tests are marked:
```python
@pytest.mark.asyncio
async def test_async_function():
    result = await some_async_function()
    assert result is not None
```

### Database Errors
If tests fail with database errors, ensure migrations are up to date:
```bash
uv run python manage.py migrate
```

### Encryption Key Errors
Tests use mock encryption keys. If you see encryption errors, check `conftest.py` fixture.

## Adding New Tests

### Test Naming Convention
- Test files: `test_*.py`
- Test classes: `Test*`
- Test methods: `test_*`

### Example Test Structure
```python
import pytest
from unittest.mock import patch, AsyncMock

@pytest.mark.django_db
class TestNewFeature:
    """Test suite for new feature."""
    
    def test_feature_basic_case(self, user):
        """Test basic functionality."""
        # Arrange
        # Act
        # Assert
        pass
    
    @pytest.mark.asyncio
    async def test_feature_async_case(self, user):
        """Test async functionality."""
        with patch('module.function', new_callable=AsyncMock):
            result = await async_function()
            assert result is not None
```

## Property-Based Tests (Optional)

Property-based tests using Hypothesis are marked as optional (tasks 12.2-12.6) and can be added for additional validation:

```python
from hypothesis import given, strategies as st

@given(st.text())
def test_encryption_roundtrip(plaintext):
    """Property: encrypt then decrypt returns original."""
    encrypted = TokenEncryption.encrypt(plaintext)
    decrypted = TokenEncryption.decrypt(encrypted)
    assert decrypted == plaintext
```

## Test Maintenance

- Run tests before committing code
- Update tests when modifying authentication logic
- Maintain 90% coverage threshold
- Add tests for new authentication strategies
- Keep mocks synchronized with actual API responses

## Support

For questions or issues with tests:
1. Check test output for specific error messages
2. Review fixture definitions in `conftest.py`
3. Verify mock configurations match actual service behavior
4. Consult requirements document for expected behavior
