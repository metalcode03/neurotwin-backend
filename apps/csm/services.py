"""
CSM (Cognitive Signature Model) service for NeuroTwin platform.

Handles CSM profile creation, updates, versioning, and rollback.
Business logic for cognitive profile management.

Requirements: 4.2, 4.3, 4.4, 4.5, 4.7
"""

from typing import Optional, List, Dict, Any
from django.db import transaction
from django.utils import timezone

from .models import CSMProfile, CSMChangeLog
from .dataclasses import (
    CSMProfileData,
    PersonalityTraits,
    TonePreferences,
    CommunicationHabits,
    DecisionStyle,
    QuestionnaireResponse,
)


class CSMService:
    """
    Manages CSM profiles and versioning.
    
    Provides methods for creating, updating, and rolling back
    cognitive signature model profiles.
    
    Requirements: 4.2, 4.3, 4.4, 4.5, 4.7
    """
    
    @transaction.atomic
    def create_from_questionnaire(
        self,
        user_id: str,
        responses: QuestionnaireResponse
    ) -> CSMProfile:
        """
        Generate initial CSM from onboarding questionnaire responses.
        
        Requirements: 4.1, 4.2
        
        Args:
            user_id: UUID of the user
            responses: Questionnaire responses containing communication style,
                      decision patterns, and preferences
                      
        Returns:
            Newly created CSMProfile
        """
        # Extract personality traits from questionnaire
        personality = self._extract_personality(responses)
        tone = self._extract_tone(responses)
        communication = self._extract_communication(responses)
        decision_style = self._extract_decision_style(responses)
        vocabulary = self._extract_vocabulary(responses)
        
        # Create profile data
        profile_data = CSMProfileData(
            personality=personality,
            tone=tone,
            vocabulary_patterns=vocabulary,
            communication=communication,
            decision_style=decision_style,
            custom_rules={},
        )
        
        # Mark any existing profiles as not current
        CSMProfile.objects.filter(user_id=user_id, is_current=True).update(
            is_current=False
        )
        
        # Create new profile
        profile = CSMProfile.objects.create(
            user_id=user_id,
            version=1,
            profile_data=profile_data.to_dict(),
            is_current=True,
        )
        
        # Log the creation
        CSMChangeLog.objects.create(
            profile=profile,
            from_version=None,
            to_version=1,
            change_type='create',
            change_summary={'source': 'questionnaire'},
        )
        
        return profile
    
    def _extract_personality(self, responses: QuestionnaireResponse) -> PersonalityTraits:
        """Extract personality traits from questionnaire responses."""
        comm = responses.communication_style
        decision = responses.decision_patterns
        prefs = responses.preferences
        
        return PersonalityTraits(
            openness=float(comm.get('openness', 0.5)),
            conscientiousness=float(decision.get('conscientiousness', 0.5)),
            extraversion=float(comm.get('extraversion', 0.5)),
            agreeableness=float(comm.get('agreeableness', 0.5)),
            neuroticism=float(prefs.get('neuroticism', 0.5)),
        )
    
    def _extract_tone(self, responses: QuestionnaireResponse) -> TonePreferences:
        """Extract tone preferences from questionnaire responses."""
        comm = responses.communication_style
        prefs = responses.preferences
        
        return TonePreferences(
            formality=float(comm.get('formality', 0.5)),
            warmth=float(comm.get('warmth', 0.5)),
            directness=float(comm.get('directness', 0.5)),
            humor_level=float(prefs.get('humor_level', 0.3)),
        )
    
    def _extract_communication(self, responses: QuestionnaireResponse) -> CommunicationHabits:
        """Extract communication habits from questionnaire responses."""
        comm = responses.communication_style
        prefs = responses.preferences
        
        return CommunicationHabits(
            preferred_greeting=str(comm.get('preferred_greeting', 'Hello')),
            sign_off_style=str(comm.get('sign_off_style', 'Best regards')),
            response_length=str(prefs.get('response_length', 'moderate')),
            emoji_usage=str(prefs.get('emoji_usage', 'minimal')),
        )
    
    def _extract_decision_style(self, responses: QuestionnaireResponse) -> DecisionStyle:
        """Extract decision style from questionnaire responses."""
        decision = responses.decision_patterns
        
        return DecisionStyle(
            risk_tolerance=float(decision.get('risk_tolerance', 0.5)),
            speed_vs_accuracy=float(decision.get('speed_vs_accuracy', 0.5)),
            collaboration_preference=float(decision.get('collaboration_preference', 0.5)),
        )
    
    def _extract_vocabulary(self, responses: QuestionnaireResponse) -> List[str]:
        """Extract vocabulary patterns from questionnaire responses."""
        prefs = responses.preferences
        vocab = prefs.get('vocabulary_patterns', [])
        if isinstance(vocab, list):
            return [str(v) for v in vocab]
        return []
    
    def get_profile(self, user_id: str) -> Optional[CSMProfile]:
        """
        Get current CSM profile for user.
        
        Args:
            user_id: UUID of the user
            
        Returns:
            Current CSMProfile or None if not found
        """
        return CSMProfile.get_current_for_user(user_id)
    
    @transaction.atomic
    def update_profile(
        self,
        user_id: str,
        updates: Dict[str, Any]
    ) -> CSMProfile:
        """
        Update CSM and create new version in history.
        
        Requirements: 4.7 - maintains change history for rollback
        
        Args:
            user_id: UUID of the user
            updates: Dictionary of updates to apply to the profile
            
        Returns:
            New CSMProfile version with updates applied
            
        Raises:
            ValueError: If no current profile exists
        """
        current = self.get_profile(user_id)
        if not current:
            raise ValueError(f"No CSM profile found for user {user_id}")
        
        # Get current profile data
        current_data = current.get_profile_data()
        
        # Apply updates
        updated_data = self._apply_updates(current_data, updates)
        
        # Mark current as not current
        current.is_current = False
        current.save()
        
        # Get next version number
        next_version = CSMProfile.get_latest_version_number(user_id) + 1
        
        # Create new version
        new_profile = CSMProfile.objects.create(
            user_id=user_id,
            version=next_version,
            profile_data=updated_data.to_dict(),
            is_current=True,
        )
        
        # Log the change
        CSMChangeLog.objects.create(
            profile=new_profile,
            from_version=current.version,
            to_version=next_version,
            change_type='update',
            change_summary={'updated_fields': list(updates.keys())},
        )
        
        return new_profile
    
    def _apply_updates(
        self,
        current: CSMProfileData,
        updates: Dict[str, Any]
    ) -> CSMProfileData:
        """Apply updates to profile data."""
        data_dict = current.to_dict()
        
        for key, value in updates.items():
            if key in data_dict:
                if isinstance(data_dict[key], dict) and isinstance(value, dict):
                    # Merge nested dicts
                    data_dict[key].update(value)
                else:
                    data_dict[key] = value
        
        return CSMProfileData.from_dict(data_dict)
    
    def get_version_history(self, user_id: str) -> List[CSMProfile]:
        """
        Get all historical versions of user's CSM.
        
        Requirements: 4.7
        
        Args:
            user_id: UUID of the user
            
        Returns:
            List of all CSMProfile versions, ordered by version descending
        """
        return list(
            CSMProfile.objects.filter(user_id=user_id).order_by('-version')
        )
    
    @transaction.atomic
    def rollback_to_version(self, user_id: str, version: int) -> CSMProfile:
        """
        Restore CSM to a previous version.
        
        Requirements: 4.7, 12.4, 12.5
        
        Args:
            user_id: UUID of the user
            version: Version number to rollback to
            
        Returns:
            New CSMProfile with restored data
            
        Raises:
            ValueError: If version not found
        """
        target = CSMProfile.get_version_for_user(user_id, version)
        if not target:
            raise ValueError(f"Version {version} not found for user {user_id}")
        
        current = self.get_profile(user_id)
        current_version = current.version if current else 0
        
        # Mark current as not current
        if current:
            current.is_current = False
            current.save()
        
        # Get next version number
        next_version = CSMProfile.get_latest_version_number(user_id) + 1
        
        # Create new version with target's data
        new_profile = CSMProfile.objects.create(
            user_id=user_id,
            version=next_version,
            profile_data=target.profile_data,  # Copy the data from target version
            is_current=True,
        )
        
        # Log the rollback
        CSMChangeLog.objects.create(
            profile=new_profile,
            from_version=current_version,
            to_version=next_version,
            change_type='rollback',
            change_summary={
                'rolled_back_to': version,
                'reason': 'user_requested',
            },
        )
        
        return new_profile
    
    def apply_blend(self, profile: CSMProfile, blend: int) -> Dict[str, Any]:
        """
        Apply cognitive blend to profile for response generation.
        
        Requirements: 4.2, 4.3, 4.4, 4.5
        
        The blend value (0-100) controls how much personality vs AI logic:
        - 0-30%: Pure AI logic with minimal personality mimicry
        - 31-70%: Balanced blend of user personality + AI reasoning
        - 71-100%: Heavy personality mimicry, requires confirmation
        
        Args:
            profile: CSMProfile to apply blend to
            blend: Cognitive blend value (0-100)
            
        Returns:
            Dictionary with blended profile settings and metadata
            
        Raises:
            ValueError: If blend is not between 0 and 100
        """
        if not 0 <= blend <= 100:
            raise ValueError(f"Blend must be between 0 and 100, got {blend}")
        
        profile_data = profile.get_profile_data()
        blend_factor = blend / 100.0
        
        # Determine blend mode
        if blend <= 30:
            mode = 'ai_logic'
            personality_weight = blend_factor  # 0.0 - 0.3
            requires_confirmation = False
        elif blend <= 70:
            mode = 'balanced'
            personality_weight = blend_factor  # 0.31 - 0.7
            requires_confirmation = False
        else:
            mode = 'personality_heavy'
            personality_weight = blend_factor  # 0.71 - 1.0
            requires_confirmation = True
        
        # Apply blend to personality traits
        blended_personality = self._blend_personality(
            profile_data.personality,
            personality_weight
        )
        
        # Apply blend to tone
        blended_tone = self._blend_tone(
            profile_data.tone,
            personality_weight
        )
        
        return {
            'mode': mode,
            'blend_value': blend,
            'personality_weight': personality_weight,
            'requires_confirmation': requires_confirmation,
            'personality': blended_personality,
            'tone': blended_tone,
            'communication': profile_data.communication.to_dict(),
            'decision_style': profile_data.decision_style.to_dict(),
            'vocabulary_patterns': profile_data.vocabulary_patterns,
            'custom_rules': profile_data.custom_rules,
        }
    
    def _blend_personality(
        self,
        personality: PersonalityTraits,
        weight: float
    ) -> Dict[str, float]:
        """
        Blend personality traits with neutral baseline.
        
        At weight=0, returns neutral (0.5) values.
        At weight=1, returns full personality values.
        """
        neutral = 0.5
        return {
            'openness': neutral + (personality.openness - neutral) * weight,
            'conscientiousness': neutral + (personality.conscientiousness - neutral) * weight,
            'extraversion': neutral + (personality.extraversion - neutral) * weight,
            'agreeableness': neutral + (personality.agreeableness - neutral) * weight,
            'neuroticism': neutral + (personality.neuroticism - neutral) * weight,
        }
    
    def _blend_tone(
        self,
        tone: TonePreferences,
        weight: float
    ) -> Dict[str, float]:
        """
        Blend tone preferences with neutral baseline.
        
        At weight=0, returns neutral (0.5) values.
        At weight=1, returns full tone values.
        """
        neutral = 0.5
        return {
            'formality': neutral + (tone.formality - neutral) * weight,
            'warmth': neutral + (tone.warmth - neutral) * weight,
            'directness': neutral + (tone.directness - neutral) * weight,
            'humor_level': neutral + (tone.humor_level - neutral) * weight,
        }
