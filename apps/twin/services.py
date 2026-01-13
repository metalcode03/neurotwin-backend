"""
Twin service for NeuroTwin platform.

Handles Twin creation, onboarding, and cognitive blend management.
Business logic for Twin lifecycle management.

Requirements: 2.1, 2.2, 2.4, 2.5, 2.6
"""

from typing import Optional, Dict, Any
from django.db import transaction

from .models import Twin, OnboardingProgress
from .dataclasses import AIModel, QuestionnaireResponse, OnboardingQuestionnaire
from apps.csm.services import CSMService
from apps.csm.dataclasses import QuestionnaireResponse as CSMQuestionnaireResponse


class TwinService:
    """
    Manages Twin lifecycle and configuration.
    
    Provides methods for onboarding, Twin creation, and cognitive blend updates.
    
    Requirements: 2.1, 2.2, 2.4, 2.5, 2.6
    """
    
    def __init__(self):
        """Initialize TwinService with CSMService dependency."""
        self.csm_service = CSMService()
    
    def start_onboarding(self, user_id: str) -> Dict[str, Any]:
        """
        Return cognitive questionnaire for new user.
        
        Requirements: 2.1
        
        Args:
            user_id: UUID of the user starting onboarding
            
        Returns:
            Dictionary containing the questionnaire and onboarding metadata
        """
        # Check if user already has a Twin
        existing_twin = Twin.get_for_user(user_id)
        if existing_twin:
            return {
                'status': 'already_completed',
                'message': 'User already has an active Twin',
                'twin_id': str(existing_twin.id),
            }
        
        # Get or create onboarding progress
        progress, created = OnboardingProgress.objects.get_or_create(
            user_id=user_id,
            defaults={'questionnaire_responses': {}}
        )
        
        if progress.is_complete:
            return {
                'status': 'already_completed',
                'message': 'Onboarding already completed',
            }
        
        # Get the questionnaire
        questionnaire = OnboardingQuestionnaire.get_default_questionnaire()
        
        return {
            'status': 'in_progress' if not created else 'started',
            'questionnaire': questionnaire.to_dict(),
            'available_models': [
                {
                    'id': model.value,
                    'name': model.name.replace('_', ' ').title(),
                    'tier': 'free' if model in AIModel.free_tier_models() else 'paid',
                }
                for model in AIModel.all_models()
            ],
            'cognitive_blend': {
                'min': 0,
                'max': 100,
                'default': 50,
                'description': (
                    'Controls how much human personality vs AI logic your Twin uses. '
                    '0-30%: Pure AI logic with minimal personality. '
                    '31-70%: Balanced blend of personality and AI reasoning. '
                    '71-100%: Heavy personality mimicry (requires confirmation for actions).'
                ),
            },
            'saved_responses': progress.questionnaire_responses,
        }
    
    @transaction.atomic
    def complete_onboarding(
        self,
        user_id: str,
        responses: QuestionnaireResponse,
        model: AIModel,
        cognitive_blend: int
    ) -> Twin:
        """
        Create Twin with initial CSM from questionnaire responses.
        
        Requirements: 2.2, 2.4, 2.5, 2.6
        
        Args:
            user_id: UUID of the user
            responses: Completed questionnaire responses
            model: Selected AI model
            cognitive_blend: Initial cognitive blend value (0-100)
            
        Returns:
            Newly created Twin
            
        Raises:
            ValueError: If cognitive_blend is not between 0 and 100
            ValueError: If user already has an active Twin
            ValueError: If questionnaire responses are incomplete
        """
        # Validate cognitive blend
        if not 0 <= cognitive_blend <= 100:
            raise ValueError(f"Cognitive blend must be between 0 and 100, got {cognitive_blend}")
        
        # Check if user already has a Twin
        existing_twin = Twin.get_for_user(user_id)
        if existing_twin:
            raise ValueError(f"User {user_id} already has an active Twin")
        
        # Validate questionnaire responses
        if not responses.is_complete():
            raise ValueError("Questionnaire responses are incomplete")
        
        # Convert to CSM questionnaire response format
        csm_responses = CSMQuestionnaireResponse(
            communication_style=responses.communication_style,
            decision_patterns=responses.decision_patterns,
            preferences=responses.preferences,
        )
        
        # Create CSM profile from questionnaire
        csm_profile = self.csm_service.create_from_questionnaire(
            user_id=user_id,
            responses=csm_responses
        )
        
        # Create the Twin
        twin = Twin.objects.create(
            user_id=user_id,
            model=model.value,
            cognitive_blend=cognitive_blend,
            csm_profile=csm_profile,
            is_active=True,
        )
        
        # Mark onboarding as complete
        OnboardingProgress.objects.filter(user_id=user_id).update(
            is_complete=True,
            questionnaire_responses=responses.to_dict(),
            selected_model=model.value,
            selected_blend=cognitive_blend,
        )
        
        return twin
    
    @transaction.atomic
    def update_cognitive_blend(self, twin_id: str, blend: int) -> Twin:
        """
        Update the cognitive blend setting (0-100).
        
        Requirements: 2.4, 2.5, 14.3 (Transaction integrity)
        
        Args:
            twin_id: UUID of the Twin
            blend: New cognitive blend value (0-100)
            
        Returns:
            Updated Twin
            
        Raises:
            ValueError: If blend is not between 0 and 100
            ValueError: If Twin not found
        """
        if not 0 <= blend <= 100:
            raise ValueError(f"Cognitive blend must be between 0 and 100, got {blend}")
        
        try:
            twin = Twin.objects.get(id=twin_id)
        except Twin.DoesNotExist:
            raise ValueError(f"Twin {twin_id} not found")
        
        twin.cognitive_blend = blend
        twin.save()
        
        return twin
    
    def get_twin(self, user_id: str) -> Optional[Twin]:
        """
        Retrieve user's Twin.
        
        Args:
            user_id: UUID of the user
            
        Returns:
            Twin instance or None if not found
        """
        return Twin.get_for_user(user_id)
    
    @transaction.atomic
    def deactivate_twin(self, twin_id: str) -> bool:
        """
        Deactivate Twin (kill switch).
        
        Requirements: 2.6, 14.3 (Transaction integrity)
        
        Args:
            twin_id: UUID of the Twin to deactivate
            
        Returns:
            True if deactivation was successful
            
        Raises:
            ValueError: If Twin not found
        """
        try:
            twin = Twin.objects.get(id=twin_id)
        except Twin.DoesNotExist:
            raise ValueError(f"Twin {twin_id} not found")
        
        twin.is_active = False
        twin.kill_switch_active = True
        twin.save()
        
        return True
    
    @transaction.atomic
    def reactivate_twin(self, twin_id: str) -> Twin:
        """
        Reactivate a deactivated Twin.
        
        Requirements: 14.3 (Transaction integrity)
        
        Args:
            twin_id: UUID of the Twin to reactivate
            
        Returns:
            Reactivated Twin
            
        Raises:
            ValueError: If Twin not found
        """
        try:
            twin = Twin.objects.get(id=twin_id)
        except Twin.DoesNotExist:
            raise ValueError(f"Twin {twin_id} not found")
        
        twin.is_active = True
        twin.kill_switch_active = False
        twin.save()
        
        return twin
    
    @transaction.atomic
    def update_model(self, twin_id: str, model: AIModel) -> Twin:
        """
        Update the AI model for a Twin.
        
        Requirements: 2.3, 14.3 (Transaction integrity)
        
        Args:
            twin_id: UUID of the Twin
            model: New AI model
            
        Returns:
            Updated Twin
            
        Raises:
            ValueError: If Twin not found
        """
        try:
            twin = Twin.objects.get(id=twin_id)
        except Twin.DoesNotExist:
            raise ValueError(f"Twin {twin_id} not found")
        
        twin.set_ai_model(model)
        twin.save()
        
        return twin
    
    def save_onboarding_progress(
        self,
        user_id: str,
        responses: Dict[str, Any],
        model: Optional[str] = None,
        blend: Optional[int] = None
    ) -> OnboardingProgress:
        """
        Save partial onboarding progress.
        
        Args:
            user_id: UUID of the user
            responses: Partial questionnaire responses
            model: Selected AI model (optional)
            blend: Selected cognitive blend (optional)
            
        Returns:
            Updated OnboardingProgress
        """
        progress, _ = OnboardingProgress.objects.get_or_create(
            user_id=user_id,
            defaults={'questionnaire_responses': {}}
        )
        
        # Merge responses
        current_responses = progress.questionnaire_responses or {}
        current_responses.update(responses)
        progress.questionnaire_responses = current_responses
        
        if model is not None:
            progress.selected_model = model
        
        if blend is not None:
            if not 0 <= blend <= 100:
                raise ValueError(f"Cognitive blend must be between 0 and 100, got {blend}")
            progress.selected_blend = blend
        
        progress.save()
        return progress
    
    def get_twin_with_blend_info(self, user_id: str) -> Optional[Dict[str, Any]]:
        """
        Get Twin with cognitive blend information.
        
        Returns detailed information about the Twin including blend mode
        and whether actions require confirmation.
        
        Args:
            user_id: UUID of the user
            
        Returns:
            Dictionary with Twin info or None if not found
        """
        twin = self.get_twin(user_id)
        if not twin:
            return None
        
        # Get blended profile from CSM service
        blended_profile = None
        if twin.csm_profile:
            blended_profile = self.csm_service.apply_blend(
                twin.csm_profile,
                twin.cognitive_blend
            )
        
        return {
            'id': str(twin.id),
            'user_id': str(twin.user_id),
            'model': twin.model,
            'cognitive_blend': twin.cognitive_blend,
            'blend_mode': twin.blend_mode,
            'requires_confirmation': twin.requires_confirmation,
            'is_active': twin.is_active,
            'kill_switch_active': twin.kill_switch_active,
            'csm_profile_id': str(twin.csm_profile.id) if twin.csm_profile else None,
            'blended_profile': blended_profile,
            'created_at': twin.created_at.isoformat(),
            'updated_at': twin.updated_at.isoformat(),
        }
