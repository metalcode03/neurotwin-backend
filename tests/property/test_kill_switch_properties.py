"""
Property-based tests for kill switch service.

Feature: neurotwin-platform
Validates: Requirements 12.1-12.3, 12.6

These tests use Hypothesis to verify kill switch properties hold
across a wide range of inputs.
"""

import pytest
import uuid
from hypothesis import given, strategies as st, settings, assume
from datetime import timedelta
from django.utils import timezone

from apps.safety.services import KillSwitchService, AuditService
from apps.safety.models import (
    ReversibleAction, 
    KillSwitchEvent, 
    ActionType, 
    IntegrationType,
    AuditOutcome,
)
from apps.authentication.models import User
from apps.twin.models import Twin
from apps.csm.models import CSMProfile


# Custom strategies for generating test data
action_type_strategy = st.sampled_from(list(ActionType.values))
integration_strategy = st.sampled_from(list(IntegrationType.values))
reason_strategy = st.text(min_size=0, max_size=100, alphabet=st.characters(
    whitelist_categories=('L', 'N', 'P', 'S', 'Z'),
    blacklist_characters='\x00'
))
triggered_by_strategy = st.sampled_from(['user', 'system', 'api', 'scheduled'])
undo_window_strategy = st.integers(min_value=1, max_value=1440)  # 1 minute to 24 hours


@pytest.fixture
def kill_switch_service():
    """Provide a KillSwitchService instance."""
    return KillSwitchService()


def create_test_user(email_suffix: str) -> User:
    """Create a test user with unique email."""
    email = f"kill_switch_test_{email_suffix}@example.com"
    User.objects.filter(email=email).delete()
    return User.objects.create_user(email=email, password="testpass123")


def create_test_twin(user: User) -> Twin:
    """Create a test Twin for a user."""
    # First create a CSM profile
    csm_profile = CSMProfile.objects.create(
        user=user,
        version=1,
        profile_data={
            'personality': {
                'openness': 0.5,
                'conscientiousness': 0.5,
                'extraversion': 0.5,
                'agreeableness': 0.5,
                'neuroticism': 0.5,
            },
            'tone': {
                'formality': 0.5,
                'warmth': 0.5,
                'directness': 0.5,
                'humor_level': 0.5,
            },
            'vocabulary_patterns': [],
            'communication': {
                'preferred_greeting': 'Hello',
                'sign_off_style': 'Best',
                'response_length': 'moderate',
                'emoji_usage': 'minimal',
            },
            'decision_style': {
                'risk_tolerance': 0.5,
                'speed_vs_accuracy': 0.5,
                'collaboration_preference': 0.5,
            },
            'custom_rules': {},
        }
    )
    
    # Delete any existing Twin for this user
    Twin.objects.filter(user=user).delete()
    
    return Twin.objects.create(
        user=user,
        model='gemini-3-flash',
        cognitive_blend=50,
        csm_profile=csm_profile,
        is_active=True,
        kill_switch_active=False,
    )


@pytest.mark.django_db(transaction=True)
class TestKillSwitchBehavior:
    """
    Property 41: Kill switch behavior
    
    *For any* kill switch activation, the system SHALL:
    - Immediately halt all Twin automations
    - Terminate all in-progress workflows and calls
    - Prevent new automated actions until manually re-enabled
    
    **Validates: Requirements 12.1, 12.2, 12.3**
    """
    
    @settings(max_examples=20, deadline=None)
    @given(
        reason=reason_strategy,
        triggered_by=triggered_by_strategy
    )
    def test_kill_switch_activation_sets_flag(
        self,
        reason: str,
        triggered_by: str
    ):
        """
        Feature: neurotwin-platform, Property 41: Kill switch behavior
        
        For any kill switch activation, the Twin's kill_switch_active flag
        should be set to True.
        """
        service = KillSwitchService()
        
        # Create test user and twin
        user = create_test_user(f"p41_activate_{hash((reason, triggered_by)) % 10000}")
        twin = create_test_twin(user)
        
        try:
            # Verify initial state
            assert not twin.kill_switch_active, "Kill switch should be inactive initially"
            
            # Activate kill switch
            status = service.activate_kill_switch(
                str(user.id),
                reason=reason,
                triggered_by=triggered_by
            )
            
            # Verify activation
            assert status.is_active, "Status should indicate kill switch is active"
            assert status.activated_by == triggered_by, "Triggered by should match"
            assert status.reason == reason, "Reason should match"
            
            # Verify Twin flag is set
            twin.refresh_from_db()
            assert twin.kill_switch_active, "Twin kill_switch_active should be True"
            
            # Verify is_kill_switch_active returns True
            assert service.is_kill_switch_active(str(user.id)), (
                "is_kill_switch_active should return True after activation"
            )
        finally:
            User.objects.filter(id=user.id).delete()
    
    @settings(max_examples=20, deadline=None)
    @given(
        reason=reason_strategy,
        triggered_by=triggered_by_strategy
    )
    def test_kill_switch_prevents_automations(
        self,
        reason: str,
        triggered_by: str
    ):
        """
        Feature: neurotwin-platform, Property 41: Kill switch behavior
        
        For any active kill switch, can_execute_automation should return False.
        """
        service = KillSwitchService()
        
        # Create test user and twin
        user = create_test_user(f"p41_prevent_{hash((reason, triggered_by)) % 10000}")
        twin = create_test_twin(user)
        
        try:
            # Before activation, automations should be allowed
            can_execute, msg = service.can_execute_automation(str(user.id))
            assert can_execute, "Automations should be allowed before activation"
            
            # Activate kill switch
            service.activate_kill_switch(str(user.id), reason=reason, triggered_by=triggered_by)
            
            # After activation, automations should be blocked
            can_execute, msg = service.can_execute_automation(str(user.id))
            assert not can_execute, "Automations should be blocked after activation"
            assert "Kill switch is active" in msg, "Message should indicate kill switch is active"
        finally:
            User.objects.filter(id=user.id).delete()
    
    @settings(max_examples=20, deadline=None)
    @given(
        activate_reason=reason_strategy,
        deactivate_reason=reason_strategy,
        triggered_by=triggered_by_strategy
    )
    def test_kill_switch_deactivation_re_enables(
        self,
        activate_reason: str,
        deactivate_reason: str,
        triggered_by: str
    ):
        """
        Feature: neurotwin-platform, Property 41: Kill switch behavior
        
        For any kill switch deactivation, automations should be re-enabled.
        """
        service = KillSwitchService()
        
        # Create test user and twin
        user = create_test_user(f"p41_deactivate_{hash((activate_reason, deactivate_reason, triggered_by)) % 10000}")
        twin = create_test_twin(user)
        
        try:
            # Activate kill switch
            service.activate_kill_switch(str(user.id), reason=activate_reason, triggered_by=triggered_by)
            assert service.is_kill_switch_active(str(user.id)), "Kill switch should be active"
            
            # Deactivate kill switch
            status = service.deactivate_kill_switch(
                str(user.id),
                reason=deactivate_reason,
                triggered_by=triggered_by
            )
            
            # Verify deactivation
            assert not status.is_active, "Status should indicate kill switch is inactive"
            
            # Verify Twin flag is cleared
            twin.refresh_from_db()
            assert not twin.kill_switch_active, "Twin kill_switch_active should be False"
            
            # Verify automations are re-enabled
            can_execute, msg = service.can_execute_automation(str(user.id))
            assert can_execute, "Automations should be allowed after deactivation"
        finally:
            User.objects.filter(id=user.id).delete()
    
    @settings(max_examples=20, deadline=None)
    @given(
        reason=reason_strategy,
        triggered_by=triggered_by_strategy
    )
    def test_kill_switch_creates_event_record(
        self,
        reason: str,
        triggered_by: str
    ):
        """
        Feature: neurotwin-platform, Property 41: Kill switch behavior
        
        For any kill switch activation/deactivation, an event record should be created.
        """
        service = KillSwitchService()
        
        # Create test user and twin
        user = create_test_user(f"p41_event_{hash((reason, triggered_by)) % 10000}")
        twin = create_test_twin(user)
        
        try:
            # Count initial events
            initial_count = KillSwitchEvent.objects.filter(user_id=user.id).count()
            
            # Activate kill switch
            service.activate_kill_switch(str(user.id), reason=reason, triggered_by=triggered_by)
            
            # Verify activation event was created
            events = KillSwitchEvent.objects.filter(user_id=user.id).order_by('-timestamp')
            assert events.count() == initial_count + 1, "Activation event should be created"
            
            latest_event = events.first()
            assert latest_event.event_type == KillSwitchEvent.EventType.ACTIVATED
            assert latest_event.reason == reason
            assert latest_event.triggered_by == triggered_by
            
            # Deactivate kill switch
            service.deactivate_kill_switch(str(user.id), reason="test deactivation", triggered_by=triggered_by)
            
            # Verify deactivation event was created
            events = KillSwitchEvent.objects.filter(user_id=user.id).order_by('-timestamp')
            assert events.count() == initial_count + 2, "Deactivation event should be created"
            
            latest_event = events.first()
            assert latest_event.event_type == KillSwitchEvent.EventType.DEACTIVATED
        finally:
            User.objects.filter(id=user.id).delete()
    
    @settings(max_examples=20, deadline=None)
    @given(triggered_by=triggered_by_strategy)
    def test_kill_switch_idempotent_activation(
        self,
        triggered_by: str
    ):
        """
        Feature: neurotwin-platform, Property 41: Kill switch behavior
        
        For any already-active kill switch, re-activation should be idempotent
        (the flag remains True).
        """
        service = KillSwitchService()
        
        # Create test user and twin
        user = create_test_user(f"p41_idempotent_{hash(triggered_by) % 10000}")
        twin = create_test_twin(user)
        
        try:
            # Activate kill switch twice
            service.activate_kill_switch(str(user.id), reason="first", triggered_by=triggered_by)
            service.activate_kill_switch(str(user.id), reason="second", triggered_by=triggered_by)
            
            # Should still be active
            assert service.is_kill_switch_active(str(user.id)), (
                "Kill switch should remain active after multiple activations"
            )
            
            twin.refresh_from_db()
            assert twin.kill_switch_active, "Twin flag should remain True"
        finally:
            User.objects.filter(id=user.id).delete()


@pytest.mark.django_db(transaction=True)
class TestReversibleActionUndo:
    """
    Property 42: Reversible action undo
    
    *For any* reversible Twin action within the configured time window,
    the undo operation SHALL successfully reverse the action.
    
    **Validates: Requirements 12.6**
    """
    
    @settings(max_examples=20, deadline=None)
    @given(
        action_type=action_type_strategy,
        integration=integration_strategy,
        undo_window=undo_window_strategy
    )
    def test_undo_within_window_succeeds(
        self,
        action_type: str,
        integration: str,
        undo_window: int
    ):
        """
        Feature: neurotwin-platform, Property 42: Reversible action undo
        
        For any reversible action within the undo window, undo should succeed.
        """
        service = KillSwitchService()
        
        # Create test user
        user = create_test_user(f"p42_undo_{hash((action_type, integration, undo_window)) % 10000}")
        
        try:
            original_state = {'field': 'original_value', 'count': 1}
            new_state = {'field': 'new_value', 'count': 2}
            
            # Record reversible action
            action = service.record_reversible_action(
                user_id=str(user.id),
                action_type=action_type,
                original_state=original_state,
                new_state=new_state,
                target_integration=integration,
                undo_window_minutes=undo_window,
            )
            
            # Verify action can be undone
            assert action.can_undo, "Action should be undoable within window"
            
            # Get undo window
            deadline = service.get_undo_window(str(action.id))
            assert deadline is not None, "Undo deadline should be returned"
            assert deadline > timezone.now(), "Deadline should be in the future"
            
            # Undo the action
            result = service.undo_action(str(action.id))
            assert result, "Undo should succeed within window"
            
            # Verify action is marked as undone
            action.refresh_from_db()
            assert action.is_undone, "Action should be marked as undone"
            assert action.undone_at is not None, "Undone timestamp should be set"
            
            # Verify action can no longer be undone
            assert not action.can_undo, "Action should not be undoable after undo"
        finally:
            User.objects.filter(id=user.id).delete()
    
    @settings(max_examples=20, deadline=None)
    @given(
        action_type=action_type_strategy,
        integration=integration_strategy
    )
    def test_undo_outside_window_fails(
        self,
        action_type: str,
        integration: str
    ):
        """
        Feature: neurotwin-platform, Property 42: Reversible action undo
        
        For any reversible action outside the undo window, undo should fail.
        """
        service = KillSwitchService()
        
        # Create test user
        user = create_test_user(f"p42_expired_{hash((action_type, integration)) % 10000}")
        
        try:
            original_state = {'field': 'original_value'}
            new_state = {'field': 'new_value'}
            
            # Record reversible action with very short window
            action = service.record_reversible_action(
                user_id=str(user.id),
                action_type=action_type,
                original_state=original_state,
                new_state=new_state,
                target_integration=integration,
                undo_window_minutes=1,  # 1 minute window
            )
            
            # Manually expire the action by setting deadline in the past
            action.undo_deadline = timezone.now() - timedelta(minutes=1)
            action.save()
            
            # Verify action cannot be undone
            assert not action.can_undo, "Action should not be undoable after window expires"
            
            # Get undo window should return None
            deadline = service.get_undo_window(str(action.id))
            assert deadline is None, "Undo deadline should be None for expired action"
            
            # Undo should fail
            result = service.undo_action(str(action.id))
            assert not result, "Undo should fail outside window"
            
            # Verify action is not marked as undone
            action.refresh_from_db()
            assert not action.is_undone, "Action should not be marked as undone"
        finally:
            User.objects.filter(id=user.id).delete()
    
    @settings(max_examples=20, deadline=None)
    @given(
        action_type=action_type_strategy,
        integration=integration_strategy
    )
    def test_undo_already_undone_fails(
        self,
        action_type: str,
        integration: str
    ):
        """
        Feature: neurotwin-platform, Property 42: Reversible action undo
        
        For any already-undone action, undo should fail (idempotent).
        """
        service = KillSwitchService()
        
        # Create test user
        user = create_test_user(f"p42_double_{hash((action_type, integration)) % 10000}")
        
        try:
            original_state = {'field': 'original_value'}
            new_state = {'field': 'new_value'}
            
            # Record reversible action
            action = service.record_reversible_action(
                user_id=str(user.id),
                action_type=action_type,
                original_state=original_state,
                new_state=new_state,
                target_integration=integration,
                undo_window_minutes=30,
            )
            
            # First undo should succeed
            result1 = service.undo_action(str(action.id))
            assert result1, "First undo should succeed"
            
            # Second undo should fail
            result2 = service.undo_action(str(action.id))
            assert not result2, "Second undo should fail (already undone)"
        finally:
            User.objects.filter(id=user.id).delete()
    
    @settings(max_examples=20, deadline=None)
    @given(
        action_type=action_type_strategy,
        integration=integration_strategy
    )
    def test_undo_nonexistent_action_fails(
        self,
        action_type: str,
        integration: str
    ):
        """
        Feature: neurotwin-platform, Property 42: Reversible action undo
        
        For any non-existent action ID, undo should fail gracefully.
        """
        service = KillSwitchService()
        
        # Try to undo a non-existent action
        fake_id = str(uuid.uuid4())
        result = service.undo_action(fake_id)
        assert not result, "Undo should fail for non-existent action"
        
        # Get undo window should return None
        deadline = service.get_undo_window(fake_id)
        assert deadline is None, "Undo deadline should be None for non-existent action"
    
    @settings(max_examples=20, deadline=None)
    @given(
        action_type=action_type_strategy,
        integration=integration_strategy,
        undo_window=undo_window_strategy
    )
    def test_time_remaining_calculation(
        self,
        action_type: str,
        integration: str,
        undo_window: int
    ):
        """
        Feature: neurotwin-platform, Property 42: Reversible action undo
        
        For any reversible action, time_remaining should be calculated correctly.
        """
        service = KillSwitchService()
        
        # Create test user
        user = create_test_user(f"p42_time_{hash((action_type, integration, undo_window)) % 10000}")
        
        try:
            original_state = {'field': 'original_value'}
            new_state = {'field': 'new_value'}
            
            # Record reversible action
            action = service.record_reversible_action(
                user_id=str(user.id),
                action_type=action_type,
                original_state=original_state,
                new_state=new_state,
                target_integration=integration,
                undo_window_minutes=undo_window,
            )
            
            # Time remaining should be positive and less than or equal to undo window
            time_remaining = action.time_remaining
            assert time_remaining is not None, "Time remaining should not be None"
            assert time_remaining.total_seconds() > 0, "Time remaining should be positive"
            assert time_remaining.total_seconds() <= undo_window * 60, (
                "Time remaining should not exceed undo window"
            )
        finally:
            User.objects.filter(id=user.id).delete()
    
    @settings(max_examples=20, deadline=None)
    @given(
        action_type=action_type_strategy,
        integration=integration_strategy
    )
    def test_get_reversible_actions_filters_correctly(
        self,
        action_type: str,
        integration: str
    ):
        """
        Feature: neurotwin-platform, Property 42: Reversible action undo
        
        For any user, get_reversible_actions should filter correctly.
        """
        service = KillSwitchService()
        
        # Create test user
        user = create_test_user(f"p42_filter_{hash((action_type, integration)) % 10000}")
        
        try:
            # Create an active action
            active_action = service.record_reversible_action(
                user_id=str(user.id),
                action_type=action_type,
                original_state={'state': 'active'},
                new_state={'state': 'new'},
                target_integration=integration,
                undo_window_minutes=30,
            )
            
            # Create an undone action
            undone_action = service.record_reversible_action(
                user_id=str(user.id),
                action_type=action_type,
                original_state={'state': 'undone'},
                new_state={'state': 'new'},
                target_integration=integration,
                undo_window_minutes=30,
            )
            service.undo_action(str(undone_action.id))
            
            # Create an expired action
            expired_action = service.record_reversible_action(
                user_id=str(user.id),
                action_type=action_type,
                original_state={'state': 'expired'},
                new_state={'state': 'new'},
                target_integration=integration,
                undo_window_minutes=1,
            )
            expired_action.undo_deadline = timezone.now() - timedelta(minutes=1)
            expired_action.save()
            
            # Default filter: only active, non-expired
            actions = service.get_reversible_actions(str(user.id))
            action_ids = [a.action_id for a in actions]
            assert str(active_action.id) in action_ids, "Active action should be included"
            assert str(undone_action.id) not in action_ids, "Undone action should be excluded"
            assert str(expired_action.id) not in action_ids, "Expired action should be excluded"
            
            # Include undone
            actions = service.get_reversible_actions(str(user.id), include_undone=True)
            action_ids = [a.action_id for a in actions]
            assert str(undone_action.id) in action_ids, "Undone action should be included"
            
            # Include expired
            actions = service.get_reversible_actions(str(user.id), include_expired=True)
            action_ids = [a.action_id for a in actions]
            assert str(expired_action.id) in action_ids, "Expired action should be included"
        finally:
            User.objects.filter(id=user.id).delete()
