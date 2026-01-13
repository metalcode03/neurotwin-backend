"""
Data classes for authentication service.

These provide structured return types for authentication operations.
"""

from dataclasses import dataclass
from typing import Optional


@dataclass
class TokenPair:
    """JWT token pair with access and refresh tokens."""
    
    access_token: str
    refresh_token: str


@dataclass
class AuthResult:
    """Result of an authentication operation."""
    
    success: bool
    user_id: Optional[str] = None
    token: Optional[str] = None  # Access token
    refresh_token: Optional[str] = None  # Refresh token
    error: Optional[str] = None
    
    @classmethod
    def success_result(
        cls, 
        user_id: str, 
        token: Optional[str] = None,
        refresh_token: Optional[str] = None
    ) -> 'AuthResult':
        """Create a successful auth result."""
        return cls(
            success=True, 
            user_id=user_id, 
            token=token,
            refresh_token=refresh_token
        )
    
    @classmethod
    def failure_result(cls, error: str) -> 'AuthResult':
        """Create a failed auth result."""
        return cls(success=False, error=error)
