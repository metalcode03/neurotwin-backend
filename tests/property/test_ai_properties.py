"""
Property-based tests for AI Service cognitive blend behavior.

Feature: neurotwin-platform
Validates: Requirements 4.3, 4.4, 4.5

These tests use Hypothesis to verify cognitive blend properties hold
across a wide range of inputs.

Property 9: Cognitive blend behavior ranges
*For any* cognitive blend value:
- 0-30%: Twin uses pure AI logic with minimal personality mimicry
- 31-70%: Twin balances user personality with AI reasoning
- 71-100%: Twin heavily mimics personality and requires confirmation before actions
"""

import pytest
from hypothesis import given, strategies as st, settings, assume

from core.ai import AIService, BlendMode
from core.ai.dataclasses import BlendedProfile


# Custom strategies for generating test data

# Strategy for cognitive blend values (0-100)
blend_value_strategy = st.integers(min_value=0, max_value=100)

# Strategy for float values between 0.0 and 1.0
unit_float = st.floats(min_value=0.0, max_value=1.0, allow_nan=False, allow_infinity=False)

# Strategy for personality traits
personality_strategy = st.fixed_dictionaries({
    'openness': unit_float,
    'conscientiousness': unit_float,
    'extraversion': unit_float,
    'agreeableness': unit_float,
    'neuroticism': unit_float,
})

# Strategy for tone preferences
tone_strategy = st.fixed_dictionaries({
    'formality': unit_float,
    'warmth': unit_float,
    'directness': unit_float,
    'humor_level': unit_float,
})

# Strategy for communication habits
communication_strategy = st.fixed_dictionaries({
    'preferred_greeting': st.text(min_size=0, max_size=20),
    'sign_off_style': st.text(min_size=0, max_size=20),
    'response_length': st.sampled_from(['brief', 'moderate', 'detailed']),
    'emoji_usage': st.sampled_from(['none', 'minimal', 'moderate', 'frequent']),
})

# Strategy for decision style
decision_style_strategy = st.fixed_dictionaries({
    'risk_tolerance': unit_float,
    'speed_vs_accuracy': unit_float,
    'collaboration_preference': unit_float,
})

# Strategy for vocabulary patterns
vocabulary_strategy = st.lists(
    st.text(min_size=1, max_size=20, alphabet=st.characters(
        whitelist_categories=('L',),
    )),
    min_size=0,
    max_size=10
)

# Strategy for complete CSM profile data
csm_profile_data_strategy = st.fixed_dictionaries({
    'personality': personality_strategy,
    'tone': tone_strategy,
    'communication': communication_strategy,
    'decision_style': decision_style_strategy,
    'vocabulary_patterns': vocabulary_strategy,
    'custom_rules': st.dictionaries(
        keys=st.text(min_size=1, max_size=10, alphabet=st.characters(whitelist_categories=('L',))),
        values=st.text(min_size=0, max_size=50),
        min_size=0,
        max_size=5
    ),
})


class TestCognitiveBlendBehaviorRanges:
    """
    Property 9: Cognitive blend behavior ranges
    
    *For any* cognitive blend value:
    - 0-30%: Twin uses pure AI logic with minimal personality mimicry
    - 31-70%: Twin balances user personality with AI reasoning
    - 71-100%: Twin heavily mimics personality and requires confirmation before actions
    
    **Validates: Requirements 4.3, 4.4, 4.5**
    """
    
    @settings(deadline=None)
    @given(blend=st.integers(min_value=0, max_value=30))
    def test_low_blend_uses_ai_logic_mode(self, blend: int):
        """
        Feature: neurotwin-platform, Property 9: Cognitive blend behavior ranges
        
        For any blend value 0-30%, the system should use AI_LOGIC mode
        with minimal personality mimicry.
        
        Requirements: 4.3
        """
        mode = BlendMode.from_blend_value(blend)
        
        # Verify AI_LOGIC mode is selected
        assert mode == BlendMode.AI_LOGIC, (
            f"Blend {blend}% should use AI_LOGIC mode, got {mode}"
        )
        
        # Verify no confirmation required
        assert not mode.requires_confirmation(), (
            f"AI_LOGIC mode should not require confirmation"
        )
    
    @settings(deadline=None)
    @given(blend=st.integers(min_value=31, max_value=70))
    def test_mid_blend_uses_balanced_mode(self, blend: int):
        """
        Feature: neurotwin-platform, Property 9: Cognitive blend behavior ranges
        
        For any blend value 31-70%, the system should use BALANCED mode
        balancing user personality with AI reasoning.
        
        Requirements: 4.4
        """
        mode = BlendMode.from_blend_value(blend)
        
        # Verify BALANCED mode is selected
        assert mode == BlendMode.BALANCED, (
            f"Blend {blend}% should use BALANCED mode, got {mode}"
        )
        
        # Verify no confirmation required
        assert not mode.requires_confirmation(), (
            f"BALANCED mode should not require confirmation"
        )
    
    @settings(deadline=None)
    @given(blend=st.integers(min_value=71, max_value=100))
    def test_high_blend_uses_personality_heavy_mode(self, blend: int):
        """
        Feature: neurotwin-platform, Property 9: Cognitive blend behavior ranges
        
        For any blend value 71-100%, the system should use PERSONALITY_HEAVY mode
        and require confirmation before actions.
        
        Requirements: 4.5
        """
        mode = BlendMode.from_blend_value(blend)
        
        # Verify PERSONALITY_HEAVY mode is selected
        assert mode == BlendMode.PERSONALITY_HEAVY, (
            f"Blend {blend}% should use PERSONALITY_HEAVY mode, got {mode}"
        )
        
        # Verify confirmation IS required
        assert mode.requires_confirmation(), (
            f"PERSONALITY_HEAVY mode should require confirmation"
        )
    
    @settings(deadline=None)
    @given(blend=blend_value_strategy, csm_data=csm_profile_data_strategy)
    def test_blend_applies_personality_weight_correctly(
        self,
        blend: int,
        csm_data: dict
    ):
        """
        Feature: neurotwin-platform, Property 9: Cognitive blend behavior ranges
        
        For any blend value and CSM profile, the personality weight should
        be proportional to the blend value (blend/100).
        
        Requirements: 4.2, 4.3, 4.4, 4.5
        """
        service = AIService()
        blended = service.apply_blend(csm_data, blend)
        
        expected_weight = blend / 100.0
        
        # Verify personality weight matches blend
        assert blended.personality_weight == expected_weight, (
            f"Personality weight should be {expected_weight}, got {blended.personality_weight}"
        )
        
        # Verify blend value is stored
        assert blended.blend_value == blend, (
            f"Blend value should be {blend}, got {blended.blend_value}"
        )
    
    @settings(deadline=None)
    @given(blend=blend_value_strategy, csm_data=csm_profile_data_strategy)
    def test_blend_mode_matches_blend_value(
        self,
        blend: int,
        csm_data: dict
    ):
        """
        Feature: neurotwin-platform, Property 9: Cognitive blend behavior ranges
        
        For any blend value, the blended profile's mode should match
        the expected mode for that blend range.
        
        Requirements: 4.3, 4.4, 4.5
        """
        service = AIService()
        blended = service.apply_blend(csm_data, blend)
        
        expected_mode = BlendMode.from_blend_value(blend)
        
        # Verify mode matches
        assert blended.mode == expected_mode, (
            f"Blend {blend}% should have mode {expected_mode}, got {blended.mode}"
        )
    
    @settings(deadline=None)
    @given(blend=blend_value_strategy, csm_data=csm_profile_data_strategy)
    def test_requires_confirmation_matches_mode(
        self,
        blend: int,
        csm_data: dict
    ):
        """
        Feature: neurotwin-platform, Property 9: Cognitive blend behavior ranges
        
        For any blend value, requires_confirmation should be True only
        when blend > 70% (PERSONALITY_HEAVY mode).
        
        Requirements: 4.5
        """
        service = AIService()
        blended = service.apply_blend(csm_data, blend)
        
        expected_requires_confirmation = blend > 70
        
        # Verify requires_confirmation matches expectation
        assert blended.requires_confirmation == expected_requires_confirmation, (
            f"Blend {blend}% should have requires_confirmation={expected_requires_confirmation}, "
            f"got {blended.requires_confirmation}"
        )
    
    @settings(deadline=None)
    @given(blend=blend_value_strategy, csm_data=csm_profile_data_strategy)
    def test_personality_traits_blend_toward_neutral_at_low_blend(
        self,
        blend: int,
        csm_data: dict
    ):
        """
        Feature: neurotwin-platform, Property 9: Cognitive blend behavior ranges
        
        For any blend value, personality traits should be blended toward
        neutral (0.5) proportionally to (1 - blend/100).
        
        At blend=0, all traits should be exactly 0.5 (neutral).
        At blend=100, all traits should match the original profile.
        
        Requirements: 4.2, 4.3
        """
        service = AIService()
        blended = service.apply_blend(csm_data, blend)
        
        original_personality = csm_data.get('personality', {})
        blended_personality = blended.personality
        
        weight = blend / 100.0
        neutral = 0.5
        
        for trait, original_value in original_personality.items():
            if isinstance(original_value, (int, float)):
                expected = neutral + (original_value - neutral) * weight
                actual = blended_personality.get(trait, neutral)
                
                # Allow small floating point tolerance
                assert abs(actual - expected) < 0.0001, (
                    f"Trait {trait} at blend {blend}%: expected {expected}, got {actual}"
                )
    
    @settings(deadline=None)
    @given(blend=blend_value_strategy, csm_data=csm_profile_data_strategy)
    def test_tone_preferences_blend_toward_neutral_at_low_blend(
        self,
        blend: int,
        csm_data: dict
    ):
        """
        Feature: neurotwin-platform, Property 9: Cognitive blend behavior ranges
        
        For any blend value, tone preferences should be blended toward
        neutral (0.5) proportionally to (1 - blend/100).
        
        Requirements: 4.2, 4.3
        """
        service = AIService()
        blended = service.apply_blend(csm_data, blend)
        
        original_tone = csm_data.get('tone', {})
        blended_tone = blended.tone
        
        weight = blend / 100.0
        neutral = 0.5
        
        for pref, original_value in original_tone.items():
            if isinstance(original_value, (int, float)):
                expected = neutral + (original_value - neutral) * weight
                actual = blended_tone.get(pref, neutral)
                
                # Allow small floating point tolerance
                assert abs(actual - expected) < 0.0001, (
                    f"Tone {pref} at blend {blend}%: expected {expected}, got {actual}"
                )
    
    @settings(deadline=None)
    @given(csm_data=csm_profile_data_strategy)
    def test_zero_blend_produces_neutral_traits(self, csm_data: dict):
        """
        Feature: neurotwin-platform, Property 9: Cognitive blend behavior ranges
        
        At blend=0%, all personality and tone traits should be exactly
        neutral (0.5), regardless of the original profile values.
        
        Requirements: 4.3
        """
        service = AIService()
        blended = service.apply_blend(csm_data, 0)
        
        neutral = 0.5
        
        # Check personality traits are neutral
        for trait, value in blended.personality.items():
            if isinstance(value, (int, float)):
                assert abs(value - neutral) < 0.0001, (
                    f"At blend 0%, personality trait {trait} should be {neutral}, got {value}"
                )
        
        # Check tone preferences are neutral
        for pref, value in blended.tone.items():
            if isinstance(value, (int, float)):
                assert abs(value - neutral) < 0.0001, (
                    f"At blend 0%, tone preference {pref} should be {neutral}, got {value}"
                )
    
    @settings(deadline=None)
    @given(csm_data=csm_profile_data_strategy)
    def test_full_blend_preserves_original_traits(self, csm_data: dict):
        """
        Feature: neurotwin-platform, Property 9: Cognitive blend behavior ranges
        
        At blend=100%, all personality and tone traits should match
        the original profile values exactly.
        
        Requirements: 4.5
        """
        service = AIService()
        blended = service.apply_blend(csm_data, 100)
        
        original_personality = csm_data.get('personality', {})
        original_tone = csm_data.get('tone', {})
        
        # Check personality traits match original
        for trait, original_value in original_personality.items():
            if isinstance(original_value, (int, float)):
                actual = blended.personality.get(trait)
                assert abs(actual - original_value) < 0.0001, (
                    f"At blend 100%, personality trait {trait} should be {original_value}, got {actual}"
                )
        
        # Check tone preferences match original
        for pref, original_value in original_tone.items():
            if isinstance(original_value, (int, float)):
                actual = blended.tone.get(pref)
                assert abs(actual - original_value) < 0.0001, (
                    f"At blend 100%, tone preference {pref} should be {original_value}, got {actual}"
                )
    
    @settings(deadline=None)
    @given(blend=blend_value_strategy, csm_data=csm_profile_data_strategy)
    def test_response_generation_includes_blend_metadata(
        self,
        blend: int,
        csm_data: dict
    ):
        """
        Feature: neurotwin-platform, Property 9: Cognitive blend behavior ranges
        
        For any response generation, the response should include
        the blend mode and value in its metadata.
        
        Requirements: 4.3, 4.4, 4.5
        """
        service = AIService()
        response = service.generate_response(
            prompt="Test prompt",
            csm_profile_data=csm_data,
            cognitive_blend=blend
        )
        
        expected_mode = BlendMode.from_blend_value(blend)
        
        # Verify blend metadata is included
        assert response.blend_mode == expected_mode, (
            f"Response should have blend_mode {expected_mode}, got {response.blend_mode}"
        )
        assert response.blend_value == blend, (
            f"Response should have blend_value {blend}, got {response.blend_value}"
        )
        assert response.requires_confirmation == (blend > 70), (
            f"Response requires_confirmation should be {blend > 70}, got {response.requires_confirmation}"
        )


class TestBlendModeEdgeCases:
    """
    Edge case tests for blend mode boundaries.
    
    **Validates: Requirements 4.3, 4.4, 4.5**
    """
    
    def test_blend_boundary_30_is_ai_logic(self):
        """Blend value 30 should be AI_LOGIC mode."""
        assert BlendMode.from_blend_value(30) == BlendMode.AI_LOGIC
    
    def test_blend_boundary_31_is_balanced(self):
        """Blend value 31 should be BALANCED mode."""
        assert BlendMode.from_blend_value(31) == BlendMode.BALANCED
    
    def test_blend_boundary_70_is_balanced(self):
        """Blend value 70 should be BALANCED mode."""
        assert BlendMode.from_blend_value(70) == BlendMode.BALANCED
    
    def test_blend_boundary_71_is_personality_heavy(self):
        """Blend value 71 should be PERSONALITY_HEAVY mode."""
        assert BlendMode.from_blend_value(71) == BlendMode.PERSONALITY_HEAVY
    
    def test_blend_0_is_valid(self):
        """Blend value 0 should be valid and use AI_LOGIC mode."""
        assert BlendMode.from_blend_value(0) == BlendMode.AI_LOGIC
    
    def test_blend_100_is_valid(self):
        """Blend value 100 should be valid and use PERSONALITY_HEAVY mode."""
        assert BlendMode.from_blend_value(100) == BlendMode.PERSONALITY_HEAVY
    
    def test_blend_negative_raises_error(self):
        """Blend value -1 should raise ValueError."""
        with pytest.raises(ValueError):
            BlendMode.from_blend_value(-1)
    
    def test_blend_over_100_raises_error(self):
        """Blend value 101 should raise ValueError."""
        with pytest.raises(ValueError):
            BlendMode.from_blend_value(101)
    
    def test_apply_blend_negative_raises_error(self):
        """apply_blend with negative blend should raise ValueError."""
        service = AIService()
        with pytest.raises(ValueError):
            service.apply_blend({}, -1)
    
    def test_apply_blend_over_100_raises_error(self):
        """apply_blend with blend > 100 should raise ValueError."""
        service = AIService()
        with pytest.raises(ValueError):
            service.apply_blend({}, 101)
