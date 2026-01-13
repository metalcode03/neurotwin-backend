"""
Property-based tests for Twin app.

Feature: neurotwin-platform
Validates: Requirements 2.2, 2.5, 4.1, 4.2

These tests use Hypothesis to verify Twin properties hold
across a wide range of inputs.
"""

import pytest
from hypothesis import given, strategies as st, settings, assume
from django.utils import timezone

from apps.twin.models import Twin, OnboardingProgress
from apps.twin.services import TwinService
from apps.twin.dataclasses import AIModel, QuestionnaireResponse
from apps.csm.models import CSMProfile
from apps.csm.dataclasses import CSMProfileData
from apps.authentication.models import User


# Custom strategies for generating Twin data

# Strategy for float values between 0.0 and 1.0
unit_float = st.floats(min_value=0.0, max_value=1.0, allow_nan=False, allow_infinity=False)

# Strategy for cognitive blend values (0-100)
cognitive_blend_strategy = st.integers(min_value=0, max_value=100)

# Strategy for AI model selection
ai_model_strategy = st.sampled_from(list(AIModel))

# Strategy for response length
response_length_strategy = st.sampled_from(['brief', 'moderate', 'detailed'])

# Strategy for emoji usage
emoji_usage_strategy = st.sampled_from(['none', 'minimal', 'moderate', 'frequent'])

# Strategy for text fields (greetings, sign-offs) - simplified
text_field_strategy = st.sampled_from(['Hello', 'Hi', 'Hey', 'Greetings', 'Dear'])

# Strategy for sign-off fields
sign_off_strategy = st.sampled_from(['Best regards', 'Thanks', 'Cheers', 'Best', 'Regards'])

# Strategy for vocabulary patterns - simplified
vocabulary_patterns_strategy = st.lists(
    st.sampled_from(['thanks', 'please', 'regards', 'cheers', 'awesome', 'great']),
    min_size=0,
    max_size=5
)

# Strategy for complete questionnaire responses
questionnaire_response_strategy = st.builds(
    QuestionnaireResponse,
    communication_style=st.fixed_dictionaries({
        'openness': unit_float,
        'extraversion': unit_float,
        'agreeableness': unit_float,
        'formality': unit_float,
        'warmth': unit_float,
        'directness': unit_float,
        'preferred_greeting': text_field_strategy,
        'sign_off_style': sign_off_strategy,
    }),
    decision_patterns=st.fixed_dictionaries({
        'conscientiousness': unit_float,
        'risk_tolerance': unit_float,
        'speed_vs_accuracy': unit_float,
        'collaboration_preference': unit_float,
    }),
    preferences=st.fixed_dictionaries({
        'neuroticism': unit_float,
        'humor_level': unit_float,
        'response_length': response_length_strategy,
        'emoji_usage': emoji_usage_strategy,
        'vocabulary_patterns': vocabulary_patterns_strategy,
    }),
)


def create_test_user(email_suffix: str) -> User:
    """Create a test user with unique email."""
    email = f"twin_test_{email_suffix}@example.com"
    User.objects.filter(email=email).delete()
    return User.objects.create_user(email=email, password="testpass123")


def cleanup_user(user: User) -> None:
    """Clean up test user and related data."""
    # Delete twins first (due to foreign key)
    Twin.objects.filter(user=user).delete()
    OnboardingProgress.objects.filter(user=user).delete()
    CSMProfile.objects.filter(user=user).delete()
    User.objects.filter(id=user.id).delete()


@pytest.mark.django_db(transaction=True)
class TestQuestionnaireGeneratesCSM:
    """
    Property 7: Questionnaire generates CSM
    
    *For any* completed onboarding questionnaire, the system SHALL generate
    a valid CSM profile containing all required fields (personality, tone,
    vocabulary, communication, decision style).
    
    **Validates: Requirements 2.2, 4.1**
    """
    
    @settings(max_examples=10, deadline=None)
    @given(
        responses=questionnaire_response_strategy,
        model=ai_model_strategy,
        blend=cognitive_blend_strategy,
    )
    def test_questionnaire_generates_valid_csm(
        self,
        responses: QuestionnaireResponse,
        model: AIModel,
        blend: int
    ):
        """
        Feature: neurotwin-platform, Property 7: Questionnaire generates CSM
        
        For any completed questionnaire, the system should generate a valid
        CSM profile with all required fields populated.
        """
        service = TwinService()
        user = create_test_user(f"csm_gen_{hash(str(responses.to_dict())) % 100000}")
        
        try:
            # Complete onboarding with questionnaire
            twin = service.complete_onboarding(
                user_id=str(user.id),
                responses=responses,
                model=model,
                cognitive_blend=blend,
            )
            
            # Verify Twin was created
            assert twin is not None
            assert str(twin.user_id) == str(user.id)
            
            # Verify CSM profile was created
            assert twin.csm_profile is not None
            csm_profile = twin.csm_profile
            
            # Get profile data
            profile_data = csm_profile.get_profile_data()
            
            # Verify all required fields are present
            # Personality traits
            assert profile_data.personality is not None
            assert 0.0 <= profile_data.personality.openness <= 1.0
            assert 0.0 <= profile_data.personality.conscientiousness <= 1.0
            assert 0.0 <= profile_data.personality.extraversion <= 1.0
            assert 0.0 <= profile_data.personality.agreeableness <= 1.0
            assert 0.0 <= profile_data.personality.neuroticism <= 1.0
            
            # Tone preferences
            assert profile_data.tone is not None
            assert 0.0 <= profile_data.tone.formality <= 1.0
            assert 0.0 <= profile_data.tone.warmth <= 1.0
            assert 0.0 <= profile_data.tone.directness <= 1.0
            assert 0.0 <= profile_data.tone.humor_level <= 1.0
            
            # Communication habits
            assert profile_data.communication is not None
            assert profile_data.communication.preferred_greeting is not None
            assert profile_data.communication.sign_off_style is not None
            assert profile_data.communication.response_length in ['brief', 'moderate', 'detailed']
            assert profile_data.communication.emoji_usage in ['none', 'minimal', 'moderate', 'frequent']
            
            # Decision style
            assert profile_data.decision_style is not None
            assert 0.0 <= profile_data.decision_style.risk_tolerance <= 1.0
            assert 0.0 <= profile_data.decision_style.speed_vs_accuracy <= 1.0
            assert 0.0 <= profile_data.decision_style.collaboration_preference <= 1.0
            
            # Vocabulary patterns (list)
            assert isinstance(profile_data.vocabulary_patterns, list)
            
            # Custom rules (dict)
            assert isinstance(profile_data.custom_rules, dict)
            
        finally:
            cleanup_user(user)
    
    @settings(max_examples=10, deadline=None)
    @given(
        responses=questionnaire_response_strategy,
        model=ai_model_strategy,
        blend=cognitive_blend_strategy,
    )
    def test_questionnaire_values_transferred_to_csm(
        self,
        responses: QuestionnaireResponse,
        model: AIModel,
        blend: int
    ):
        """
        Feature: neurotwin-platform, Property 7: Questionnaire generates CSM
        
        For any questionnaire response, the values should be correctly
        transferred to the CSM profile.
        """
        service = TwinService()
        user = create_test_user(f"csm_transfer_{hash(str(responses.to_dict())) % 100000}")
        
        try:
            # Complete onboarding
            twin = service.complete_onboarding(
                user_id=str(user.id),
                responses=responses,
                model=model,
                cognitive_blend=blend,
            )
            
            profile_data = twin.csm_profile.get_profile_data()
            
            # Verify personality values match questionnaire
            assert profile_data.personality.openness == responses.communication_style['openness']
            assert profile_data.personality.extraversion == responses.communication_style['extraversion']
            assert profile_data.personality.agreeableness == responses.communication_style['agreeableness']
            assert profile_data.personality.conscientiousness == responses.decision_patterns['conscientiousness']
            assert profile_data.personality.neuroticism == responses.preferences['neuroticism']
            
            # Verify tone values match questionnaire
            assert profile_data.tone.formality == responses.communication_style['formality']
            assert profile_data.tone.warmth == responses.communication_style['warmth']
            assert profile_data.tone.directness == responses.communication_style['directness']
            assert profile_data.tone.humor_level == responses.preferences['humor_level']
            
            # Verify communication habits match questionnaire
            assert profile_data.communication.preferred_greeting == responses.communication_style['preferred_greeting']
            assert profile_data.communication.sign_off_style == responses.communication_style['sign_off_style']
            assert profile_data.communication.response_length == responses.preferences['response_length']
            assert profile_data.communication.emoji_usage == responses.preferences['emoji_usage']
            
            # Verify decision style matches questionnaire
            assert profile_data.decision_style.risk_tolerance == responses.decision_patterns['risk_tolerance']
            assert profile_data.decision_style.speed_vs_accuracy == responses.decision_patterns['speed_vs_accuracy']
            assert profile_data.decision_style.collaboration_preference == responses.decision_patterns['collaboration_preference']
            
            # Verify vocabulary patterns match
            assert profile_data.vocabulary_patterns == responses.preferences['vocabulary_patterns']
            
        finally:
            cleanup_user(user)


@pytest.mark.django_db(transaction=True)
class TestCognitiveBlendStorageAndApplication:
    """
    Property 8: Cognitive blend storage and application
    
    *For any* cognitive blend value (0-100), the system SHALL store the value
    and apply it proportionally to all Twin responses.
    
    **Validates: Requirements 2.5, 4.2**
    """
    
    @settings(max_examples=10, deadline=None)
    @given(
        responses=questionnaire_response_strategy,
        model=ai_model_strategy,
        blend=cognitive_blend_strategy,
    )
    def test_cognitive_blend_stored_correctly(
        self,
        responses: QuestionnaireResponse,
        model: AIModel,
        blend: int
    ):
        """
        Feature: neurotwin-platform, Property 8: Cognitive blend storage and application
        
        For any cognitive blend value, the system should store it correctly
        in the Twin model.
        """
        service = TwinService()
        user = create_test_user(f"blend_store_{hash(str(responses.to_dict())) % 100000}")
        
        try:
            # Create Twin with specific blend
            twin = service.complete_onboarding(
                user_id=str(user.id),
                responses=responses,
                model=model,
                cognitive_blend=blend,
            )
            
            # Verify blend is stored correctly
            assert twin.cognitive_blend == blend
            
            # Verify blend can be retrieved
            retrieved_twin = service.get_twin(str(user.id))
            assert retrieved_twin is not None
            assert retrieved_twin.cognitive_blend == blend
            
        finally:
            cleanup_user(user)
    
    @settings(max_examples=10, deadline=None)
    @given(
        responses=questionnaire_response_strategy,
        model=ai_model_strategy,
        initial_blend=cognitive_blend_strategy,
        new_blend=cognitive_blend_strategy,
    )
    def test_cognitive_blend_update(
        self,
        responses: QuestionnaireResponse,
        model: AIModel,
        initial_blend: int,
        new_blend: int
    ):
        """
        Feature: neurotwin-platform, Property 8: Cognitive blend storage and application
        
        For any cognitive blend update, the new value should be stored
        and retrievable.
        """
        service = TwinService()
        user = create_test_user(f"blend_update_{hash(str(responses.to_dict())) % 100000}")
        
        try:
            # Create Twin with initial blend
            twin = service.complete_onboarding(
                user_id=str(user.id),
                responses=responses,
                model=model,
                cognitive_blend=initial_blend,
            )
            
            # Update blend
            updated_twin = service.update_cognitive_blend(str(twin.id), new_blend)
            
            # Verify new blend is stored
            assert updated_twin.cognitive_blend == new_blend
            
            # Verify blend persists after retrieval
            retrieved_twin = service.get_twin(str(user.id))
            assert retrieved_twin.cognitive_blend == new_blend
            
        finally:
            cleanup_user(user)
    
    @settings(max_examples=10, deadline=None)
    @given(
        responses=questionnaire_response_strategy,
        model=ai_model_strategy,
        blend=cognitive_blend_strategy,
    )
    def test_cognitive_blend_mode_classification(
        self,
        responses: QuestionnaireResponse,
        model: AIModel,
        blend: int
    ):
        """
        Feature: neurotwin-platform, Property 8: Cognitive blend storage and application
        
        For any cognitive blend value, the blend mode should be correctly
        classified according to the ranges:
        - 0-30%: ai_logic
        - 31-70%: balanced
        - 71-100%: personality_heavy
        """
        service = TwinService()
        user = create_test_user(f"blend_mode_{hash(str(responses.to_dict())) % 100000}")
        
        try:
            # Create Twin
            twin = service.complete_onboarding(
                user_id=str(user.id),
                responses=responses,
                model=model,
                cognitive_blend=blend,
            )
            
            # Verify blend mode classification
            if blend <= 30:
                assert twin.blend_mode == 'ai_logic'
            elif blend <= 70:
                assert twin.blend_mode == 'balanced'
            else:
                assert twin.blend_mode == 'personality_heavy'
            
        finally:
            cleanup_user(user)
    
    @settings(max_examples=10, deadline=None)
    @given(
        responses=questionnaire_response_strategy,
        model=ai_model_strategy,
        blend=cognitive_blend_strategy,
    )
    def test_cognitive_blend_confirmation_requirement(
        self,
        responses: QuestionnaireResponse,
        model: AIModel,
        blend: int
    ):
        """
        Feature: neurotwin-platform, Property 8: Cognitive blend storage and application
        
        For any cognitive blend value > 80%, the system should require
        confirmation for actions.
        """
        service = TwinService()
        user = create_test_user(f"blend_confirm_{hash(str(responses.to_dict())) % 100000}")
        
        try:
            # Create Twin
            twin = service.complete_onboarding(
                user_id=str(user.id),
                responses=responses,
                model=model,
                cognitive_blend=blend,
            )
            
            # Verify confirmation requirement
            if blend > 80:
                assert twin.requires_confirmation is True
            else:
                assert twin.requires_confirmation is False
            
        finally:
            cleanup_user(user)
    
    @settings(max_examples=10, deadline=None)
    @given(
        responses=questionnaire_response_strategy,
        model=ai_model_strategy,
        blend=cognitive_blend_strategy,
    )
    def test_cognitive_blend_applied_to_profile(
        self,
        responses: QuestionnaireResponse,
        model: AIModel,
        blend: int
    ):
        """
        Feature: neurotwin-platform, Property 8: Cognitive blend storage and application
        
        For any cognitive blend value, the blend should be applied
        proportionally to the CSM profile.
        """
        from apps.csm.services import CSMService
        
        service = TwinService()
        csm_service = CSMService()
        user = create_test_user(f"blend_apply_{hash(str(responses.to_dict())) % 100000}")
        
        try:
            # Create Twin
            twin = service.complete_onboarding(
                user_id=str(user.id),
                responses=responses,
                model=model,
                cognitive_blend=blend,
            )
            
            # Apply blend to profile
            blended = csm_service.apply_blend(twin.csm_profile, blend)
            
            # Verify blend metadata
            assert blended['blend_value'] == blend
            assert blended['personality_weight'] == blend / 100.0
            
            # Verify mode matches
            if blend <= 30:
                assert blended['mode'] == 'ai_logic'
                assert blended['requires_confirmation'] is False
            elif blend <= 70:
                assert blended['mode'] == 'balanced'
                assert blended['requires_confirmation'] is False
            else:
                assert blended['mode'] == 'personality_heavy'
                assert blended['requires_confirmation'] is True
            
            # Verify personality values are blended
            # At blend=0, values should be neutral (0.5)
            # At blend=100, values should match original profile
            profile_data = twin.csm_profile.get_profile_data()
            blend_factor = blend / 100.0
            neutral = 0.5
            
            expected_openness = neutral + (profile_data.personality.openness - neutral) * blend_factor
            assert abs(blended['personality']['openness'] - expected_openness) < 0.0001
            
        finally:
            cleanup_user(user)
