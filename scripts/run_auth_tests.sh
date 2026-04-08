#!/bin/bash
# Script to run authentication tests with coverage reporting
# Requirements: 20.8

set -e

echo "=========================================="
echo "Multi-Auth Integration System Test Suite"
echo "=========================================="
echo ""

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# Check if uv is installed
if ! command -v uv &> /dev/null; then
    echo -e "${RED}Error: uv is not installed${NC}"
    echo "Install with: pip install uv"
    exit 1
fi

# Set Django settings
export DJANGO_SETTINGS_MODULE=neurotwin.settings

echo -e "${YELLOW}Running authentication tests...${NC}"
echo ""

# Run tests with coverage
uv run pytest apps/automation/tests/ \
    --cov=apps.automation.services.auth_strategy \
    --cov=apps.automation.services.oauth_strategy \
    --cov=apps.automation.services.meta_strategy \
    --cov=apps.automation.services.api_key_strategy \
    --cov=apps.automation.services.auth_strategy_factory \
    --cov=apps.automation.services.auth_client \
    --cov=apps.automation.services.auth_config_parser \
    --cov=apps.automation.services.auth_config_serializer \
    --cov=apps.automation.services.installation \
    --cov=apps.automation.utils.encryption \
    --cov-report=html \
    --cov-report=term-missing \
    --cov-report=json \
    --cov-fail-under=90 \
    -v

TEST_EXIT_CODE=$?

echo ""
echo "=========================================="

if [ $TEST_EXIT_CODE -eq 0 ]; then
    echo -e "${GREEN}✓ All tests passed!${NC}"
    echo ""
    echo "Coverage report generated:"
    echo "  - HTML: htmlcov/index.html"
    echo "  - JSON: coverage.json"
    echo ""
    echo "View HTML report:"
    echo "  open htmlcov/index.html  # macOS"
    echo "  xdg-open htmlcov/index.html  # Linux"
    echo "  start htmlcov/index.html  # Windows"
else
    echo -e "${RED}✗ Tests failed or coverage below 90%${NC}"
    exit 1
fi

echo "=========================================="
