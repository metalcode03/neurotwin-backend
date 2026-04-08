"""
Custom exceptions for credit-based AI architecture.

Defines exceptions for credit validation, brain mode restrictions,
and model availability errors.

Requirements: 4.1, 5.10, 6.7, 7.9, 19.1-19.4
"""

from typing import Optional, List


class InsufficientCreditsError(Exception):
    """
    Raised when user has insufficient credits to complete a request.
    
    Requirements: 4.1, 4.2, 19.1, 19.2
    """
    
    def __init__(
        self,
        remaining_credits: int,
        required_credits: int,
        message: Optional[str] = None
    ):
        self.remaining_credits = remaining_credits
        self.required_credits = required_credits
        self.message = message or (
            f"Insufficient credits. Required: {required_credits}, "
            f"Remaining: {remaining_credits}"
        )
        super().__init__(self.message)


class BrainModeRestrictedError(Exception):
    """
    Raised when user's subscription tier does not allow requested brain mode.
    
    Requirements: 5.10, 19.3
    """
    
    def __init__(
        self,
        requested_mode: str,
        current_tier: str,
        required_tier: str,
        message: Optional[str] = None
    ):
        self.requested_mode = requested_mode
        self.current_tier = current_tier
        self.required_tier = required_tier
        self.message = message or (
            f"Brain mode '{requested_mode}' requires {required_tier} tier or higher. "
            f"Current tier: {current_tier}"
        )
        super().__init__(self.message)


class ModelUnavailableError(Exception):
    """
    Raised when all models (primary and fallbacks) are unavailable.
    
    Requirements: 6.7, 19.4
    """
    
    def __init__(
        self,
        attempted_models: List[str],
        message: Optional[str] = None
    ):
        self.attempted_models = attempted_models
        self.message = message or (
            f"All models unavailable. Attempted: {', '.join(attempted_models)}"
        )
        super().__init__(self.message)


class CerebrasAPIError(Exception):
    """
    Raised when Cerebras API returns an error.
    
    Requirements: 7.9
    """
    
    def __init__(self, message: str, status_code: Optional[int] = None):
        self.status_code = status_code
        super().__init__(message)


class CerebrasTimeoutError(CerebrasAPIError):
    """
    Raised when Cerebras API request times out.
    
    Requirements: 7.9
    """
    
    def __init__(self, message: str = "Cerebras API request timed out"):
        super().__init__(message, status_code=None)


class CerebrasAuthError(CerebrasAPIError):
    """
    Raised when Cerebras API authentication fails.
    
    Requirements: 7.9
    """
    
    def __init__(self, message: str = "Cerebras API authentication failed"):
        super().__init__(message, status_code=401)


class ProviderAPIError(Exception):
    """
    Generic provider API error for all AI providers.
    
    Base exception for provider-specific errors.
    Requirements: 8.5
    """
    
    def __init__(self, message: str, status_code: Optional[int] = None):
        self.status_code = status_code
        super().__init__(message)


class ProviderTimeoutError(ProviderAPIError):
    """
    Raised when provider API request times out.
    
    Requirements: 8.5
    """
    
    def __init__(self, message: str = "Provider API request timed out"):
        super().__init__(message, status_code=None)


class ProviderAuthError(ProviderAPIError):
    """
    Raised when provider API authentication fails.
    
    Requirements: 8.5
    """
    
    def __init__(self, message: str = "Provider API authentication failed"):
        super().__init__(message, status_code=401)


class ProviderRateLimitError(ProviderAPIError):
    """
    Raised when provider API rate limit is exceeded.
    
    Requirements: 8.5
    """
    
    def __init__(self, message: str = "Provider API rate limit exceeded"):
        super().__init__(message, status_code=429)
