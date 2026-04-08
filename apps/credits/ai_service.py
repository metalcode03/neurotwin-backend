"""
AI Service orchestration for NeuroTwin platform.

Coordinates credit validation, model routing, CSM profile loading,
and request execution through provider abstraction layer.

Requirements: 9.1, 9.2, 9.3, 9.4, 9.5, 9.6, 9.7, 9.8, 9.9, 9.10, 9.11, 19.1-19.4
"""

import logging
import time
import uuid
from typing import Dict, Any, Optional, List
from django.db import transaction

from apps.credits.services import CreditManager
from apps.credits.routing import get_model_router
from apps.credits.providers.registry import get_registry
from apps.credits.models import AIRequestLog
from apps.credits.enums import BrainMode, OperationType
from apps.credits.constants import BRAIN_MODE_TIER_REQUIREMENTS
from apps.credits.exceptions import (
    InsufficientCreditsError,
    BrainModeRestrictedError,
    ModelUnavailableError,
    ProviderAPIError,
)
from apps.credits.dataclasses import ProviderResponse
from apps.credits.metrics import (
    ai_requests_total,
    ai_request_tokens_total,
    ai_request_latency_seconds,
)
from apps.twin.services import TwinService
from apps.csm.services import CSMService


logger = logging.getLogger(__name__)


class AIResponse:
    """
    Response from AIService.process_request().
    
    Contains AI-generated content and metadata about the request.
    """
    
    def __init__(
        self,
        content: str,
        tokens_used: int,
        model_used: str,
        credits_consumed: int,
        latency_ms: int,
        request_id: uuid.UUID,
        brain_mode: str,
        operation_type: str,
        cognitive_blend_value: Optional[int] = None,
    ):
        self.content = content
        self.tokens_used = tokens_used
        self.model_used = model_used
        self.credits_consumed = credits_consumed
        self.latency_ms = latency_ms
        self.request_id = request_id
        self.brain_mode = brain_mode
        self.operation_type = operation_type
        self.cognitive_blend_value = cognitive_blend_value
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for API response."""
        return {
            'content': self.content,
            'metadata': {
                'tokens_used': self.tokens_used,
                'model_used': self.model_used,
                'credits_consumed': self.credits_consumed,
                'latency_ms': self.latency_ms,
                'request_id': str(self.request_id),
                'brain_mode': self.brain_mode,
                'operation_type': self.operation_type,
                'cognitive_blend_value': self.cognitive_blend_value,
            }
        }


class AIService:
    """
    Orchestrates AI request processing with credit validation and model routing.
    
    Requirements: 9.1, 9.2
    
    Execution Flow:
    1. Validate user's subscription tier allows requested brain_mode
    2. Check and perform monthly reset if needed
    3. Estimate credit cost
    4. Validate sufficient credits
    5. Select model via ModelRouter
    6. Load CSM profile and cognitive_blend from Twin
    7. Execute request through provider
    8. Deduct actual credits based on token usage
    9. Create usage and request logs
    10. Return response with metadata
    """
    
    def __init__(self):
        """Initialize AIService with dependencies."""
        self.credit_manager = CreditManager()
        self.model_router = get_model_router()
        self.provider_registry = get_registry()
        self.twin_service = TwinService()
        self.csm_service = CSMService()
    
    def process_request(
        self,
        user_id: int,
        prompt: str,
        brain_mode: BrainMode,
        operation_type: OperationType,
        context: Optional[Dict[str, Any]] = None,
        max_tokens: int = 1000,
        temperature: float = 0.7,
    ) -> AIResponse:
        """
        Process AI request with full orchestration.
        
        Requirements: 9.1, 9.2, 9.3, 9.4, 9.5, 9.6, 9.7, 9.8, 9.9, 9.10, 9.11
        
        Args:
            user_id: ID of the user making the request
            prompt: User's prompt/message
            brain_mode: Brain intelligence level (brain, brain_pro, brain_gen)
            operation_type: Type of operation (simple_response, long_response, etc.)
            context: Optional context dictionary
            max_tokens: Maximum tokens for response
            temperature: Temperature for response generation
        
        Returns:
            AIResponse with content and metadata
        
        Raises:
            InsufficientCreditsError: If user has insufficient credits
            BrainModeRestrictedError: If user's tier doesn't allow brain_mode
            ModelUnavailableError: If all models fail
            ProviderAPIError: If provider errors occur
        """
        start_time = time.time()
        request_id = uuid.uuid4()
        context = context or {}
        
        # Convert enums to strings for logging and storage
        brain_mode_str = brain_mode.value if isinstance(brain_mode, BrainMode) else brain_mode
        operation_type_str = operation_type.value if isinstance(operation_type, OperationType) else operation_type
        
        logger.info(
            f"[AIService] Processing request {request_id} for user {user_id}: "
            f"brain_mode={brain_mode_str}, operation_type={operation_type_str}"
        )
        
        try:
            # Step 1: Validate brain mode access
            self.validate_brain_mode_access(user_id, brain_mode)
            
            # Step 2: Check and perform monthly reset if needed
            self.credit_manager.check_and_reset_if_needed(user_id)
            
            # Step 3: Estimate credit cost
            estimated_tokens = context.get('estimated_tokens', 500)
            estimated_cost = self.credit_manager.estimate_cost(
                operation_type_str,
                brain_mode_str,
                estimated_tokens
            )
            
            # Step 4: Validate sufficient credits
            if not self.credit_manager.check_sufficient_credits(user_id, estimated_cost):
                balance = self.credit_manager.get_balance(user_id)
                raise InsufficientCreditsError(
                    remaining_credits=balance['remaining_credits'],
                    required_credits=estimated_cost
                )
            
            # Step 5: Route to appropriate model
            model_selection = self.model_router.select_model(brain_mode, operation_type)
            self.model_router.log_routing_decision(model_selection, user_id)
            
            # Step 6: Load CSM profile and cognitive blend from Twin
            twin = self.twin_service.get_twin(str(user_id))
            cognitive_blend_value = None
            system_prompt = None
            
            if twin:
                cognitive_blend_value = twin.cognitive_blend
                
                # Load CSM profile and build system prompt if blend > 0
                if cognitive_blend_value > 0 and twin.csm_profile:
                    try:
                        blended_profile = self.csm_service.apply_blend(
                            twin.csm_profile,
                            cognitive_blend_value
                        )
                        system_prompt = self._build_system_prompt_from_profile(
                            blended_profile,
                            cognitive_blend_value
                        )
                        logger.info(
                            f"[AIService] Applied CSM profile with blend {cognitive_blend_value}% "
                            f"for user {user_id}"
                        )
                    except Exception as e:
                        logger.warning(
                            f"[AIService] Failed to load CSM profile for user {user_id}: {e}. "
                            f"Proceeding without personality overlay."
                        )
                        system_prompt = None
            
            # Step 7: Build messages array for provider
            messages = []
            if system_prompt:
                messages.append({"role": "system", "content": system_prompt})
            messages.append({"role": "user", "content": prompt})
            
            # Step 8: Execute request through provider with fallback logic
            provider_response = self._execute_with_fallback(
                model_selection,
                messages,
                max_tokens,
                temperature
            )
            
            # Calculate actual cost based on tokens used
            actual_cost = self.credit_manager.estimate_cost(
                operation_type_str,
                brain_mode_str,
                provider_response.tokens_used
            )
            
            # Step 8: Deduct credits
            self.credit_manager.deduct_credits(
                user_id=user_id,
                amount=actual_cost,
                metadata={
                    'operation_type': operation_type_str,
                    'brain_mode': brain_mode_str,
                    'model_used': provider_response.model_used,
                    'request_id': request_id,
                }
            )
            
            # Calculate latency
            latency_ms = int((time.time() - start_time) * 1000)
            
            # Step 9: Create AI request log
            self._create_request_log(
                user_id=user_id,
                request_id=request_id,
                brain_mode=brain_mode_str,
                operation_type=operation_type_str,
                model_used=provider_response.model_used,
                prompt_length=len(prompt),
                response_length=len(provider_response.content),
                tokens_used=provider_response.tokens_used,
                credits_consumed=actual_cost,
                latency_ms=latency_ms,
                status='success',
                cognitive_blend_value=cognitive_blend_value,
            )
            
            logger.info(
                f"[AIService] Request {request_id} completed successfully: "
                f"model={provider_response.model_used}, tokens={provider_response.tokens_used}, "
                f"credits={actual_cost}, latency={latency_ms}ms"
            )
            
            # Record metrics
            ai_requests_total.labels(
                brain_mode=brain_mode_str,
                operation_type=operation_type_str,
                model_used=provider_response.model_used,
                status='success'
            ).inc()
            
            ai_request_tokens_total.labels(
                brain_mode=brain_mode_str,
                model_used=provider_response.model_used
            ).inc(provider_response.tokens_used)
            
            ai_request_latency_seconds.labels(
                brain_mode=brain_mode_str,
                model_used=provider_response.model_used
            ).observe(latency_ms / 1000.0)
            
            # Step 10: Return response
            return AIResponse(
                content=provider_response.content,
                tokens_used=provider_response.tokens_used,
                model_used=provider_response.model_used,
                credits_consumed=actual_cost,
                latency_ms=latency_ms,
                request_id=request_id,
                brain_mode=brain_mode_str,
                operation_type=operation_type_str,
                cognitive_blend_value=cognitive_blend_value,
            )
        
        except (InsufficientCreditsError, BrainModeRestrictedError, ModelUnavailableError) as e:
            # These are expected errors - log and re-raise
            latency_ms = int((time.time() - start_time) * 1000)
            error_type = type(e).__name__
            
            self._create_request_log(
                user_id=user_id,
                request_id=request_id,
                brain_mode=brain_mode_str,
                operation_type=operation_type_str,
                model_used='none',
                prompt_length=len(prompt),
                response_length=0,
                tokens_used=0,
                credits_consumed=0,
                latency_ms=latency_ms,
                status='failed',
                error_message=str(e),
                error_type=error_type,
            )
            
            # Record metrics
            ai_requests_total.labels(
                brain_mode=brain_mode_str,
                operation_type=operation_type_str,
                model_used='none',
                status='failed'
            ).inc()
            
            logger.warning(
                f"[AIService] Request {request_id} failed: {error_type} - {str(e)}"
            )
            raise
        
        except Exception as e:
            # Unexpected errors - log and wrap in ProviderAPIError
            latency_ms = int((time.time() - start_time) * 1000)
            error_type = type(e).__name__
            
            self._create_request_log(
                user_id=user_id,
                request_id=request_id,
                brain_mode=brain_mode_str,
                operation_type=operation_type_str,
                model_used='none',
                prompt_length=len(prompt),
                response_length=0,
                tokens_used=0,
                credits_consumed=0,
                latency_ms=latency_ms,
                status='failed',
                error_message=str(e),
                error_type=error_type,
            )
            
            logger.error(
                f"[AIService] Request {request_id} failed with unexpected error: {e}",
                exc_info=True
            )
            raise ProviderAPIError(f"AI request failed: {str(e)}")
    
    def validate_brain_mode_access(
        self,
        user_id: int,
        brain_mode: BrainMode
    ) -> None:
        """
        Validate user's subscription tier allows requested brain mode.
        
        Requirements: 5.10, 9.2
        
        Args:
            user_id: ID of the user
            brain_mode: Requested brain mode
        
        Raises:
            BrainModeRestrictedError: If user's tier doesn't allow brain_mode
        """
        # Import here to avoid circular dependency
        from apps.authentication.models import User
        
        brain_mode_str = brain_mode.value if isinstance(brain_mode, BrainMode) else brain_mode
        
        try:
            user = User.objects.get(id=user_id)
            user_tier = user.subscription.tier.upper()
            
            # Get allowed tiers for this brain mode
            allowed_tiers = BRAIN_MODE_TIER_REQUIREMENTS.get(brain_mode_str, [])
            
            if user_tier not in allowed_tiers:
                # Determine required tier (lowest tier that allows this mode)
                tier_hierarchy = ['FREE', 'PRO', 'TWIN_PLUS', 'EXECUTIVE']
                required_tier = None
                for tier in tier_hierarchy:
                    if tier in allowed_tiers:
                        required_tier = tier
                        break
                
                logger.warning(
                    f"[AIService] User {user_id} (tier={user_tier}) attempted to access "
                    f"restricted brain_mode={brain_mode_str} (requires {required_tier})"
                )
                
                raise BrainModeRestrictedError(
                    requested_mode=brain_mode_str,
                    current_tier=user_tier,
                    required_tier=required_tier or 'UNKNOWN'
                )
            
            logger.debug(
                f"[AIService] User {user_id} (tier={user_tier}) has access to "
                f"brain_mode={brain_mode_str}"
            )
        
        except User.DoesNotExist:
            logger.error(f"[AIService] User {user_id} not found")
            raise ValueError(f"User {user_id} not found")
    
    def _build_system_prompt_from_profile(
        self,
        blended_profile: Dict[str, Any],
        blend_percentage: int
    ) -> str:
        """
        Build system prompt from blended CSM profile.
        
        Constructs a system prompt that incorporates personality traits,
        tone preferences, and communication habits proportional to the
        cognitive blend percentage.
        
        Args:
            blended_profile: Blended profile from CSMService.apply_blend()
            blend_percentage: Cognitive blend value (0-100)
        
        Returns:
            System prompt string with personality context
        """
        # Extract profile components
        personality = blended_profile.get('personality', {})
        tone = blended_profile.get('tone', {})
        communication = blended_profile.get('communication', {})
        vocabulary = blended_profile.get('vocabulary_patterns', [])
        
        # Build system prompt based on blend mode
        mode = blended_profile.get('mode', 'balanced')
        
        if mode == 'ai_logic':
            # Minimal personality overlay (0-30%)
            prompt = (
                f"You are an AI assistant with {blend_percentage}% personality mimicry. "
                f"Prioritize logical reasoning and accuracy. "
            )
        elif mode == 'balanced':
            # Balanced personality and logic (31-70%)
            prompt = (
                f"You are an AI assistant with {blend_percentage}% personality mimicry. "
                f"Balance the user's communication style with clear, logical responses. "
            )
        else:
            # Heavy personality mimicry (71-100%)
            prompt = (
                f"You are an AI assistant with {blend_percentage}% personality mimicry. "
                f"Closely match the user's communication style and personality. "
            )
        
        # Add tone preferences
        formality = tone.get('formality', 0.5)
        warmth = tone.get('warmth', 0.5)
        directness = tone.get('directness', 0.5)
        
        if formality > 0.6:
            prompt += "Use formal language. "
        elif formality < 0.4:
            prompt += "Use casual, conversational language. "
        
        if warmth > 0.6:
            prompt += "Be warm and friendly. "
        elif warmth < 0.4:
            prompt += "Be professional and neutral. "
        
        if directness > 0.6:
            prompt += "Be direct and concise. "
        elif directness < 0.4:
            prompt += "Be detailed and explanatory. "
        
        # Add communication habits
        greeting = communication.get('preferred_greeting')
        if greeting:
            prompt += f"Use '{greeting}' as a greeting when appropriate. "
        
        response_length = communication.get('response_length', 'moderate')
        if response_length == 'brief':
            prompt += "Keep responses brief and to the point. "
        elif response_length == 'detailed':
            prompt += "Provide detailed, comprehensive responses. "
        
        # Add vocabulary patterns
        if vocabulary:
            vocab_str = ', '.join(vocabulary[:5])  # Limit to first 5
            prompt += f"Incorporate these vocabulary patterns when natural: {vocab_str}. "
        
        return prompt.strip()
    
    def _execute_with_fallback(
        self,
        model_selection,
        messages: List[dict],
        max_tokens: int,
        temperature: float
    ) -> ProviderResponse:
        """
        Execute request with fallback logic.
        
        Requirements: 9.4, 9.5, 9.6
        
        Tries primary model first, then fallbacks if primary fails.
        
        Args:
            model_selection: ModelSelection from router
            messages: List of message dicts with 'role' and 'content'
            max_tokens: Maximum tokens for response
            temperature: Temperature for generation
        
        Returns:
            ProviderResponse from successful provider
        
        Raises:
            ModelUnavailableError: If all models fail
        """
        all_models = model_selection.get_all_models()
        attempted_models = []
        last_error = None
        
        for model_name in all_models:
            try:
                logger.info(f"[AIService] Attempting model: {model_name}")
                
                # Get provider for this model
                provider = self.provider_registry.get_provider(model_name)
                
                # Execute request with messages
                response = provider.generate_response(
                    messages=messages,
                    max_tokens=max_tokens,
                    temperature=temperature
                )
                
                logger.info(
                    f"[AIService] Successfully generated response with {model_name}: "
                    f"{response.tokens_used} tokens, {response.latency_ms}ms"
                )
                
                return response
            
            except Exception as e:
                attempted_models.append(model_name)
                last_error = e
                logger.warning(
                    f"[AIService] Model {model_name} failed: {str(e)}. "
                    f"Trying fallback..."
                )
                continue
        
        # All models failed
        logger.error(
            f"[AIService] All models failed. Attempted: {attempted_models}"
        )
        raise ModelUnavailableError(
            attempted_models=attempted_models
        )
    
    def _create_request_log(
        self,
        user_id: int,
        request_id: uuid.UUID,
        brain_mode: str,
        operation_type: str,
        model_used: str,
        prompt_length: int,
        response_length: int,
        tokens_used: int,
        credits_consumed: int,
        latency_ms: int,
        status: str,
        error_message: Optional[str] = None,
        error_type: Optional[str] = None,
        cognitive_blend_value: Optional[int] = None,
    ) -> AIRequestLog:
        """
        Create AI request log entry.
        
        Requirements: 9.9, 9.10, 9.11
        
        Args:
            user_id: ID of the user
            request_id: UUID of the request
            brain_mode: Brain mode used
            operation_type: Operation type
            model_used: Model that processed the request
            prompt_length: Length of prompt in characters
            response_length: Length of response in characters
            tokens_used: Number of tokens consumed
            credits_consumed: Number of credits consumed
            latency_ms: Request latency in milliseconds
            status: Status of the request (success, failed, etc.)
            error_message: Optional error message
            error_type: Optional error type
            cognitive_blend_value: Optional cognitive blend value from Twin
        
        Returns:
            Created AIRequestLog instance
        """
        log_entry = AIRequestLog.objects.create(
            id=request_id,
            user_id=user_id,
            brain_mode=brain_mode,
            operation_type=operation_type,
            model_used=model_used,
            prompt_length=prompt_length,
            response_length=response_length,
            tokens_used=tokens_used,
            credits_consumed=credits_consumed,
            latency_ms=latency_ms,
            status=status,
            error_message=error_message,
            error_type=error_type,
            cognitive_blend_value=cognitive_blend_value,
        )
        
        logger.debug(
            f"[AIService] Created AI request log: {request_id} "
            f"(status={status}, model={model_used})"
        )
        
        return log_entry
