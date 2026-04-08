# PowerShell script to run authentication tests with coverage reporting
# Requirements: 20.8

Write-Host "==========================================" -ForegroundColor Cyan
Write-Host "Multi-Auth Integration System Test Suite" -ForegroundColor Cyan
Write-Host "==========================================" -ForegroundColor Cyan
Write-Host ""

# Check if uv is installed
if (-not (Get-Command uv -ErrorAction SilentlyContinue)) {
    Write-Host "Error: uv is not installed" -ForegroundColor Red
    Write-Host "Install with: pip install uv"
    exit 1
}

# Set Django settings
$env:DJANGO_SETTINGS_MODULE = "neurotwin.settings"

Write-Host "Running authentication tests..." -ForegroundColor Yellow
Write-Host ""

# Run tests with coverage
uv run pytest apps/automation/tests/ `
    --cov=apps.automation.services.auth_strategy `
    --cov=apps.automation.services.oauth_strategy `
    --cov=apps.automation.services.meta_strategy `
    --cov=apps.automation.services.api_key_strategy `
    --cov=apps.automation.services.auth_strategy_factory `
    --cov=apps.automation.services.auth_client `
    --cov=apps.automation.services.auth_config_parser `
    --cov=apps.automation.services.auth_config_serializer `
    --cov=apps.automation.services.installation `
    --cov=apps.automation.utils.encryption `
    --cov-report=html `
    --cov-report=term-missing `
    --cov-report=json `
    --cov-fail-under=90 `
    -v

$testExitCode = $LASTEXITCODE

Write-Host ""
Write-Host "==========================================" -ForegroundColor Cyan

if ($testExitCode -eq 0) {
    Write-Host "✓ All tests passed!" -ForegroundColor Green
    Write-Host ""
    Write-Host "Coverage report generated:"
    Write-Host "  - HTML: htmlcov/index.html"
    Write-Host "  - JSON: coverage.json"
    Write-Host ""
    Write-Host "View HTML report:"
    Write-Host "  start htmlcov/index.html"
} else {
    Write-Host "✗ Tests failed or coverage below 90%" -ForegroundColor Red
    exit 1
}

Write-Host "==========================================" -ForegroundColor Cyan
