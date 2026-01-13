"""
Property-based tests for voice service.

Feature: neurotwin-platform
Validates: Requirements 9.1, 9.5, 9.6, 9.7

These tests use Hypothesis to verify voice properties hold
across a wide range of inputs.
"""

import pytest
import uuid
from hypothesis import given, strategies as st, settings, assume
from datetime import timedelta
from django.utils import timezone

from apps.voice.services import VoiceTwinService
from apps.voice.models import (
    VoiceProfile,
    CallRecord,
    VoiceApprovalHistory,
    CallDirection,
    CallStatus,
)
from apps.authentication.models import User


# Custom strategies for generating test data
phone_number_strategy = st.text(
    alphabet=st.characters(whitelist_categories=('Nd',)),
    min_size=10,
    max_size=15
).map(lambda x: f"+1{x[:10]}")

reason_strategy = st.text(
    min_size=0,
    max_size=100,
    alphabet=st.characters(
        whitelist_categories=('L', 'N', 'P', 'S', 'Z'),
        blacklist_characters='\x00'
    )
)

duration_strategy = st.integers(min_value=1, max_value=1440)  # 1 minute to 24 hours
cognitive_blend_strategy = st.integers(min_value=0, max_value=100)


@pytest.fixture
def voice_service():
    """Provide a VoiceTwinService instance."""
    return VoiceTwinService()


def create_test_user(email_suffix: str) -> User:
    """Create a test user with unique email."""
    email = f"voice_test_{email_suffix}@example.com"
    User.objects.filter(email=email).delete()
    return User.objects.create_user(email=email, password="testpass123")


def setup_voice_profile_with_clone(user: User, service: VoiceTwinService) -> VoiceProfile:
    """Set up a voice profile with phone number and voice clone."""
    # Provision phone number
    service.provision_phone_number(str(user.id))
    
    # Create voice clone
    service.create_voice_clone(
        str(user.id),
        audio_samples=[b"fake_audio_sample"],
        voice_name="Test Voice"
    )
    
    profile = VoiceProfile.objects.get(user=user)
    return profile


@pytest.mark.django_db(transaction=True)
class TestPhoneNumberProvisioning:
    """
    Property 30: Phone number provisioning
    
    *For any* Voice_Twin enablement, the system SHALL provision a virtual phone number.
    
    **Validates: Requirements 9.1**
    """
    
    @settings(max_examples=20, deadline=None)
    @given(area_code=st.sampled_from(['212', '415', '310', '312', '617', None]))
    def test_provisioning_creates_phone_number(self, area_code):
        """
        Feature: neurotwin-platform, Property 30: Phone number provisioning
        
        For any Voice Twin enablement, a phone number should be provisioned.
        """
        service = VoiceTwinService()
        
        # Create test user
        user = create_test_user(f"p30_provision_{hash(area_code) % 10000}")
        
        try:
            # Provision phone number
            result = service.provision_phone_number(
                str(user.id),
                area_code=area_code
            )
            
            # Verify provisioning succeeded
            assert result.success, f"Provisioning should succeed: {result.error}"
            assert result.phone_number is not None, "Phone number should be returned"
            assert result.phone_sid is not None, "Phone SID should be returned"
            
            # Verify profile has phone number
            profile = VoiceProfile.objects.get(user=user)
            assert profile.has_phone_number, "Profile should have phone number"
            assert profile.phone_number == result.phone_number
            assert profile.twilio_phone_sid == result.phone_sid
            assert profile.is_enabled, "Voice Twin should be enabled"
        finally:
            User.objects.filter(id=user.id).delete()
    
    @settings(max_examples=20, deadline=None)
    @given(dummy=st.integers())
    def test_provisioning_is_idempotent(self, dummy):
        """
        Feature: neurotwin-platform, Property 30: Phone number provisioning
        
        For any user with existing phone number, re-provisioning returns same number.
        """
        service = VoiceTwinService()
        
        # Create test user
        user = create_test_user(f"p30_idempotent_{dummy % 10000}")
        
        try:
            # First provisioning
            result1 = service.provision_phone_number(str(user.id))
            assert result1.success
            
            # Second provisioning should return same number
            result2 = service.provision_phone_number(str(user.id))
            assert result2.success
            assert result2.phone_number == result1.phone_number
            assert result2.phone_sid == result1.phone_sid
        finally:
            User.objects.filter(id=user.id).delete()


@pytest.mark.django_db(transaction=True)
class TestCallTranscriptStorage:
    """
    Property 31: Call transcript storage
    
    *For any* phone call (inbound or outbound), the system SHALL generate and store a transcript.
    
    **Validates: Requirements 9.5**
    """
    
    @settings(max_examples=20, deadline=None)
    @given(
        phone_number=phone_number_strategy,
        transcript=st.text(min_size=1, max_size=500)
    )
    def test_inbound_call_stores_transcript(self, phone_number, transcript):
        """
        Feature: neurotwin-platform, Property 31: Call transcript storage
        
        For any inbound call, the transcript should be stored.
        """
        service = VoiceTwinService()
        
        # Create test user with voice profile
        user = create_test_user(f"p31_inbound_{hash((phone_number, transcript)) % 10000}")
        
        try:
            # Set up voice profile with clone and approval
            setup_voice_profile_with_clone(user, service)
            service.approve_voice_session(str(user.id), duration_minutes=60)
            
            # Handle inbound call
            result = service.handle_inbound_call(str(user.id), phone_number)
            
            assert result.success, f"Inbound call should succeed: {result.error}"
            
            # Complete call with transcript
            success = service.complete_call_with_transcript(result.call_id, transcript)
            assert success, "Completing call with transcript should succeed"
            
            # Verify transcript is stored
            stored_transcript = service.get_call_transcript(result.call_id)
            assert stored_transcript == transcript, "Transcript should be stored correctly"
            
            # Verify call record has transcript
            call_data = service.get_call_record(result.call_id)
            assert call_data is not None
            assert call_data.has_transcript, "Call should have transcript"
            assert call_data.transcript == transcript
        finally:
            User.objects.filter(id=user.id).delete()
    
    @settings(max_examples=20, deadline=None)
    @given(
        phone_number=phone_number_strategy,
        transcript=st.text(min_size=1, max_size=500),
        cognitive_blend=cognitive_blend_strategy
    )
    def test_outbound_call_stores_transcript(self, phone_number, transcript, cognitive_blend):
        """
        Feature: neurotwin-platform, Property 31: Call transcript storage
        
        For any outbound call, the transcript should be stored.
        """
        service = VoiceTwinService()
        
        # Create test user with voice profile
        user = create_test_user(f"p31_outbound_{hash((phone_number, transcript, cognitive_blend)) % 10000}")
        
        try:
            # Set up voice profile with clone and approval
            setup_voice_profile_with_clone(user, service)
            service.approve_voice_session(str(user.id), duration_minutes=60)
            
            # Make outbound call
            result = service.make_outbound_call(
                str(user.id),
                phone_number,
                cognitive_blend=cognitive_blend
            )
            
            assert result.success, f"Outbound call should succeed: {result.error}"
            
            # Complete call with transcript
            success = service.complete_call_with_transcript(result.call_id, transcript)
            assert success, "Completing call with transcript should succeed"
            
            # Verify transcript is stored
            stored_transcript = service.get_call_transcript(result.call_id)
            assert stored_transcript == transcript, "Transcript should be stored correctly"
        finally:
            User.objects.filter(id=user.id).delete()


@pytest.mark.django_db(transaction=True)
class TestVoiceSessionApproval:
    """
    Property 32: Voice session approval requirement
    
    *For any* voice cloning session, the system SHALL require separate explicit approval
    that has not expired.
    
    **Validates: Requirements 9.6**
    """
    
    @settings(max_examples=20, deadline=None)
    @given(
        phone_number=phone_number_strategy,
        duration=duration_strategy
    )
    def test_call_requires_approval(self, phone_number, duration):
        """
        Feature: neurotwin-platform, Property 32: Voice session approval requirement
        
        For any call attempt without approval, the call should be rejected.
        """
        service = VoiceTwinService()
        
        # Create test user with voice profile but NO approval
        user = create_test_user(f"p32_no_approval_{hash((phone_number, duration)) % 10000}")
        
        try:
            # Set up voice profile with clone but don't approve
            setup_voice_profile_with_clone(user, service)
            
            # Verify not approved
            assert not service.is_voice_approved(str(user.id)), "Should not be approved"
            
            # Try to make outbound call - should fail
            result = service.make_outbound_call(str(user.id), phone_number)
            
            assert not result.success, "Call should fail without approval"
            assert "not approved" in result.error.lower(), "Error should mention approval"
        finally:
            User.objects.filter(id=user.id).delete()
    
    @settings(max_examples=20, deadline=None)
    @given(
        phone_number=phone_number_strategy,
        duration=duration_strategy,
        reason=reason_strategy
    )
    def test_approval_enables_calls(self, phone_number, duration, reason):
        """
        Feature: neurotwin-platform, Property 32: Voice session approval requirement
        
        For any approved session, calls should be allowed.
        """
        service = VoiceTwinService()
        
        # Create test user
        user = create_test_user(f"p32_approved_{hash((phone_number, duration, reason)) % 10000}")
        
        try:
            # Set up voice profile with clone
            setup_voice_profile_with_clone(user, service)
            
            # Approve voice session
            approval_result = service.approve_voice_session(
                str(user.id),
                duration_minutes=duration,
                reason=reason
            )
            
            assert approval_result.success, f"Approval should succeed: {approval_result.error}"
            assert approval_result.expires_at is not None
            assert approval_result.duration_minutes == duration
            
            # Verify approved
            assert service.is_voice_approved(str(user.id)), "Should be approved"
            
            # Make outbound call - should succeed
            result = service.make_outbound_call(str(user.id), phone_number)
            
            assert result.success, f"Call should succeed with approval: {result.error}"
        finally:
            User.objects.filter(id=user.id).delete()
    
    @settings(max_examples=20, deadline=None)
    @given(phone_number=phone_number_strategy)
    def test_expired_approval_blocks_calls(self, phone_number):
        """
        Feature: neurotwin-platform, Property 32: Voice session approval requirement
        
        For any expired approval, calls should be blocked.
        """
        service = VoiceTwinService()
        
        # Create test user
        user = create_test_user(f"p32_expired_{hash(phone_number) % 10000}")
        
        try:
            # Set up voice profile with clone
            setup_voice_profile_with_clone(user, service)
            
            # Approve voice session
            service.approve_voice_session(str(user.id), duration_minutes=60)
            
            # Manually expire the approval
            profile = VoiceProfile.objects.get(user=user)
            profile.approval_expires_at = timezone.now() - timedelta(minutes=1)
            profile.save()
            
            # Verify not approved (expired)
            assert not service.is_voice_approved(str(user.id)), "Should not be approved (expired)"
            
            # Try to make call - should fail
            result = service.make_outbound_call(str(user.id), phone_number)
            
            assert not result.success, "Call should fail with expired approval"
        finally:
            User.objects.filter(id=user.id).delete()


@pytest.mark.django_db(transaction=True)
class TestVoiceKillSwitch:
    """
    Property 33: Voice kill switch availability
    
    *For any* active call, the kill switch SHALL be available and immediately
    terminate the call when activated.
    
    **Validates: Requirements 9.7**
    """
    
    @settings(max_examples=20, deadline=None)
    @given(
        phone_number=phone_number_strategy,
        reason=reason_strategy
    )
    def test_kill_switch_terminates_active_call(self, phone_number, reason):
        """
        Feature: neurotwin-platform, Property 33: Voice kill switch availability
        
        For any active call, kill switch should terminate it immediately.
        """
        service = VoiceTwinService()
        
        # Create test user
        user = create_test_user(f"p33_terminate_{hash((phone_number, reason)) % 10000}")
        
        try:
            # Set up voice profile with clone and approval
            setup_voice_profile_with_clone(user, service)
            service.approve_voice_session(str(user.id), duration_minutes=60)
            
            # Make outbound call
            call_result = service.make_outbound_call(str(user.id), phone_number)
            
            assert call_result.success, f"Call should succeed: {call_result.error}"
            
            # Verify call is active
            call_data = service.get_call_record(call_result.call_id)
            assert call_data.is_active, "Call should be active"
            
            # Terminate call via kill switch
            terminate_result = service.terminate_call(
                call_result.call_id,
                reason=reason or "Kill switch activated"
            )
            
            assert terminate_result.success, "Termination should succeed"
            assert terminate_result.was_active, "Call should have been active"
            
            # Verify call is terminated
            call_data = service.get_call_record(call_result.call_id)
            assert not call_data.is_active, "Call should no longer be active"
            assert call_data.status == CallStatus.TERMINATED
            assert call_data.was_terminated, "Call should be marked as terminated"
        finally:
            User.objects.filter(id=user.id).delete()
    
    @settings(max_examples=20, deadline=None)
    @given(
        phone_numbers=st.lists(phone_number_strategy, min_size=1, max_size=3),
        reason=reason_strategy
    )
    def test_kill_switch_terminates_all_active_calls(self, phone_numbers, reason):
        """
        Feature: neurotwin-platform, Property 33: Voice kill switch availability
        
        For any user with multiple active calls, kill switch should terminate all.
        """
        service = VoiceTwinService()
        
        # Create test user
        user = create_test_user(f"p33_terminate_all_{hash((tuple(phone_numbers), reason)) % 10000}")
        
        try:
            # Set up voice profile with clone and approval
            setup_voice_profile_with_clone(user, service)
            service.approve_voice_session(str(user.id), duration_minutes=60)
            
            # Make multiple outbound calls
            call_ids = []
            for phone in phone_numbers:
                result = service.make_outbound_call(str(user.id), phone)
                if result.success:
                    call_ids.append(result.call_id)
            
            # Verify we have active calls
            active_calls = service.get_active_calls(str(user.id))
            initial_active_count = len(active_calls)
            assert initial_active_count > 0, "Should have active calls"
            
            # Terminate all calls
            terminated_count = service.terminate_all_active_calls(
                str(user.id),
                reason=reason or "Kill switch activated"
            )
            
            assert terminated_count == initial_active_count, (
                f"Should terminate all {initial_active_count} calls"
            )
            
            # Verify no active calls remain
            active_calls = service.get_active_calls(str(user.id))
            assert len(active_calls) == 0, "No active calls should remain"
        finally:
            User.objects.filter(id=user.id).delete()
    
    @settings(max_examples=20, deadline=None)
    @given(dummy=st.integers())
    def test_kill_switch_on_nonexistent_call(self, dummy):
        """
        Feature: neurotwin-platform, Property 33: Voice kill switch availability
        
        For any non-existent call ID, kill switch should fail gracefully.
        """
        service = VoiceTwinService()
        
        # Try to terminate non-existent call
        fake_id = str(uuid.uuid4())
        result = service.terminate_call(fake_id)
        
        assert not result.success, "Termination should fail for non-existent call"
        assert "not found" in result.error.lower(), "Error should mention call not found"
    
    @settings(max_examples=20, deadline=None)
    @given(phone_number=phone_number_strategy)
    def test_kill_switch_on_completed_call(self, phone_number):
        """
        Feature: neurotwin-platform, Property 33: Voice kill switch availability
        
        For any already-completed call, kill switch should indicate it was not active.
        """
        service = VoiceTwinService()
        
        # Create test user
        user = create_test_user(f"p33_completed_{hash(phone_number) % 10000}")
        
        try:
            # Set up voice profile with clone and approval
            setup_voice_profile_with_clone(user, service)
            service.approve_voice_session(str(user.id), duration_minutes=60)
            
            # Make outbound call
            call_result = service.make_outbound_call(str(user.id), phone_number)
            
            assert call_result.success
            
            # Complete the call
            service.complete_call_with_transcript(call_result.call_id, "Test transcript")
            
            # Try to terminate completed call
            terminate_result = service.terminate_call(call_result.call_id)
            
            assert terminate_result.success, "Should succeed (idempotent)"
            assert not terminate_result.was_active, "Call should not have been active"
        finally:
            User.objects.filter(id=user.id).delete()
