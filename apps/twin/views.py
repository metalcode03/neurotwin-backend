"""
Twin API views.

Requirements: 2.1-2.6, 13.1, 13.3
"""

from rest_framework import status
from rest_framework.permissions import IsAuthenticated

from core.api.views import BaseAPIView
from core.api.permissions import IsVerifiedUser
from .services import TwinService
from .dataclasses import AIModel, QuestionnaireResponse
from .serializers import (
    OnboardingCompleteSerializer,
    CognitiveBlendUpdateSerializer,
    OnboardingProgressSerializer,
)


class OnboardingStartView(BaseAPIView):
    """
    POST /api/v1/twin/onboarding/start
    
    Start the onboarding process and get the questionnaire.
    Requirements: 2.1
    """
    permission_classes = [IsAuthenticated, IsVerifiedUser]
    
    def post(self, request):
        twin_service = TwinService()
        result = twin_service.start_onboarding(str(request.user.id))
        
        return self.success_response(data=result)


class OnboardingCompleteView(BaseAPIView):
    """
    POST /api/v1/twin/onboarding/complete
    
    Complete onboarding and create the Twin.
    Requirements: 2.2, 2.4, 2.5, 2.6
    """
    permission_classes = [IsAuthenticated, IsVerifiedUser]
    
    def post(self, request):
        serializer = OnboardingCompleteSerializer(data=request.data)
        if not serializer.is_valid():
            return self.error_response(
                message="Validation error",
                code="VALIDATION_ERROR",
                details=serializer.errors,
                status_code=status.HTTP_400_BAD_REQUEST
            )
        
        twin_service = TwinService()
        
        try:
            # Convert responses to QuestionnaireResponse
            responses_data = serializer.validated_data['responses']
            responses = QuestionnaireResponse(
                communication_style=responses_data['communication_style'],
                decision_patterns=responses_data['decision_patterns'],
                preferences=responses_data['preferences'],
            )
            
            # Get AI model
            model = AIModel(serializer.validated_data['model'])
            
            # Create Twin
            twin = twin_service.complete_onboarding(
                user_id=str(request.user.id),
                responses=responses,
                model=model,
                cognitive_blend=serializer.validated_data['cognitive_blend']
            )
            
            return self.created_response(
                data={
                    "id": str(twin.id),
                    "user_id": str(twin.user_id),
                    "model": twin.model,
                    "cognitive_blend": twin.cognitive_blend,
                    "blend_mode": twin.blend_mode,
                    "requires_confirmation": twin.requires_confirmation,
                    "is_active": twin.is_active,
                    "created_at": twin.created_at.isoformat(),
                },
                message="Twin created successfully"
            )
            
        except ValueError as e:
            return self.error_response(
                message=str(e),
                code="ONBOARDING_FAILED",
                status_code=status.HTTP_400_BAD_REQUEST
            )


class OnboardingProgressView(BaseAPIView):
    """
    PATCH /api/v1/twin/onboarding/progress
    
    Save partial onboarding progress.
    """
    permission_classes = [IsAuthenticated, IsVerifiedUser]
    
    def patch(self, request):
        serializer = OnboardingProgressSerializer(data=request.data)
        if not serializer.is_valid():
            return self.error_response(
                message="Validation error",
                code="VALIDATION_ERROR",
                details=serializer.errors,
                status_code=status.HTTP_400_BAD_REQUEST
            )
        
        twin_service = TwinService()
        
        try:
            progress = twin_service.save_onboarding_progress(
                user_id=str(request.user.id),
                responses=serializer.validated_data.get('responses', {}),
                model=serializer.validated_data.get('model'),
                blend=serializer.validated_data.get('cognitive_blend')
            )
            
            return self.success_response(
                data={
                    "saved_responses": progress.questionnaire_responses,
                    "selected_model": progress.selected_model,
                    "selected_blend": progress.selected_blend,
                },
                message="Progress saved"
            )
            
        except ValueError as e:
            return self.error_response(
                message=str(e),
                code="SAVE_FAILED",
                status_code=status.HTTP_400_BAD_REQUEST
            )


class TwinView(BaseAPIView):
    """
    GET /api/v1/twin
    
    Get the current user's Twin.
    Requirements: 2.1
    """
    permission_classes = [IsAuthenticated, IsVerifiedUser]
    
    def get(self, request):
        twin_service = TwinService()
        twin_info = twin_service.get_twin_with_blend_info(str(request.user.id))
        
        if not twin_info:
            return self.error_response(
                message="No Twin found. Please complete onboarding first.",
                code="TWIN_NOT_FOUND",
                status_code=status.HTTP_404_NOT_FOUND
            )
        
        return self.success_response(data=twin_info)


class CognitiveBlendView(BaseAPIView):
    """
    PATCH /api/v1/twin/blend
    
    Update the cognitive blend setting.
    Requirements: 2.4, 2.5
    """
    permission_classes = [IsAuthenticated, IsVerifiedUser]
    
    def patch(self, request):
        serializer = CognitiveBlendUpdateSerializer(data=request.data)
        if not serializer.is_valid():
            return self.error_response(
                message="Validation error",
                code="VALIDATION_ERROR",
                details=serializer.errors,
                status_code=status.HTTP_400_BAD_REQUEST
            )
        
        twin_service = TwinService()
        twin = twin_service.get_twin(str(request.user.id))
        
        if not twin:
            return self.error_response(
                message="No Twin found. Please complete onboarding first.",
                code="TWIN_NOT_FOUND",
                status_code=status.HTTP_404_NOT_FOUND
            )
        
        try:
            updated_twin = twin_service.update_cognitive_blend(
                twin_id=str(twin.id),
                blend=serializer.validated_data['cognitive_blend']
            )
            
            return self.success_response(
                data={
                    "id": str(updated_twin.id),
                    "cognitive_blend": updated_twin.cognitive_blend,
                    "blend_mode": updated_twin.blend_mode,
                    "requires_confirmation": updated_twin.requires_confirmation,
                },
                message="Cognitive blend updated"
            )
            
        except ValueError as e:
            return self.error_response(
                message=str(e),
                code="UPDATE_FAILED",
                status_code=status.HTTP_400_BAD_REQUEST
            )


class TwinDeactivateView(BaseAPIView):
    """
    POST /api/v1/twin/deactivate
    
    Deactivate the Twin (kill switch).
    Requirements: 2.6
    """
    permission_classes = [IsAuthenticated, IsVerifiedUser]
    
    def post(self, request):
        twin_service = TwinService()
        twin = twin_service.get_twin(str(request.user.id))
        
        if not twin:
            return self.error_response(
                message="No Twin found",
                code="TWIN_NOT_FOUND",
                status_code=status.HTTP_404_NOT_FOUND
            )
        
        try:
            twin_service.deactivate_twin(str(twin.id))
            return self.success_response(message="Twin deactivated")
        except ValueError as e:
            return self.error_response(
                message=str(e),
                code="DEACTIVATION_FAILED",
                status_code=status.HTTP_400_BAD_REQUEST
            )


class TwinReactivateView(BaseAPIView):
    """
    POST /api/v1/twin/reactivate
    
    Reactivate a deactivated Twin.
    """
    permission_classes = [IsAuthenticated, IsVerifiedUser]
    
    def post(self, request):
        twin_service = TwinService()
        
        # Get Twin even if inactive
        from .models import Twin
        try:
            twin = Twin.objects.get(user_id=request.user.id)
        except Twin.DoesNotExist:
            return self.error_response(
                message="No Twin found",
                code="TWIN_NOT_FOUND",
                status_code=status.HTTP_404_NOT_FOUND
            )
        
        try:
            reactivated = twin_service.reactivate_twin(str(twin.id))
            return self.success_response(
                data={
                    "id": str(reactivated.id),
                    "is_active": reactivated.is_active,
                    "kill_switch_active": reactivated.kill_switch_active,
                },
                message="Twin reactivated"
            )
        except ValueError as e:
            return self.error_response(
                message=str(e),
                code="REACTIVATION_FAILED",
                status_code=status.HTTP_400_BAD_REQUEST
            )



class KillSwitchActivateView(BaseAPIView):
    """
    POST /api/v1/twin/kill-switch/activate
    
    Activate kill-switch to disable all Twin automations.
    Requirements: Safety principles
    """
    permission_classes = [IsAuthenticated, IsVerifiedUser]
    
    def post(self, request):
        from .services.kill_switch import KillSwitchService
        
        reason = request.data.get('reason', 'User-initiated')
        ip_address = self._get_client_ip(request)
        user_agent = request.META.get('HTTP_USER_AGENT', '')
        
        try:
            twin = KillSwitchService.activate_kill_switch(
                user=request.user,
                reason=reason,
                ip_address=ip_address,
                user_agent=user_agent
            )
            
            # Optionally disable all workflows
            if request.data.get('disable_workflows', False):
                disabled_count = KillSwitchService.disable_all_twin_automations(request.user)
            else:
                disabled_count = 0
            
            return self.success_response(
                data={
                    'twin_id': str(twin.id),
                    'kill_switch_active': twin.kill_switch_active,
                    'workflows_disabled': disabled_count,
                },
                message='Kill-switch activated. All Twin automations are now disabled.'
            )
            
        except ValueError as e:
            return self.error_response(
                message=str(e),
                code='ACTIVATION_FAILED',
                status_code=status.HTTP_400_BAD_REQUEST
            )
    
    def _get_client_ip(self, request) -> str:
        """Get client IP address from request."""
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[0]
        else:
            ip = request.META.get('REMOTE_ADDR')
        return ip or ''


class KillSwitchDeactivateView(BaseAPIView):
    """
    POST /api/v1/twin/kill-switch/deactivate
    
    Deactivate kill-switch to re-enable Twin automations.
    Requirements: Safety principles
    """
    permission_classes = [IsAuthenticated, IsVerifiedUser]
    
    def post(self, request):
        from .services.kill_switch import KillSwitchService
        
        reason = request.data.get('reason', 'User-initiated')
        ip_address = self._get_client_ip(request)
        user_agent = request.META.get('HTTP_USER_AGENT', '')
        
        try:
            twin = KillSwitchService.deactivate_kill_switch(
                user=request.user,
                reason=reason,
                ip_address=ip_address,
                user_agent=user_agent
            )
            
            return self.success_response(
                data={
                    'twin_id': str(twin.id),
                    'kill_switch_active': twin.kill_switch_active,
                },
                message='Kill-switch deactivated. Twin automations are now enabled.'
            )
            
        except ValueError as e:
            return self.error_response(
                message=str(e),
                code='DEACTIVATION_FAILED',
                status_code=status.HTTP_400_BAD_REQUEST
            )
    
    def _get_client_ip(self, request) -> str:
        """Get client IP address from request."""
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[0]
        else:
            ip = request.META.get('REMOTE_ADDR')
        return ip or ''


class KillSwitchStatusView(BaseAPIView):
    """
    GET /api/v1/twin/kill-switch/status
    
    Get current kill-switch status.
    Requirements: Safety principles
    """
    permission_classes = [IsAuthenticated, IsVerifiedUser]
    
    def get(self, request):
        from .services.kill_switch import KillSwitchService
        
        status_data = KillSwitchService.get_kill_switch_status(request.user)
        
        # Add blocked requests count
        blocked_count = KillSwitchService.get_blocked_requests_count(
            request.user,
            since_hours=24
        )
        status_data['blocked_requests_24h'] = blocked_count
        
        return self.success_response(data=status_data)
