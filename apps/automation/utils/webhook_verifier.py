"""
Meta Webhook Signature Verification Utility

Provides secure signature verification for Meta webhook requests
using HMAC-SHA256 with constant-time comparison.

Requirements: 10.2, 17.6
"""

import hmac
import hashlib
import logging
from typing import Optional

logger = logging.getLogger(__name__)


class WebhookVerifier:
    """
    Utility for verifying Meta webhook signatures.
    
    Meta signs webhook payloads using HMAC-SHA256 with the app secret.
    This class provides secure verification using constant-time comparison
    to prevent timing attacks.
    
    Requirements: 10.2, 17.6
    """
    
    @staticmethod
    def verify_meta_signature(
        payload: bytes,
        signature: str,
        app_secret: str
    ) -> bool:
        """
        Verify Meta webhook signature using HMAC-SHA256.
        
        Uses constant-time comparison to prevent timing attacks.
        
        Args:
            payload: Raw request body as bytes
            signature: Value from X-Hub-Signature-256 header
            app_secret: Meta app secret for HMAC verification
            
        Returns:
            True if signature is valid, False otherwise
            
        Requirements: 10.2, 17.6
            
        Example:
            >>> verifier = WebhookVerifier()
            >>> is_valid = verifier.verify_meta_signature(
            ...     payload=request.body,
            ...     signature=request.headers.get('X-Hub-Signature-256'),
            ...     app_secret=settings.META_APP_SECRET
            ... )
        """
        if not signature:
            logger.warning("Missing X-Hub-Signature-256 header")
            return False
        
        if not app_secret:
            logger.error("Meta app secret not configured")
            return False
        
        # Extract signature from header (format: "sha256=<signature>")
        try:
            method, signature_value = signature.split('=', 1)
            if method != 'sha256':
                logger.warning(f"Unsupported signature method: {method}")
                return False
        except ValueError:
            logger.warning(f"Invalid signature header format: {signature}")
            return False
        
        # Compute expected signature using HMAC SHA256
        expected_signature = hmac.new(
            key=app_secret.encode('utf-8'),
            msg=payload,
            digestmod=hashlib.sha256
        ).hexdigest()
        
        # Use constant-time comparison to prevent timing attacks
        is_valid = hmac.compare_digest(signature_value, expected_signature)
        
        if not is_valid:
            logger.warning("Meta webhook signature verification failed")
        
        return is_valid
    
    @staticmethod
    def verify_token(received_token: str, expected_token: str) -> bool:
        """
        Verify Meta webhook verification token.
        
        Used during webhook setup when Meta sends a verification challenge.
        
        Args:
            received_token: Token received from Meta
            expected_token: Expected verification token from configuration
            
        Returns:
            True if tokens match, False otherwise
        """
        if not received_token or not expected_token:
            return False
        
        # Use constant-time comparison
        return hmac.compare_digest(received_token, expected_token)
