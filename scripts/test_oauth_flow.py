#!/usr/bin/env python
"""
OAuth Flow Testing Script

Helper script for Task 19 checkpoint testing.
Provides utilities to test OAuth flow components.

Usage:
    uv run python scripts/test_oauth_flow.py --help
"""

import argparse
import asyncio
import base64
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

import django
django.setup()

from django.contrib.auth import get_user_model
from apps.automation.models import (
    InstallationSession,
    Integration,
    IntegrationType,
)
from apps.automation.services.installation import InstallationService
from apps.automation.utils.encryption import TokenEncryption

User = get_user_model()


def test_token_encryption():
    """Test token encryption round-trip."""
    print("Testing token encryption...")
    
    test_tokens = [
        "simple_token",
        "token_with_special_chars!@#$%^&*()",
        "very_long_token_" * 50,
    ]
    
    for token in test_tokens:
        encrypted = TokenEncryption.encrypt(token)
        decrypted = TokenEncryption.decrypt(encrypted)
        
        if decrypted == token:
            print(f"  ✅ Token encryption/decryption works: {token[:20]}...")
        else:
            print(f"  ❌ Token encryption/decryption FAILED: {token[:20]}...")
            return False
    
    print("  ✅ All token encryption tests passed\n")
    return True


def test_installation_session_creation(user_email: str, integration_type: str):
    """Test installation session creation."""
    print(f"Testing installation session creation...")
    
    try:
        user = User.objects.get(email=user_email)
    except User.DoesNotExist:
        print(f"  ❌ User not found: {user_email}")
        return False
    
    try:
        int_type = IntegrationType.objects.get(type=integration_type)
    except IntegrationType.DoesNotExist:
        print(f"  ❌ Integration type not found: {integration_type}")
        return False
    
    try:
        session = InstallationService.start_installation(
            user=user,
            integration_type_id=int_type.id
        )
        
        print(f"  ✅ Session created: {session.id}")
        print(f"     Status: {session.status}")
        print(f"     OAuth state: {session.oauth_state[:20]}...")
        print(f"     Progress: {session.progress}%\n")
        
        return True
    except Exception as e:
        print(f"  ❌ Session creation failed: {e}\n")
        return False


def test_oauth_url_generation(session_id: str):
    """Test OAuth URL generation."""
    print(f"Testing OAuth URL generation...")
    
    try:
        session = InstallationSession.objects.get(id=session_id)
    except InstallationSession.DoesNotExist:
        print(f"  ❌ Session not found: {session_id}")
        return False
    
    try:
        oauth_url = InstallationService.get_oauth_authorization_url(
            session_id=session.id
        )
        
        print(f"  ✅ OAuth URL generated:")
        print(f"     {oauth_url[:100]}...")
        
        # Verify URL components
        checks = [
            ('client_id' in oauth_url, 'client_id parameter'),
            ('state' in oauth_url, 'state parameter'),
            ('scope' in oauth_url, 'scope parameter'),
            ('redirect_uri' in oauth_url, 'redirect_uri parameter'),
        ]
        
        for check, name in checks:
            if check:
                print(f"     ✅ {name} present")
            else:
                print(f"     ❌ {name} MISSING")
        
        print()
        return True
    except Exception as e:
        print(f"  ❌ OAuth URL generation failed: {e}\n")
        return False


def list_installations(user_email: str):
    """List user's installations."""
    print(f"Listing installations for {user_email}...")
    
    try:
        user = User.objects.get(email=user_email)
    except User.DoesNotExist:
        print(f"  ❌ User not found: {user_email}")
        return
    
    integrations = Integration.objects.filter(user=user)
    
    if not integrations.exists():
        print("  No installations found\n")
        return
    
    for integration in integrations:
        print(f"\n  Integration: {integration.integration_type.name}")
        print(f"    Type: {integration.integration_type.type}")
        print(f"    Active: {integration.is_active}")
        print(f"    Has access token: {bool(integration.oauth_token_encrypted)}")
        print(f"    Has refresh token: {bool(integration.refresh_token_encrypted)}")
        print(f"    Created: {integration.created_at}")
    
    print()


def list_sessions(user_email: str):
    """List user's installation sessions."""
    print(f"Listing installation sessions for {user_email}...")
    
    try:
        user = User.objects.get(email=user_email)
    except User.DoesNotExist:
        print(f"  ❌ User not found: {user_email}")
        return
    
    sessions = InstallationSession.objects.filter(user=user).order_by('-created_at')
    
    if not sessions.exists():
        print("  No sessions found\n")
        return
    
    for session in sessions[:10]:  # Show last 10
        print(f"\n  Session: {session.id}")
        print(f"    Integration: {session.integration_type.name}")
        print(f"    Status: {session.status}")
        print(f"    Progress: {session.progress}%")
        print(f"    Created: {session.created_at}")
        if session.error_message:
            print(f"    Error: {session.error_message}")
    
    print()


def verify_token_encryption_in_db(user_email: str, integration_type: str):
    """Verify tokens are encrypted in database."""
    print(f"Verifying token encryption in database...")
    
    try:
        user = User.objects.get(email=user_email)
        int_type = IntegrationType.objects.get(type=integration_type)
        integration = Integration.objects.get(user=user, integration_type=int_type)
    except Exception as e:
        print(f"  ❌ Could not find integration: {e}")
        return False
    
    # Check encrypted field
    if not integration.oauth_token_encrypted:
        print("  ❌ No access token stored")
        return False
    
    print(f"  ✅ Access token encrypted (binary data)")
    print(f"     Length: {len(integration.oauth_token_encrypted)} bytes")
    print(f"     First 20 bytes: {integration.oauth_token_encrypted[:20]}")
    
    # Verify decryption works
    try:
        decrypted = TokenEncryption.decrypt(integration.oauth_token_encrypted)
        print(f"  ✅ Token decrypts successfully")
        print(f"     Decrypted length: {len(decrypted)} chars")
    except Exception as e:
        print(f"  ❌ Decryption failed: {e}")
        return False
    
    print()
    return True


def cleanup_test_data(user_email: str):
    """Clean up test installation data."""
    print(f"Cleaning up test data for {user_email}...")
    
    try:
        user = User.objects.get(email=user_email)
    except User.DoesNotExist:
        print(f"  ❌ User not found: {user_email}")
        return
    
    # Delete sessions
    session_count = InstallationSession.objects.filter(user=user).count()
    InstallationSession.objects.filter(user=user).delete()
    print(f"  ✅ Deleted {session_count} installation sessions")
    
    # Delete integrations
    integration_count = Integration.objects.filter(user=user).count()
    Integration.objects.filter(user=user).delete()
    print(f"  ✅ Deleted {integration_count} integrations")
    
    print()


def main():
    parser = argparse.ArgumentParser(
        description='OAuth Flow Testing Script'
    )
    
    subparsers = parser.add_subparsers(dest='command', help='Command to run')
    
    # Test encryption
    subparsers.add_parser(
        'test-encryption',
        help='Test token encryption/decryption'
    )
    
    # Create session
    create_parser = subparsers.add_parser(
        'create-session',
        help='Create installation session'
    )
    create_parser.add_argument('--user', required=True, help='User email')
    create_parser.add_argument('--type', required=True, help='Integration type')
    
    # Generate OAuth URL
    oauth_parser = subparsers.add_parser(
        'generate-oauth-url',
        help='Generate OAuth authorization URL'
    )
    oauth_parser.add_argument('--session', required=True, help='Session ID')
    
    # List installations
    list_inst_parser = subparsers.add_parser(
        'list-installations',
        help='List user installations'
    )
    list_inst_parser.add_argument('--user', required=True, help='User email')
    
    # List sessions
    list_sess_parser = subparsers.add_parser(
        'list-sessions',
        help='List installation sessions'
    )
    list_sess_parser.add_argument('--user', required=True, help='User email')
    
    # Verify encryption
    verify_parser = subparsers.add_parser(
        'verify-encryption',
        help='Verify token encryption in database'
    )
    verify_parser.add_argument('--user', required=True, help='User email')
    verify_parser.add_argument('--type', required=True, help='Integration type')
    
    # Cleanup
    cleanup_parser = subparsers.add_parser(
        'cleanup',
        help='Clean up test data'
    )
    cleanup_parser.add_argument('--user', required=True, help='User email')
    
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        return
    
    # Execute command
    if args.command == 'test-encryption':
        test_token_encryption()
    
    elif args.command == 'create-session':
        test_installation_session_creation(args.user, args.type)
    
    elif args.command == 'generate-oauth-url':
        test_oauth_url_generation(args.session)
    
    elif args.command == 'list-installations':
        list_installations(args.user)
    
    elif args.command == 'list-sessions':
        list_sessions(args.user)
    
    elif args.command == 'verify-encryption':
        verify_token_encryption_in_db(args.user, args.type)
    
    elif args.command == 'cleanup':
        cleanup_test_data(args.user)


if __name__ == '__main__':
    main()
