"""
Property-based tests for Learning Loop system.

Feature: neurotwin-platform
Validates: Requirements 6.1, 6.2, 6.3, 6.4, 6.5

These tests use Hypothesis to verify learning loop properties hold
across a wide range of inputs.
"""

import pytest
import asyncio
import uuid
from hypothesis import given, strategies as st, settings, assume, Phase
from django.utils import timezone

from apps.learning.models import LearningEvent
from apps.learning.services import LearningService
from apps.learning.dataclasses import (
    ExtractedFeatures,
    FeedbackType,
    ActionCategory,
    UserAction,
    ProfileUpdateResult,
    FeedbackResult,
)
from apps.csm.services import CSMService
from apps.csm.dataclasses import QuestionnaireResponse
from apps.authentication.models import User


# Custom strategies for generating learning data

# Strategy for action types
action_type_strategy = st.sampled_from([
    'send_message',
    'reply_email',
    'chat_response',
    'approve_request',
    'reject_proposal',
    'decide_option',
    'update_setting',
    'set_preference',
    'rate_response',
    'provide_feedback',
    'click_button',
    'navigate_page',
])

# Strategy for action categories
action_category_strategy = st.sampled_from([
    ActionCategory.COMMUNICATION,
    ActionCategory.DECISION,
    ActionCategory.PREFERENCE,
    ActionCategory.INTERACTION,
    ActionCategory.FEEDBACK,
])

# Strategy for content text - simplified for performance
content_strategy = st.text(
    min_size=0,
    max_size=100,
    alphabet=st.characters(
        whitelist_categories=('L', 'N'),
        whitelist_characters=' .,!?-'
    )
)

# Strategy for context dictionaries - simplified
context_strategy = st.fixed_dictionaries({})

# Strategy for metadata dictionaries - simplified
metadata_strategy = st.fixed_dictionaries({})

# Strategy for UserAction
user_action_strategy = st.builds(
    UserAction,
    action_type=action_type_strategy,
    content=content_strategy,
    context=context_strategy,
    metadata=metadata_strategy,
)

# Strategy for feedback types
feedback_type_strategy = st.sampled_from([
    FeedbackType.POSITIVE,
    FeedbackType.NEGATIVE,
    FeedbackType.CORRECTION,
])


# Shared test user counter for unique emails
_test_counter = [0]


def get_unique_suffix() -> str:
    """Get a unique suffix for test user emails."""
    _test_counter[0] += 1
    return f"{_test_counter[0]}_{uuid.uuid4().hex[:8]}"


def create_test_user(email_suffix: str) -> User:
    """Create a test user with unique email."""
    email = f"learning_test_{email_suffix}@example.com"
    User.objects.filter(email=email).delete()
    return User.objects.create_user(email=email, password="testpass123")


def create_user_with_csm(email_suffix: str) -> User:
    """Create a test user with an initial CSM profile."""
    user = create_test_user(email_suffix)
    
    # Create initial CSM profile
    csm_service = CSMService()
    responses = QuestionnaireResponse(
        communication_style={
            'openness': 0.5,
            'extraversion': 0.5,
            'agreeableness': 0.5,
            'formality': 0.5,
            'warmth': 0.5,
            'directness': 0.5,
            'preferred_greeting': 'Hello',
            'sign_off_style': 'Best regards',
        },
        decision_patterns={
            'conscientiousness': 0.5,
            'risk_tolerance': 0.5,
            'speed_vs_accuracy': 0.5,
            'collaboration_preference': 0.5,
        },
        preferences={
            'neuroticism': 0.5,
            'humor_level': 0.3,
            'response_length': 'moderate',
            'emoji_usage': 'minimal',
            'vocabulary_patterns': [],
        }
    )
    csm_service.create_from_questionnaire(str(user.id), responses)
    
    return user


def cleanup_user(user: User) -> None:
    """Clean up test user and related data."""
    LearningEvent.objects.filter(user_id=user.id).delete()
    User.objects.filter(id=user.id).delete()


@pytest.mark.django_db(transaction=True)
class TestLearningLoopProcessing:
    """
    Property 16: Learning loop processing
    
    *For any* user action, the learning system SHALL extract features,
    update the CSM profile asynchronously, and shift Twin behavior accordingly.
    
    **Validates: Requirements 6.1, 6.2, 6.3, 6.5**
    """
    
    @settings(max_examples=20, deadline=60000, phases=[Phase.generate])
    @given(action=user_action_strategy)
    def test_feature_extraction_from_action(self, action: UserAction):
        """
        Feature: neurotwin-platform, Property 16: Learning loop processing
        
        For any user action, the learning system should extract features
        and create a learning event record.
        """
        user = create_user_with_csm(get_unique_suffix())
        service = LearningService()
        
        try:
            # Process the action
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            try:
                features = loop.run_until_complete(
                    service.process_user_action(str(user.id), action)
                )
            finally:
                loop.close()
            
            # Verify features were extracted
            assert features is not None
            assert isinstance(features, ExtractedFeatures)
            assert features.action_type == action.action_type
            assert isinstance(features.category, ActionCategory)
            assert -1.0 <= features.sentiment <= 1.0
            assert 0.0 <= features.confidence <= 1.0
            
            # Verify learning event was created
            events = LearningEvent.objects.filter(
                user_id=user.id,
                action_type=action.action_type
            )
            assert events.exists()
            
            # Verify event is marked as processed
            event = events.first()
            assert event.is_processed is True
            assert event.processed_at is not None
            
        finally:
            cleanup_user(user)
    
    @settings(max_examples=20, deadline=60000, phases=[Phase.generate])
    @given(action=user_action_strategy)
    def test_profile_update_from_features(self, action: UserAction):
        """
        Feature: neurotwin-platform, Property 16: Learning loop processing
        
        For any extracted features with sufficient confidence,
        the learning system should update the CSM profile.
        """
        user = create_user_with_csm(get_unique_suffix())
        service = LearningService()
        csm_service = CSMService()
        
        try:
            # Get initial profile version
            initial_profile = csm_service.get_profile(str(user.id))
            initial_version = initial_profile.version if initial_profile else 0
            
            # Process the action
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            try:
                features = loop.run_until_complete(
                    service.process_user_action(str(user.id), action)
                )
                
                # Update profile from features
                result = loop.run_until_complete(
                    service.update_profile(str(user.id), features)
                )
            finally:
                loop.close()
            
            # Verify result structure
            assert isinstance(result, ProfileUpdateResult)
            assert result.success is True
            
            # If updates were applied, verify version changed
            if result.updated_fields:
                assert result.new_version is not None
                assert result.new_version > initial_version
                
                # Verify profile was actually updated
                updated_profile = csm_service.get_profile(str(user.id))
                assert updated_profile.version == result.new_version
            
        finally:
            cleanup_user(user)
    
    @settings(max_examples=20, deadline=60000, phases=[Phase.generate])
    @given(
        action=user_action_strategy,
        limit=st.integers(min_value=1, max_value=50)
    )
    def test_learning_history_transparency(self, action: UserAction, limit: int):
        """
        Feature: neurotwin-platform, Property 16: Learning loop processing
        
        For any user, the learning history should be accessible
        for transparency and debugging.
        """
        user = create_user_with_csm(get_unique_suffix())
        service = LearningService()
        
        try:
            # Process an action to create history
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            try:
                loop.run_until_complete(
                    service.process_user_action(str(user.id), action)
                )
            finally:
                loop.close()
            
            # Get learning history
            history = service.get_learning_history(str(user.id), limit=limit)
            
            # Verify history is accessible
            assert isinstance(history, list)
            assert len(history) >= 1  # At least the action we just processed
            assert len(history) <= limit
            
            # Verify history contains our action
            action_types = [event.action_type for event in history]
            assert action.action_type in action_types
            
            # Verify history is ordered by created_at descending
            if len(history) > 1:
                for i in range(len(history) - 1):
                    assert history[i].created_at >= history[i + 1].created_at
            
        finally:
            cleanup_user(user)


@pytest.mark.django_db(transaction=True)
class TestFeedbackReinforcement:
    """
    Property 17: Feedback reinforcement
    
    *For any* user feedback (positive, negative, or correction),
    the learning system SHALL reinforce or correct the associated behavior.
    
    **Validates: Requirements 6.4**
    """
    
    @settings(max_examples=20, deadline=60000, phases=[Phase.generate])
    @given(
        action=user_action_strategy,
        feedback_type=feedback_type_strategy
    )
    def test_feedback_application(
        self,
        action: UserAction,
        feedback_type: FeedbackType
    ):
        """
        Feature: neurotwin-platform, Property 17: Feedback reinforcement
        
        For any user feedback on a learning event, the system should
        record and apply the feedback appropriately.
        """
        user = create_user_with_csm(get_unique_suffix())
        service = LearningService()
        
        try:
            # First, process an action to create a learning event
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            try:
                loop.run_until_complete(
                    service.process_user_action(str(user.id), action)
                )
            finally:
                loop.close()
            
            # Get the learning event
            event = LearningEvent.objects.filter(
                user_id=user.id,
                action_type=action.action_type
            ).first()
            
            assert event is not None
            
            # Apply feedback
            correction_content = "This is a correction" if feedback_type == FeedbackType.CORRECTION else ""
            result = service.apply_feedback(
                str(user.id),
                str(event.id),
                feedback_type,
                correction_content
            )
            
            # Verify result
            assert isinstance(result, FeedbackResult)
            assert result.success is True
            
            # Verify feedback was recorded on the event
            event.refresh_from_db()
            assert event.feedback == feedback_type.value
            assert event.feedback_applied_at is not None
            
            if feedback_type == FeedbackType.CORRECTION:
                assert event.feedback_content == correction_content
            
        finally:
            cleanup_user(user)
    
    @settings(max_examples=20, deadline=60000, phases=[Phase.generate])
    @given(action=user_action_strategy)
    def test_positive_feedback_reinforces(self, action: UserAction):
        """
        Feature: neurotwin-platform, Property 17: Feedback reinforcement
        
        For any positive feedback, the system should reinforce
        the learned patterns.
        """
        user = create_user_with_csm(get_unique_suffix())
        service = LearningService()
        
        try:
            # Process an action
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            try:
                loop.run_until_complete(
                    service.process_user_action(str(user.id), action)
                )
            finally:
                loop.close()
            
            # Get the learning event
            event = LearningEvent.objects.filter(
                user_id=user.id,
                action_type=action.action_type
            ).first()
            
            # Apply positive feedback
            result = service.apply_feedback(
                str(user.id),
                str(event.id),
                FeedbackType.POSITIVE
            )
            
            # Verify reinforcement was applied
            assert result.success is True
            assert result.reinforcement_applied is True
            
        finally:
            cleanup_user(user)
    
    @settings(max_examples=20, deadline=60000, phases=[Phase.generate])
    @given(action=user_action_strategy)
    def test_negative_feedback_reduces_influence(self, action: UserAction):
        """
        Feature: neurotwin-platform, Property 17: Feedback reinforcement
        
        For any negative feedback, the system should reduce
        the influence of the learned patterns.
        """
        user = create_user_with_csm(get_unique_suffix())
        service = LearningService()
        
        try:
            # Process an action
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            try:
                loop.run_until_complete(
                    service.process_user_action(str(user.id), action)
                )
            finally:
                loop.close()
            
            # Get the learning event
            event = LearningEvent.objects.filter(
                user_id=user.id,
                action_type=action.action_type
            ).first()
            
            # Apply negative feedback
            result = service.apply_feedback(
                str(user.id),
                str(event.id),
                FeedbackType.NEGATIVE
            )
            
            # Verify reduction was applied
            assert result.success is True
            assert result.reinforcement_applied is True
            
        finally:
            cleanup_user(user)
    
    @settings(max_examples=20, deadline=60000, phases=[Phase.generate])
    @given(action=user_action_strategy)
    def test_feedback_on_nonexistent_event_fails(self, action: UserAction):
        """
        Feature: neurotwin-platform, Property 17: Feedback reinforcement
        
        For any feedback on a non-existent event, the system should
        return an error result.
        """
        user = create_user_with_csm(get_unique_suffix())
        service = LearningService()
        
        try:
            # Try to apply feedback to a non-existent event
            fake_event_id = str(uuid.uuid4())
            
            result = service.apply_feedback(
                str(user.id),
                fake_event_id,
                FeedbackType.POSITIVE
            )
            
            # Verify error result
            assert result.success is False
            assert result.error is not None
            assert "not found" in result.error.lower()
            
        finally:
            cleanup_user(user)
