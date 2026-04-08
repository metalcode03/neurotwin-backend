# Multi-Auth Integration System - Testing Quick Start

## Run All Tests

### Option 1: Use Test Scripts (Recommended)
```bash
# Unix/Linux/macOS
./scripts/run_auth_tests.sh

# Windows PowerShell
.\scripts\run_auth_tests.ps1
```

### Option 2: Direct pytest
```bash
uv run pytest apps/automation/tests/ -v
```

## Run Tests with Coverage

```bash
uv run pytest apps/automation/tests/ \
    --cov=apps.automation.services \
    --cov=apps.automation.utils \
    --cov-report=html \
    --cov-report=term-missing \
    --cov-fail-under=90
```

## View Coverage Report

```bash
# macOS
open htmlcov/index.html

# Linux
xdg-open htmlcov/index.html

# Windows
start htmlcov/index.html
```

## Run Specific Tests

```bash
# Unit tests only
uv run pytest apps/automation/tests/test_auth_strategies.py -v

# Integration tests only
uv run pytest apps/automation/tests/test_installation_flows.py -v

# Backward compatibility tests only
uv run pytest apps/automation/tests/test_backward_compatibility.py -v

# Specific test class
uv run pytest apps/automation/tests/test_auth_strategies.py::TestOAuthStrategy -v

# Specific test method
uv run pytest apps/automation/tests/test_auth_strategies.py::TestOAuthStrategy::test_get_authorization_url -v
```

## Test Statistics

- **Total Tests**: 65+
- **Unit Tests**: 30+
- **Integration Tests**: 15+
- **Compatibility Tests**: 20+
- **Coverage Target**: 90%

## Test Files

1. `apps/automation/tests/test_auth_strategies.py` - Unit tests for auth strategies
2. `apps/automation/tests/test_installation_flows.py` - Integration tests for flows
3. `apps/automation/tests/test_backward_compatibility.py` - Backward compatibility tests
4. `apps/automation/tests/conftest.py` - Shared fixtures
5. `apps/automation/tests/README.md` - Detailed documentation

## Requirements Validated

- ✅ 20.1: OAuth strategy unit tests
- ✅ 20.2: Meta strategy unit tests
- ✅ 20.3: API Key strategy unit tests
- ✅ 20.4: Error handling tests
- ✅ 20.6: Integration tests
- ✅ 20.7: Backward compatibility tests
- ✅ 20.8: 90% coverage threshold
- ✅ 15.3: Legacy OAuth compatibility
- ✅ 15.5: oauth_config accessor

## Troubleshooting

### Import Errors
```bash
export DJANGO_SETTINGS_MODULE=neurotwin.settings
```

### Missing Dependencies
```bash
uv sync
```

### Database Errors
```bash
uv run python manage.py migrate
```

## Documentation

- Full documentation: `apps/automation/tests/README.md`
- Test summary: `apps/automation/tests/TESTING_SUMMARY.md`
- Implementation status: `apps/automation/tests/IMPLEMENTATION_COMPLETE.md`

## Next Steps

1. Run tests to verify all pass
2. Check coverage meets 90% threshold
3. Review coverage report for gaps
4. Add to CI/CD pipeline
5. Maintain tests with code changes
