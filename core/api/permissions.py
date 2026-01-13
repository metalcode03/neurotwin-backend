"""
Custom permissions for NeuroTwin REST API.

Provides permission classes for different access levels.
Requirements: 13.3 - JWT authentication for protected endpoints
"""

from rest_framework.permissions import BasePermission, IsAuthenticated
from rest_framework.request import Request
from rest_framework.views import APIView


class IsVerifiedUser(BasePermission):
    """
    Permission that requires user to have verified email.
    """
    message = "Email verification required to access this resource."
    
    def has_permission(self, request: Request, view: APIView) -> bool:
        if not request.user or not request.user.is_authenticated:
            return False
        return getattr(request.user, 'is_verified', False)


class IsSubscriptionActive(BasePermission):
    """
    Permission that requires user to have an active subscription.
    """
    message = "Active subscription required to access this resource."
    
    def has_permission(self, request: Request, view: APIView) -> bool:
        if not request.user or not request.user.is_authenticated:
            return False
        
        # Check if user has active subscription
        # This will be implemented when subscription checking is needed
        return True


class HasTwin(BasePermission):
    """
    Permission that requires user to have created a Twin.
    """
    message = "You must create a Twin to access this resource."
    
    def has_permission(self, request: Request, view: APIView) -> bool:
        if not request.user or not request.user.is_authenticated:
            return False
        
        # Import here to avoid circular imports
        from apps.twin.models import Twin
        return Twin.objects.filter(user_id=request.user.id, is_active=True).exists()


class HasFeatureAccess(BasePermission):
    """
    Base permission for feature-based access control.
    
    Subclass and set `required_feature` to check specific features.
    """
    required_feature: str = None
    message = "Your subscription does not include access to this feature."
    
    def has_permission(self, request: Request, view: APIView) -> bool:
        if not request.user or not request.user.is_authenticated:
            return False
        
        if not self.required_feature:
            return True
        
        # Import here to avoid circular imports
        from apps.subscription.services import SubscriptionService
        
        service = SubscriptionService()
        return service.check_feature_access(str(request.user.id), self.required_feature)


class HasVoiceTwinAccess(HasFeatureAccess):
    """Permission for Voice Twin features (Twin+ and Executive tiers)."""
    required_feature = "voice_twin"
    message = "Voice Twin is only available on Twin+ and Executive tiers."


class HasAutonomousWorkflowAccess(HasFeatureAccess):
    """Permission for autonomous workflow features (Executive tier)."""
    required_feature = "autonomous_workflows"
    message = "Autonomous workflows are only available on Executive tier."
