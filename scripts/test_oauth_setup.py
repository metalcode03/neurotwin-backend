#!/usr/bin/env python
"""
OAuth Setup Verification Script

This script helps verify that OAuth configuration is set up correctly
for Gmail and Slack integrations.

Usage:
    python scripts/test_oauth_setup.py
"""

import os
import sys
import django

# Setup Django environment
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'neurotwin.settings')
django.setup()

from apps.automation.models import IntegrationTypeModel
from apps.automation.utils.encryption import TokenEncryption
from django.conf import settings


def check_environment_variables():
    """Check if required environment variables are set."""
    print("=" * 60)
    print("ENVIRONMENT VARIABLES CHECK")
    print("=" * 60)
    
    required_vars = {
        'TOKEN_ENCRYPTION_KEY': 'Token encryption key',
        'OAUTH_REDIRECT_URI': 'OAuth redirect URI',
        'FRONTEND_URL': 'Frontend URL',
    }
    
    all_set = True
    for var, description in required_vars.items():
        value = os.getenv(var)
        if value:
            # Mask sensitive values
            if 'KEY' in var or 'SECRET' in var:
                display_value = f"{value[:8]}...{value[-8:]}" if len(value) > 16 else "[SET]"
            else:
                display_value = value
            print(f"✓ {var}: {display_value}")
        else:
            print(f"✗ {var}: NOT SET")
            all_set = False
    
    print()
    return all_set


def check_encryption():
    """Test token encryption/decryption."""
    print("=" * 60)
    print("ENCRYPTION TEST")
    print("=" * 60)
    
    try:
        test_token = "test_oauth_token_12345"
        
        # Encrypt
        encrypted = TokenEncryption.encrypt(test_token)
        print(f"✓ Encryption successful (length: {len(encrypted)} bytes)")
        
        # Decrypt
        decrypted = TokenEncryption.decrypt(encrypted)
        print(f"✓ Decryption successful")
        
        # Verify round-trip
        if decrypted == test_token:
            print(f"✓ Round-trip verification passed")
            print()
            return True
        else:
            print(f"✗ Round-trip verification failed")
            print(f"  Expected: {test_token}")
            print(f"  Got: {decrypted}")
            print()
            return False
            
    except Exception as e:
        print(f"✗ Encryption test failed: {str(e)}")
        print()
        return False


def check_integration_types():
    """Check if Gmail and Slack integration types are configured."""
    print("=" * 60)
    print("INTEGRATION TYPES CHECK")
    print("=" * 60)
    
    integration_types = ['gmail', 'slack']
    results = {}
    
    for type_name in integration_types:
        try:
            integration_type = IntegrationTypeModel.objects.get(type=type_name)
            
            print(f"\n{integration_type.name} ({type_name}):")
            print(f"  ID: {integration_type.id}")
            print(f"  Active: {'✓' if integration_type.is_active else '✗'}")
            print(f"  Category: {integration_type.category}")
            
            # Check OAuth config
            oauth_config = integration_type.oauth_config
            
            required_fields = ['client_id', 'authorization_url', 'token_url', 'scopes']
            config_complete = True
            
            for field in required_fields:
                if field in oauth_config and oauth_config[field]:
                    if field == 'client_id':
                        # Mask client ID
                        value = oauth_config[field]
                        display = f"{value[:8]}..." if len(value) > 8 else "[SET]"
                        print(f"  ✓ {field}: {display}")
                    elif field == 'scopes':
                        scopes = oauth_config[field]
                        if isinstance(scopes, list):
                            print(f"  ✓ {field}: {len(scopes)} scopes configured")
                        else:
                            print(f"  ✓ {field}: {scopes}")
                    else:
                        print(f"  ✓ {field}: {oauth_config[field]}")
                else:
                    print(f"  ✗ {field}: NOT SET")
                    config_complete = False
            
            # Check for encrypted client secret
            if 'client_secret_encrypted' in oauth_config:
                print(f"  ✓ client_secret: [ENCRYPTED]")
            else:
                print(f"  ✗ client_secret: NOT SET")
                config_complete = False
            
            results[type_name] = config_complete
            
        except IntegrationTypeModel.DoesNotExist:
            print(f"\n✗ {type_name}: NOT FOUND in database")
            print(f"  Please create this integration type in Django admin")
            results[type_name] = False
    
    print()
    return all(results.values())


def check_oauth_urls():
    """Verify OAuth URLs are HTTPS (except localhost)."""
    print("=" * 60)
    print("OAUTH URL VALIDATION")
    print("=" * 60)
    
    redirect_uri = os.getenv('OAUTH_REDIRECT_URI', '')
    
    print(f"Redirect URI: {redirect_uri}")
    
    if not redirect_uri:
        print("✗ OAUTH_REDIRECT_URI not set")
        print()
        return False
    
    # Check if HTTPS or localhost
    if redirect_uri.startswith('https://'):
        print("✓ Using HTTPS (production-ready)")
        print()
        return True
    elif redirect_uri.startswith('http://localhost') or redirect_uri.startswith('http://127.0.0.1'):
        print("⚠ Using HTTP localhost (development only)")
        print("  WARNING: Change to HTTPS for production!")
        print()
        return True
    else:
        print("✗ Invalid redirect URI")
        print("  Must use HTTPS or http://localhost for development")
        print()
        return False


def print_next_steps():
    """Print next steps for OAuth setup."""
    print("=" * 60)
    print("NEXT STEPS")
    print("=" * 60)
    print()
    print("1. Create OAuth apps in provider consoles:")
    print("   - Gmail: https://console.cloud.google.com/")
    print("   - Slack: https://api.slack.com/apps")
    print()
    print("2. Configure integration types in Django admin:")
    print("   - URL: http://localhost:8000/admin/automation/integrationtypemodel/")
    print("   - Add client_id and client_secret from providers")
    print()
    print("3. Follow the detailed setup guide:")
    print("   - docs/oauth-setup-guide.md")
    print()
    print("4. Test the installation flow:")
    print("   - Use the test results template: docs/oauth-test-results.md")
    print()


def main():
    """Run all verification checks."""
    print("\n" + "=" * 60)
    print("OAUTH SETUP VERIFICATION")
    print("=" * 60)
    print()
    
    checks = {
        'Environment Variables': check_environment_variables(),
        'Encryption': check_encryption(),
        'OAuth URLs': check_oauth_urls(),
        'Integration Types': check_integration_types(),
    }
    
    # Summary
    print("=" * 60)
    print("SUMMARY")
    print("=" * 60)
    
    for check_name, passed in checks.items():
        status = "✓ PASS" if passed else "✗ FAIL"
        print(f"{status}: {check_name}")
    
    print()
    
    all_passed = all(checks.values())
    
    if all_passed:
        print("✓ All checks passed! OAuth setup is ready for testing.")
        print()
        print_next_steps()
    else:
        print("✗ Some checks failed. Please fix the issues above.")
        print()
        print("Common issues:")
        print("  - Missing environment variables in .env file")
        print("  - Integration types not created in Django admin")
        print("  - OAuth credentials not configured")
        print()
        print("See docs/oauth-setup-guide.md for detailed instructions.")
    
    print()
    
    return 0 if all_passed else 1


if __name__ == '__main__':
    sys.exit(main())
