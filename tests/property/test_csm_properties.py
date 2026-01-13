"""
Property-based tests for CSM (Cognitive Signature Model).

Feature: neurotwin-platform
Validates: Requirements 4.6, 4.7, 6.6, 12.4, 12.5

These tests use Hypothesis to verify CSM properties hold
across a wide range of inputs.
"""

import pytest
from hypothesis import given, strategies as st, settings, assume
from django.utils import timezone

from apps.csm.dataclasses import (
    PersonalityTraits,
    TonePreferences,
    CommunicationHabits,
    DecisionStyle,
    CSMProfileData,
)
from apps.csm.models import CSMProfile, CSMChangeLog
from apps.authentication.models import User


# Custom strategies for generating CSM data

# Strategy for float values between 0.0 and 1.0
unit_float = st.floats(min_value=0.0, max_value=1.0, allow_nan=False, allow_infinity=False)

# Strategy for PersonalityTraits
personality_traits_strategy = st.builds(
    PersonalityTraits,
    openness=unit_float,
    conscientiousness=unit_float,
    extraversion=unit_float,
    agreeableness=unit_float,
    neuroticism=unit_float,
)

# Strategy for TonePreferences
tone_preferences_strategy = st.builds(
    TonePreferences,
    formality=unit_float,
    warmth=unit_float,
    directness=unit_float,
    humor_level=unit_float,
)

# Strategy for CommunicationHabits
communication_habits_strategy = st.builds(
    CommunicationHabits,
    preferred_greeting=st.text(min_size=0, max_size=50),
    sign_off_style=st.text(min_size=0, max_size=50),
    response_length=st.sampled_from(['brief', 'moderate', 'detailed']),
    emoji_usage=st.sampled_from(['none', 'minimal', 'moderate', 'frequent']),
)

# Strategy for DecisionStyle
decision_style_strategy = st.builds(
    DecisionStyle,
    risk_tolerance=unit_float,
    speed_vs_accuracy=unit_float,
    collaboration_preference=unit_float,
)

# Strategy for vocabulary patterns (list of strings)
vocabulary_patterns_strategy = st.lists(
    st.text(min_size=1, max_size=30, alphabet=st.characters(
        whitelist_categories=('L', 'N'),  # Letters and numbers only
        whitelist_characters='-_'
    )),
    min_size=0,
    max_size=20
)

# Strategy for custom rules (dict of string to string)
custom_rules_strategy = st.dictionaries(
    keys=st.text(min_size=1, max_size=30, alphabet=st.characters(
        whitelist_categories=('L', 'N'),
        whitelist_characters='_'
    )),
    values=st.text(min_size=0, max_size=100),
    min_size=0,
    max_size=10
)

# Strategy for complete CSMProfileData
csm_profile_data_strategy = st.builds(
    CSMProfileData,
    personality=personality_traits_strategy,
    tone=tone_preferences_strategy,
    vocabulary_patterns=vocabulary_patterns_strategy,
    communication=communication_habits_strategy,
    decision_style=decision_style_strategy,
    custom_rules=custom_rules_strategy,
)


def create_test_user(email_suffix: str) -> User:
    """Create a test user with unique email."""
    email = f"csm_test_{email_suffix}@example.com"
    User.objects.filter(email=email).delete()
    return User.objects.create_user(email=email, password="testpass123")


@pytest.mark.django_db(transaction=True)
class TestCSMSerializationRoundTrip:
    """
    Property 10: CSM JSON serialization round-trip
    
    *For any* valid CSM profile, serializing to JSON then deserializing
    SHALL produce an equivalent CSM profile.
    
    **Validates: Requirements 4.6**
    """
    
    @settings(deadline=None)
    @given(profile_data=csm_profile_data_strategy)
    def test_csm_json_round_trip(self, profile_data: CSMProfileData):
        """
        Feature: neurotwin-platform, Property 10: CSM JSON serialization round-trip
        
        For any valid CSM profile data, serializing to JSON and then
        deserializing should produce an equivalent profile.
        """
        # Serialize to JSON
        json_str = profile_data.to_json()
        
        # Deserialize from JSON
        restored = CSMProfileData.from_json(json_str)
        
        # Verify all fields match
        assert restored.personality.openness == profile_data.personality.openness
        assert restored.personality.conscientiousness == profile_data.personality.conscientiousness
        assert restored.personality.extraversion == profile_data.personality.extraversion
        assert restored.personality.agreeableness == profile_data.personality.agreeableness
        assert restored.personality.neuroticism == profile_data.personality.neuroticism
        
        assert restored.tone.formality == profile_data.tone.formality
        assert restored.tone.warmth == profile_data.tone.warmth
        assert restored.tone.directness == profile_data.tone.directness
        assert restored.tone.humor_level == profile_data.tone.humor_level
        
        assert restored.vocabulary_patterns == profile_data.vocabulary_patterns
        
        assert restored.communication.preferred_greeting == profile_data.communication.preferred_greeting
        assert restored.communication.sign_off_style == profile_data.communication.sign_off_style
        assert restored.communication.response_length == profile_data.communication.response_length
        assert restored.communication.emoji_usage == profile_data.communication.emoji_usage
        
        assert restored.decision_style.risk_tolerance == profile_data.decision_style.risk_tolerance
        assert restored.decision_style.speed_vs_accuracy == profile_data.decision_style.speed_vs_accuracy
        assert restored.decision_style.collaboration_preference == profile_data.decision_style.collaboration_preference
        
        assert restored.custom_rules == profile_data.custom_rules
    
    @settings(deadline=None)
    @given(profile_data=csm_profile_data_strategy)
    def test_csm_dict_round_trip(self, profile_data: CSMProfileData):
        """
        Feature: neurotwin-platform, Property 10: CSM JSON serialization round-trip
        
        For any valid CSM profile data, converting to dict and back
        should produce an equivalent profile.
        """
        # Convert to dict
        data_dict = profile_data.to_dict()
        
        # Restore from dict
        restored = CSMProfileData.from_dict(data_dict)
        
        # Verify equivalence via dict comparison
        assert restored.to_dict() == profile_data.to_dict()
    
    @settings(deadline=None)
    @given(profile_data=csm_profile_data_strategy)
    def test_csm_model_round_trip(self, profile_data: CSMProfileData):
        """
        Feature: neurotwin-platform, Property 10: CSM JSON serialization round-trip
        
        For any valid CSM profile data, storing in a model and retrieving
        should produce an equivalent profile.
        """
        # Create test user
        user = create_test_user(f"model_rt_{hash(str(profile_data.to_dict())) % 100000}")
        
        try:
            # Create profile model
            profile = CSMProfile.objects.create(
                user=user,
                version=1,
                profile_data=profile_data.to_dict()
            )
            
            # Retrieve and verify
            retrieved = CSMProfile.objects.get(id=profile.id)
            restored_data = retrieved.get_profile_data()
            
            # Verify equivalence
            assert restored_data.to_dict() == profile_data.to_dict()
            
            # Also test model's to_json method
            json_from_model = retrieved.to_json()
            restored_from_json = CSMProfileData.from_json(json_from_model)
            assert restored_from_json.to_dict() == profile_data.to_dict()
        finally:
            User.objects.filter(id=user.id).delete()



@pytest.mark.django_db(transaction=True)
class TestCSMVersionHistoryAndRollback:
    """
    Property 11: CSM version history and rollback
    
    *For any* CSM update, the system SHALL maintain version history,
    and rolling back to any previous version SHALL restore that exact state.
    
    **Validates: Requirements 4.7, 6.6, 12.4, 12.5**
    """
    
    @settings(deadline=None)
    @given(
        initial_data=csm_profile_data_strategy,
        num_updates=st.integers(min_value=1, max_value=5),
    )
    def test_version_history_maintained(
        self,
        initial_data: CSMProfileData,
        num_updates: int
    ):
        """
        Feature: neurotwin-platform, Property 11: CSM version history and rollback
        
        For any sequence of updates, the system should maintain complete
        version history with correct version numbers.
        """
        from apps.csm.services import CSMService
        from apps.csm.dataclasses import QuestionnaireResponse
        
        service = CSMService()
        user = create_test_user(f"version_hist_{hash(str(initial_data.to_dict())) % 100000}")
        
        try:
            # Create initial profile via questionnaire
            responses = QuestionnaireResponse(
                communication_style={
                    'openness': initial_data.personality.openness,
                    'extraversion': initial_data.personality.extraversion,
                    'agreeableness': initial_data.personality.agreeableness,
                    'formality': initial_data.tone.formality,
                    'warmth': initial_data.tone.warmth,
                    'directness': initial_data.tone.directness,
                    'preferred_greeting': initial_data.communication.preferred_greeting,
                    'sign_off_style': initial_data.communication.sign_off_style,
                },
                decision_patterns={
                    'conscientiousness': initial_data.personality.conscientiousness,
                    'risk_tolerance': initial_data.decision_style.risk_tolerance,
                    'speed_vs_accuracy': initial_data.decision_style.speed_vs_accuracy,
                    'collaboration_preference': initial_data.decision_style.collaboration_preference,
                },
                preferences={
                    'neuroticism': initial_data.personality.neuroticism,
                    'humor_level': initial_data.tone.humor_level,
                    'response_length': initial_data.communication.response_length,
                    'emoji_usage': initial_data.communication.emoji_usage,
                    'vocabulary_patterns': initial_data.vocabulary_patterns,
                }
            )
            
            service.create_from_questionnaire(str(user.id), responses)
            
            # Perform updates
            for i in range(num_updates):
                new_openness = (initial_data.personality.openness + (i + 1) * 0.1) % 1.0
                service.update_profile(
                    str(user.id),
                    {'personality': {'openness': new_openness}}
                )
            
            # Verify version history
            history = service.get_version_history(str(user.id))
            
            # Should have initial + num_updates versions
            assert len(history) == num_updates + 1
            
            # Versions should be sequential and descending
            for i, profile in enumerate(history):
                expected_version = num_updates + 1 - i
                assert profile.version == expected_version
            
            # Only the latest should be current
            assert history[0].is_current is True
            for profile in history[1:]:
                assert profile.is_current is False
        finally:
            User.objects.filter(id=user.id).delete()
    
    @settings(deadline=None)
    @given(
        initial_data=csm_profile_data_strategy,
        rollback_to=st.integers(min_value=1, max_value=3),
    )
    def test_rollback_restores_exact_state(
        self,
        initial_data: CSMProfileData,
        rollback_to: int
    ):
        """
        Feature: neurotwin-platform, Property 11: CSM version history and rollback
        
        For any rollback operation, the restored profile should contain
        exactly the same data as the target version.
        """
        from apps.csm.services import CSMService
        from apps.csm.dataclasses import QuestionnaireResponse
        from apps.csm.models import CSMProfile
        
        service = CSMService()
        user = create_test_user(f"rollback_{hash(str(initial_data.to_dict())) % 100000}")
        
        try:
            # Create initial profile
            responses = QuestionnaireResponse(
                communication_style={
                    'openness': initial_data.personality.openness,
                    'extraversion': initial_data.personality.extraversion,
                    'agreeableness': initial_data.personality.agreeableness,
                    'formality': initial_data.tone.formality,
                    'warmth': initial_data.tone.warmth,
                    'directness': initial_data.tone.directness,
                    'preferred_greeting': initial_data.communication.preferred_greeting,
                    'sign_off_style': initial_data.communication.sign_off_style,
                },
                decision_patterns={
                    'conscientiousness': initial_data.personality.conscientiousness,
                    'risk_tolerance': initial_data.decision_style.risk_tolerance,
                    'speed_vs_accuracy': initial_data.decision_style.speed_vs_accuracy,
                    'collaboration_preference': initial_data.decision_style.collaboration_preference,
                },
                preferences={
                    'neuroticism': initial_data.personality.neuroticism,
                    'humor_level': initial_data.tone.humor_level,
                    'response_length': initial_data.communication.response_length,
                    'emoji_usage': initial_data.communication.emoji_usage,
                    'vocabulary_patterns': initial_data.vocabulary_patterns,
                }
            )
            
            service.create_from_questionnaire(str(user.id), responses)
            
            # Create enough versions to rollback to
            for i in range(3):
                new_openness = (initial_data.personality.openness + (i + 1) * 0.1) % 1.0
                service.update_profile(
                    str(user.id),
                    {'personality': {'openness': new_openness}}
                )
            
            # Get the target version's data before rollback
            target_profile = CSMProfile.get_version_for_user(str(user.id), rollback_to)
            target_data = target_profile.profile_data.copy()
            
            # Perform rollback
            rolled_back = service.rollback_to_version(str(user.id), rollback_to)
            
            # Verify the rolled back profile has exact same data
            assert rolled_back.profile_data == target_data
            assert rolled_back.is_current is True
            
            # Verify it's a new version (not modifying the old one)
            assert rolled_back.version > rollback_to
        finally:
            User.objects.filter(id=user.id).delete()
    
    @settings(deadline=None)
    @given(initial_data=csm_profile_data_strategy)
    def test_rollback_creates_change_log(self, initial_data: CSMProfileData):
        """
        Feature: neurotwin-platform, Property 11: CSM version history and rollback
        
        For any rollback operation, a change log entry should be created
        with the rollback details.
        """
        from apps.csm.services import CSMService
        from apps.csm.dataclasses import QuestionnaireResponse
        from apps.csm.models import CSMChangeLog
        
        service = CSMService()
        user = create_test_user(f"rollback_log_{hash(str(initial_data.to_dict())) % 100000}")
        
        try:
            # Create initial profile
            responses = QuestionnaireResponse(
                communication_style={
                    'openness': initial_data.personality.openness,
                    'extraversion': initial_data.personality.extraversion,
                    'agreeableness': initial_data.personality.agreeableness,
                    'formality': initial_data.tone.formality,
                    'warmth': initial_data.tone.warmth,
                    'directness': initial_data.tone.directness,
                    'preferred_greeting': initial_data.communication.preferred_greeting,
                    'sign_off_style': initial_data.communication.sign_off_style,
                },
                decision_patterns={
                    'conscientiousness': initial_data.personality.conscientiousness,
                    'risk_tolerance': initial_data.decision_style.risk_tolerance,
                    'speed_vs_accuracy': initial_data.decision_style.speed_vs_accuracy,
                    'collaboration_preference': initial_data.decision_style.collaboration_preference,
                },
                preferences={
                    'neuroticism': initial_data.personality.neuroticism,
                    'humor_level': initial_data.tone.humor_level,
                    'response_length': initial_data.communication.response_length,
                    'emoji_usage': initial_data.communication.emoji_usage,
                    'vocabulary_patterns': initial_data.vocabulary_patterns,
                }
            )
            
            service.create_from_questionnaire(str(user.id), responses)
            
            # Create one update
            service.update_profile(
                str(user.id),
                {'personality': {'openness': 0.9}}
            )
            
            # Rollback to version 1
            rolled_back = service.rollback_to_version(str(user.id), 1)
            
            # Verify change log exists
            log = CSMChangeLog.objects.filter(
                profile=rolled_back,
                change_type='rollback'
            ).first()
            
            assert log is not None
            assert log.change_summary['rolled_back_to'] == 1
            assert log.from_version == 2
            assert log.to_version == 3
        finally:
            User.objects.filter(id=user.id).delete()
