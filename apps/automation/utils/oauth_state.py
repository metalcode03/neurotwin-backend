"""
OAuth state generation and validation utilities.

Provides cryptographically secure state generation for CSRF protection
during OAuth authorization flows.

Requirements: 18.4
"""

import secrets
import logging
from datetime import timedelta
from typing import Optional

from django.utils import timezone
from django.core.exceptions import ValidationError


logger = logging.getLogger(__name__)


class OAuthStateManager:
    """
    Manager for OAuth state generation and validation.
    
    Generates cryptographically random state parameters and validates
    them during OAuth callbacks to prevent CSRF attacks.
    
    Requirements: 18.4
    - Generate cryptographically random state (32 bytes)
    - Store state in InstallationSession with 10-minute expiry
    - Validate state on callback to prevent CSRF
    """
    
    # State expiry time (10 minutes)
    STATE_EXPIRY_MINUTES = 10
    
    @staticmethod
    def generate_state() -> str:
        """
        Generate a cryptographically secure random state parameter.
        
        Uses secrets module to generate 32 bytes of random data,
        encoded as URL-safe base64 string.
        
        Returns:
            str: Random state string (43 characters)
            
        Requirements: 18.4
        """
        # Generate 32 random bytes
        random_bytes = secrets.token_bytes(32)
        
        # Encode as URL-safe base64 (without padding)
        state = secrets.token_urlsafe(32)
        
        logger.debug(f"Generated OAuth state: {state[:8]}...")
        
        return state
    
    @staticmethod
    def validate_state(
        session,
        provided_state: str
    ) -> tuple[bool, Optional[str]]:
        """
        Validate OAuth state parameter against session.
        
        Checks:
        1. State matches session's oauth_state
        2. Session is not expired (< 10 minutes old)
        3. Session is in appropriate status
        
        Args:
            session: InstallationSession instance
            provided_state: State parameter from OAuth callback
            
        Returns:
            tuple: (is_valid, error_message)
                - is_valid: True if state is valid
                - error_message: Error description if invalid, None if valid
                
        Requirements: 18.4
        """
        # Check if state matches
        if not secrets.compare_digest(session.oauth_state, provided_state):
            logger.warning(
                f"OAuth state mismatch for session {session.id}. "
                f"Expected: {session.oauth_state[:8]}..., "
                f"Got: {provided_state[:8]}..."
            )
            return False, "Invalid state parameter (CSRF check failed)"
        
        # Check if session is expired
        if session.is_expired:
            age_minutes = (timezone.now() - session.created_at).total_seconds() / 60
            logger.warning(
                f"OAuth state expired for session {session.id}. "
                f"Age: {age_minutes:.1f} minutes"
            )
            return False, "OAuth session expired. Please try again."
        
        # Check session status
        from apps.automation.models import InstallationStatus
        
        if session.status == InstallationStatus.COMPLETED:
            logger.warning(
                f"OAuth state used for already completed session {session.id}"
            )
            return False, "Installation already completed"
        
        if session.status == InstallationStatus.FAILED:
            logger.warning(
                f"OAuth state used for failed session {session.id}"
            )
            return False, "Installation failed. Please start a new installation."
        
        logger.info(f"OAuth state validated successfully for session {session.id}")
        return True, None
    
    @staticmethod
    def is_state_expired(created_at) -> bool:
        """
        Check if a state is expired based on creation time.
        
        Args:
            created_at: DateTime when state was created
            
        Returns:
            bool: True if expired (> 10 minutes old)
        """
        expiry_time = created_at + timedelta(minutes=OAuthStateManager.STATE_EXPIRY_MINUTES)
        return timezone.now() > expiry_time
    
    @staticmethod
    def create_session_with_state(user, integration_type):
        """
        Create InstallationSession with generated state.
        
        Args:
            user: User instance
            integration_type: IntegrationType instance
            
        Returns:
            InstallationSession: Created session with oauth_state
        """
        from apps.automation.models import InstallationSession, InstallationStatus
        
        state = OAuthStateManager.generate_state()
        
        session = InstallationSession.objects.create(
            user=user,
            integration_type=integration_type,
            status=InstallationStatus.DOWNLOADING,
            oauth_state=state,
            progress=0
        )
        
        logger.info(
            f"Created installation session {session.id} for user {user.id}, "
            f"integration_type {integration_type.type}"
        )
        
        return session
    
    @staticmethod
    def validate_and_get_session(session_id: str, state: str):
        """
        Validate state and retrieve session in one operation.
        
        Args:
            session_id: UUID of installation session
            state: State parameter from OAuth callback
            
        Returns:
            InstallationSession: Valid session instance
            
        Raises:
            ValidationError: If session not found or state invalid
        """
        from apps.automation.models import InstallationSession
        
        try:
            session = InstallationSession.objects.get(id=session_id)
        except InstallationSession.DoesNotExist:
            logger.error(f"Installation session not found: {session_id}")
            raise ValidationError("Installation session not found")
        
        is_valid, error_message = OAuthStateManager.validate_state(session, state)
        
        if not is_valid:
            raise ValidationError(error_message)
        
        return session
