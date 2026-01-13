"""
Subscription API views.

Requirements: 3.1-3.7, 13.1, 13.3
"""

from rest_framework import status
from rest_framework.permissions import IsAuthenticated

from core.api.views import BaseAPIView
from core.api.permissions import IsVerifiedUser
from .services import SubscriptionService
from .serializers import (
    SubscriptionUpgradeSerializer,
    SubscriptionDowngradeSerializer,
)


class SubscriptionView(BaseAPIView):
    """
    GET /api/v1/subscription
    
    Get the current user's subscription.
    Requirements: 3.1
    """
    permission_classes = [IsAuthenticated, IsVerifiedUser]
    
    def get(self, request):
        subscription_service = SubscriptionService()
        subscription = subscription_service.check_and_handle_lapsed(str(request.user.id))
        features = subscription_service.get_tier_features(subscription.tier)
        
        return self.success_response(
            data={
                "id": str(subscription.id),
                "user_id": str(subscription.user_id),
                "tier": subscription.tier,
                "tier_display": subscription.get_tier_display(),
                "started_at": subscription.started_at.isoformat(),
                "expires_at": subscription.expires_at.isoformat() if subscription.expires_at else None,
                "is_active": subscription.is_active,
                "is_premium": subscription.is_premium,
                "is_lapsed": subscription.is_lapsed,
                "features": {
                    "tier_name": features.tier_name,
                    "available_models": features.available_models,
                    "has_cognitive_learning": features.has_cognitive_learning,
                    "has_voice_twin": features.has_voice_twin,
                    "has_autonomous_workflows": features.has_autonomous_workflows,
                    "has_custom_models": features.has_custom_models,
                },
            }
        )


class SubscriptionUpgradeView(BaseAPIView):
    """
    POST /api/v1/subscription/upgrade
    
    Upgrade subscription to a higher tier.
    Requirements: 3.6
    """
    permission_classes = [IsAuthenticated, IsVerifiedUser]
    
    def post(self, request):
        serializer = SubscriptionUpgradeSerializer(data=request.data)
        if not serializer.is_valid():
            return self.error_response(
                message="Validation error",
                code="VALIDATION_ERROR",
                details=serializer.errors,
                status_code=status.HTTP_400_BAD_REQUEST
            )
        
        subscription_service = SubscriptionService()
        
        try:
            subscription = subscription_service.upgrade(
                user_id=str(request.user.id),
                new_tier=serializer.validated_data['tier']
            )
            
            features = subscription_service.get_tier_features(subscription.tier)
            
            return self.success_response(
                data={
                    "id": str(subscription.id),
                    "tier": subscription.tier,
                    "tier_display": subscription.get_tier_display(),
                    "started_at": subscription.started_at.isoformat(),
                    "features": {
                        "tier_name": features.tier_name,
                        "available_models": features.available_models,
                        "has_cognitive_learning": features.has_cognitive_learning,
                        "has_voice_twin": features.has_voice_twin,
                        "has_autonomous_workflows": features.has_autonomous_workflows,
                        "has_custom_models": features.has_custom_models,
                    },
                },
                message=f"Subscription upgraded to {subscription.get_tier_display()}"
            )
            
        except ValueError as e:
            return self.error_response(
                message=str(e),
                code="UPGRADE_FAILED",
                status_code=status.HTTP_400_BAD_REQUEST
            )


class SubscriptionDowngradeView(BaseAPIView):
    """
    POST /api/v1/subscription/downgrade
    
    Downgrade subscription to a lower tier.
    Requirements: 3.6
    """
    permission_classes = [IsAuthenticated, IsVerifiedUser]
    
    def post(self, request):
        serializer = SubscriptionDowngradeSerializer(data=request.data)
        if not serializer.is_valid():
            return self.error_response(
                message="Validation error",
                code="VALIDATION_ERROR",
                details=serializer.errors,
                status_code=status.HTTP_400_BAD_REQUEST
            )
        
        subscription_service = SubscriptionService()
        
        try:
            subscription = subscription_service.downgrade(
                user_id=str(request.user.id),
                new_tier=serializer.validated_data['tier']
            )
            
            features = subscription_service.get_tier_features(subscription.tier)
            
            return self.success_response(
                data={
                    "id": str(subscription.id),
                    "tier": subscription.tier,
                    "tier_display": subscription.get_tier_display(),
                    "features": {
                        "tier_name": features.tier_name,
                        "available_models": features.available_models,
                        "has_cognitive_learning": features.has_cognitive_learning,
                        "has_voice_twin": features.has_voice_twin,
                        "has_autonomous_workflows": features.has_autonomous_workflows,
                        "has_custom_models": features.has_custom_models,
                    },
                },
                message=f"Subscription downgraded to {subscription.get_tier_display()}"
            )
            
        except ValueError as e:
            return self.error_response(
                message=str(e),
                code="DOWNGRADE_FAILED",
                status_code=status.HTTP_400_BAD_REQUEST
            )


class SubscriptionHistoryView(BaseAPIView):
    """
    GET /api/v1/subscription/history
    
    Get subscription tier change history.
    """
    permission_classes = [IsAuthenticated, IsVerifiedUser]
    
    def get(self, request):
        subscription_service = SubscriptionService()
        history = subscription_service.get_subscription_history(str(request.user.id))
        
        history_data = [
            {
                "id": str(h.id),
                "from_tier": h.from_tier,
                "to_tier": h.to_tier,
                "changed_at": h.changed_at.isoformat(),
                "reason": h.reason,
            }
            for h in history
        ]
        
        return self.success_response(
            data={
                "history": history_data,
                "total": len(history_data),
            }
        )


class FeatureAccessView(BaseAPIView):
    """
    GET /api/v1/subscription/features/<feature>
    
    Check if user has access to a specific feature.
    """
    permission_classes = [IsAuthenticated, IsVerifiedUser]
    
    def get(self, request, feature):
        subscription_service = SubscriptionService()
        has_access = subscription_service.check_feature_access(
            str(request.user.id),
            feature
        )
        
        return self.success_response(
            data={
                "feature": feature,
                "has_access": has_access,
            }
        )
