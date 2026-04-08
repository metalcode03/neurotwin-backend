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



class TwinChatView(BaseAPIView):
    """
    POST /api/v1/twin/chat
    
    Send chat message to Twin with Brain mode integration.
    
    Requirements: 15.1, 15.2, 9.11, 4.1, 4.2, 4.3, 5.10, 19.1, 19.2, 19.3
    """
    permission_classes = [IsAuthenticated, IsVerifiedUser]
    
    def post(self, request):
        from apps.credits.ai_service import AIService
        from apps.credits.enums import BrainMode, OperationType
        from apps.credits.exceptions import (
            InsufficientCreditsError,
            BrainModeRestrictedError,
            ModelUnavailableError,
        )
        from apps.credits.services import CreditManager
        from apps.credits.models import UserCredits
        from django.core.cache import cache
        from datetime import date
        
        # Import serializers
        from .serializers import TwinChatRequestSerializer
        
        # Validate request
        serializer = TwinChatRequestSerializer(
            data=request.data,
            context={'request': request}
        )
        if not serializer.is_valid():
            return self.error_response(
                message="Validation error",
                code="VALIDATION_ERROR",
                details=serializer.errors,
                status_code=status.HTTP_400_BAD_REQUEST
            )
        
        # Extract validated data
        message = serializer.validated_data['message']
        brain_mode = serializer.validated_data.get('brain_mode')
        operation_type = serializer.validated_data.get('operation_type', 'long_response')
        context = serializer.validated_data.get('context', {})
        
        # If brain_mode not provided, use user's preference from settings
        if brain_mode is None:
            # Try to get from user settings (future implementation)
            # For now, default to 'brain'
            brain_mode = 'brain'
        
        try:
            # Initialize AIService
            ai_service = AIService()
            
            # Process request through AIService
            # AIService will internally:
            # - Load CSM profile and cognitive_blend from Twin
            # - Validate tier access
            # - Check and reset credits if needed
            # - Estimate and validate credits
            # - Route to appropriate model
            # - Execute request
            # - Deduct credits
            # - Log request
            ai_response = ai_service.process_request(
                user_id=request.user.id,
                prompt=message,
                brain_mode=BrainMode.from_string(brain_mode),
                operation_type=OperationType.from_string(operation_type),
                context=context,
            )
            
            # Get updated credit balance
            credit_manager = CreditManager()
            
            # Invalidate credit cache to force fresh read
            cache_key = f"credit_balance:{request.user.id}"
            cache.delete(cache_key)
            
            # Get fresh balance
            balance = credit_manager.get_balance(request.user.id)
            
            # Build response
            response_data = {
                'response': ai_response.content,
                'metadata': {
                    'brain_mode': ai_response.brain_mode,
                    'model_used': ai_response.model_used,
                    'tokens_used': ai_response.tokens_used,
                    'credits_consumed': ai_response.credits_consumed,
                    'latency_ms': ai_response.latency_ms,
                    'request_id': str(ai_response.request_id),
                },
                'credits': {
                    'remaining': balance['remaining_credits'],
                    'consumed': ai_response.credits_consumed,
                }
            }
            
            return self.success_response(
                data=response_data,
                message="Response generated successfully"
            )
        
        except InsufficientCreditsError as e:
            # Handle insufficient credits (402 Payment Required)
            # Requirements: 4.1, 4.2, 4.3, 19.1, 19.2
            
            # Get next reset date
            try:
                user_credits = UserCredits.objects.get(user_id=request.user.id)
                last_reset = user_credits.last_reset_date
                if last_reset.month == 12:
                    next_reset = date(last_reset.year + 1, 1, 1)
                else:
                    next_reset = date(last_reset.year, last_reset.month + 1, 1)
                next_reset_str = next_reset.isoformat()
            except UserCredits.DoesNotExist:
                next_reset_str = None
            
            return self.error_response(
                message="You have insufficient credits to complete this request",
                code="INSUFFICIENT_CREDITS",
                details={
                    'required_credits': e.required_credits,
                    'remaining_credits': e.remaining_credits,
                    'next_reset_date': next_reset_str,
                    'upgrade_url': '/dashboard/subscription',
                },
                status_code=402  # Payment Required
            )
        
        except BrainModeRestrictedError as e:
            # Handle brain mode restricted (403 Forbidden)
            # Requirements: 5.10, 19.3
            
            return self.error_response(
                message=f"Brain {e.requested_mode.replace('_', ' ').title()} mode requires {e.required_tier} tier or higher",
                code="BRAIN_MODE_RESTRICTED",
                details={
                    'requested_mode': e.requested_mode,
                    'current_tier': e.current_tier,
                    'required_tier': e.required_tier,
                    'upgrade_url': '/dashboard/subscription',
                },
                status_code=status.HTTP_403_FORBIDDEN
            )
        
        except ModelUnavailableError as e:
            # Handle model unavailable (503 Service Unavailable)
            
            return self.error_response(
                message="AI service is temporarily unavailable. Please try again later.",
                code="MODEL_UNAVAILABLE",
                details={
                    'attempted_models': e.attempted_models,
                },
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE
            )
        
        except Exception as e:
            # Handle unexpected errors
            import logging
            logger = logging.getLogger(__name__)
            logger.error(
                f"Unexpected error in TwinChatView for user {request.user.id}: {e}",
                exc_info=True
            )
            
            return self.error_response(
                message="An unexpected error occurred while processing your request",
                code="INTERNAL_ERROR",
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class TwinGenerateView(BaseAPIView):
    """
    POST /api/v1/twin/generate
    
    Generate AI response for automation workflows.
    
    Requirements: 9.1-9.11
    """
    permission_classes = [IsAuthenticated, IsVerifiedUser]
    
    def post(self, request):
        from apps.credits.ai_service import AIService
        from apps.credits.enums import BrainMode, OperationType
        from apps.credits.exceptions import (
            InsufficientCreditsError,
            BrainModeRestrictedError,
            ModelUnavailableError,
        )
        from apps.credits.services import CreditManager
        from apps.credits.models import UserCredits
        from django.core.cache import cache
        from datetime import date
        
        # Import serializers
        from .serializers import TwinGenerateRequestSerializer
        
        # Validate request
        serializer = TwinGenerateRequestSerializer(
            data=request.data,
            context={'request': request}
        )
        if not serializer.is_valid():
            return self.error_response(
                message="Validation error",
                code="VALIDATION_ERROR",
                details=serializer.errors,
                status_code=status.HTTP_400_BAD_REQUEST
            )
        
        # Extract validated data
        prompt = serializer.validated_data['prompt']
        brain_mode = serializer.validated_data.get('brain_mode')
        operation_type = serializer.validated_data.get('operation_type', 'automation')
        max_tokens = serializer.validated_data.get('max_tokens', 1000)
        temperature = serializer.validated_data.get('temperature', 0.7)
        context = serializer.validated_data.get('context', {})
        
        # If brain_mode not provided, use user's preference
        if brain_mode is None:
            brain_mode = 'brain'
        
        try:
            # Initialize AIService
            ai_service = AIService()
            
            # Process request through AIService
            ai_response = ai_service.process_request(
                user_id=request.user.id,
                prompt=prompt,
                brain_mode=BrainMode.from_string(brain_mode),
                operation_type=OperationType.from_string(operation_type),
                context=context,
                max_tokens=max_tokens,
                temperature=temperature,
            )
            
            # Get updated credit balance
            credit_manager = CreditManager()
            
            # Invalidate credit cache
            cache_key = f"credit_balance:{request.user.id}"
            cache.delete(cache_key)
            
            # Get fresh balance
            balance = credit_manager.get_balance(request.user.id)
            
            # Build response (same format as chat endpoint)
            response_data = {
                'response': ai_response.content,
                'metadata': {
                    'brain_mode': ai_response.brain_mode,
                    'model_used': ai_response.model_used,
                    'tokens_used': ai_response.tokens_used,
                    'credits_consumed': ai_response.credits_consumed,
                    'latency_ms': ai_response.latency_ms,
                    'request_id': str(ai_response.request_id),
                },
                'credits': {
                    'remaining': balance['remaining_credits'],
                    'consumed': ai_response.credits_consumed,
                }
            }
            
            return self.success_response(
                data=response_data,
                message="Response generated successfully"
            )
        
        except InsufficientCreditsError as e:
            # Handle insufficient credits (402 Payment Required)
            
            try:
                user_credits = UserCredits.objects.get(user_id=request.user.id)
                last_reset = user_credits.last_reset_date
                if last_reset.month == 12:
                    next_reset = date(last_reset.year + 1, 1, 1)
                else:
                    next_reset = date(last_reset.year, last_reset.month + 1, 1)
                next_reset_str = next_reset.isoformat()
            except UserCredits.DoesNotExist:
                next_reset_str = None
            
            return self.error_response(
                message="You have insufficient credits to complete this request",
                code="INSUFFICIENT_CREDITS",
                details={
                    'required_credits': e.required_credits,
                    'remaining_credits': e.remaining_credits,
                    'next_reset_date': next_reset_str,
                    'upgrade_url': '/dashboard/subscription',
                },
                status_code=402  # Payment Required
            )
        
        except BrainModeRestrictedError as e:
            # Handle brain mode restricted (403 Forbidden)
            
            return self.error_response(
                message=f"Brain {e.requested_mode.replace('_', ' ').title()} mode requires {e.required_tier} tier or higher",
                code="BRAIN_MODE_RESTRICTED",
                details={
                    'requested_mode': e.requested_mode,
                    'current_tier': e.current_tier,
                    'required_tier': e.required_tier,
                    'upgrade_url': '/dashboard/subscription',
                },
                status_code=status.HTTP_403_FORBIDDEN
            )
        
        except ModelUnavailableError as e:
            # Handle model unavailable (503 Service Unavailable)
            
            return self.error_response(
                message="AI service is temporarily unavailable. Please try again later.",
                code="MODEL_UNAVAILABLE",
                details={
                    'attempted_models': e.attempted_models,
                },
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE
            )
        
        except Exception as e:
            # Handle unexpected errors
            import logging
            logger = logging.getLogger(__name__)
            logger.error(
                f"Unexpected error in TwinGenerateView for user {request.user.id}: {e}",
                exc_info=True
            )
            
            return self.error_response(
                message="An unexpected error occurred while processing your request",
                code="INTERNAL_ERROR",
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
