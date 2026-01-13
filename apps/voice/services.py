"""
Voice Twin service for NeuroTwin platform.

Handles phone number provisioning, voice cloning, and call management.
Requirements: 9.1-9.7
"""

import uuid
from datetime import timedelta
from typing import List, Optional

from django.db import transaction
from django.utils import timezone

from .models import (
    VoiceProfile, 
    CallRecord, 
    VoiceApprovalHistory,
    CallDirection,
    CallStatus,
)
from .dataclasses import (
    VoiceProfileData,
    CallRecordData,
    ProvisionPhoneResult,
    VoiceCloneResult,
    CallResult,
    TerminateCallResult,
    VoiceApprovalResult,
    CallFilterCriteria,
)


class VoiceTwinService:
    """
    Manages Voice Twin phone capabilities.
    
    Provides methods for phone number provisioning, voice cloning,
    call handling, and kill switch functionality.
    
    Requirements: 9.1-9.7
    - Provision virtual phone number via Twilio
    - Use ElevenLabs for voice cloning
    - Handle incoming calls with cloned voice and CSM personality
    - Make outbound calls with cloned voice
    - Generate and store transcripts for all calls
    - Voice cloning requires separate explicit approval per session
    - Kill switch to immediately terminate any call
    """
    
    # Default voice session approval duration in minutes
    DEFAULT_APPROVAL_DURATION_MINUTES = 60
    
    def __init__(
        self,
        twilio_client=None,
        elevenlabs_client=None,
        audit_service=None
    ):
        """
        Initialize VoiceTwinService.
        
        Args:
            twilio_client: Optional Twilio client for phone operations
            elevenlabs_client: Optional ElevenLabs client for voice cloning
            audit_service: Optional AuditService for logging voice actions
        """
        self._twilio_client = twilio_client
        self._elevenlabs_client = elevenlabs_client
        self._audit_service = audit_service
    
    # =========================================================================
    # Voice Profile Management
    # =========================================================================
    
    def get_or_create_voice_profile(self, user_id: str) -> VoiceProfile:
        """
        Get or create a voice profile for a user.
        
        Args:
            user_id: The user's ID
            
        Returns:
            The voice profile (existing or newly created)
        """
        profile, created = VoiceProfile.objects.get_or_create(
            user_id=user_id,
            defaults={
                'is_enabled': False,
                'is_approved': False,
            }
        )
        return profile
    
    def get_voice_profile(self, user_id: str) -> Optional[VoiceProfileData]:
        """
        Get voice profile for a user.
        
        Args:
            user_id: The user's ID
            
        Returns:
            VoiceProfileData if found, None otherwise
        """
        try:
            profile = VoiceProfile.objects.get(user_id=user_id)
            return VoiceProfileData.from_model(profile)
        except VoiceProfile.DoesNotExist:
            return None
    
    def enable_voice_twin(self, user_id: str) -> VoiceProfileData:
        """
        Enable Voice Twin for a user.
        
        Args:
            user_id: The user's ID
            
        Returns:
            Updated VoiceProfileData
        """
        profile = self.get_or_create_voice_profile(user_id)
        profile.is_enabled = True
        profile.save(update_fields=['is_enabled', 'updated_at'])
        return VoiceProfileData.from_model(profile)
    
    def disable_voice_twin(self, user_id: str) -> VoiceProfileData:
        """
        Disable Voice Twin for a user.
        
        Args:
            user_id: The user's ID
            
        Returns:
            Updated VoiceProfileData
        """
        profile = self.get_or_create_voice_profile(user_id)
        profile.is_enabled = False
        profile.is_approved = False
        profile.approval_expires_at = None
        profile.save(update_fields=[
            'is_enabled', 'is_approved', 'approval_expires_at', 'updated_at'
        ])
        return VoiceProfileData.from_model(profile)
    
    # =========================================================================
    # Phone Number Provisioning (Requirements: 9.1)
    # =========================================================================
    
    @transaction.atomic
    def provision_phone_number(
        self, 
        user_id: str,
        area_code: Optional[str] = None,
        country_code: str = "US"
    ) -> ProvisionPhoneResult:
        """
        Provision a virtual phone number via Twilio.
        
        Requirements: 9.1
        - When a user enables Voice_Twin, provision a virtual phone number
        
        Args:
            user_id: The user's ID
            area_code: Optional preferred area code
            country_code: Country code for the phone number
            
        Returns:
            ProvisionPhoneResult with phone number or error
        """
        profile = self.get_or_create_voice_profile(user_id)
        
        # Check if already has a phone number
        if profile.has_phone_number:
            return ProvisionPhoneResult.succeeded(
                phone_number=profile.phone_number,
                phone_sid=profile.twilio_phone_sid
            )
        
        # In a real implementation, this would call Twilio API
        # For now, we simulate the provisioning
        if self._twilio_client:
            try:
                # Real Twilio implementation would go here
                # phone = self._twilio_client.incoming_phone_numbers.create(...)
                pass
            except Exception as e:
                return ProvisionPhoneResult.failed(str(e))
        
        # Simulate successful provisioning for testing
        # In production, this would be replaced with actual Twilio response
        simulated_phone = f"+1555{str(uuid.uuid4().int)[:7]}"
        simulated_sid = f"PN{uuid.uuid4().hex[:32]}"
        
        profile.phone_number = simulated_phone
        profile.twilio_phone_sid = simulated_sid
        profile.is_enabled = True
        profile.save(update_fields=[
            'phone_number', 'twilio_phone_sid', 'is_enabled', 'updated_at'
        ])
        
        return ProvisionPhoneResult.succeeded(
            phone_number=simulated_phone,
            phone_sid=simulated_sid
        )
    
    def release_phone_number(self, user_id: str) -> bool:
        """
        Release a provisioned phone number.
        
        Args:
            user_id: The user's ID
            
        Returns:
            True if released successfully, False otherwise
        """
        try:
            profile = VoiceProfile.objects.get(user_id=user_id)
        except VoiceProfile.DoesNotExist:
            return False
        
        if not profile.has_phone_number:
            return True
        
        # In a real implementation, this would call Twilio API to release
        # self._twilio_client.incoming_phone_numbers(profile.twilio_phone_sid).delete()
        
        profile.phone_number = None
        profile.twilio_phone_sid = None
        profile.save(update_fields=['phone_number', 'twilio_phone_sid', 'updated_at'])
        
        return True
    
    # =========================================================================
    # Voice Cloning (Requirements: 9.2)
    # =========================================================================
    
    @transaction.atomic
    def create_voice_clone(
        self, 
        user_id: str, 
        audio_samples: List[bytes],
        voice_name: Optional[str] = None
    ) -> VoiceCloneResult:
        """
        Create a voice clone via ElevenLabs.
        
        Requirements: 9.2
        - Use ElevenLabs for voice cloning based on user-provided samples
        
        Args:
            user_id: The user's ID
            audio_samples: List of audio sample bytes
            voice_name: Optional name for the voice clone
            
        Returns:
            VoiceCloneResult with clone ID or error
        """
        profile = self.get_or_create_voice_profile(user_id)
        
        # Validate audio samples
        if not audio_samples:
            return VoiceCloneResult.failed("No audio samples provided")
        
        # In a real implementation, this would call ElevenLabs API
        if self._elevenlabs_client:
            try:
                # Real ElevenLabs implementation would go here
                # voice = self._elevenlabs_client.clone(...)
                pass
            except Exception as e:
                return VoiceCloneResult.failed(str(e))
        
        # Simulate successful voice clone creation for testing
        simulated_clone_id = f"voice_{uuid.uuid4().hex[:24]}"
        clone_name = voice_name or f"Voice Clone for {user_id[:8]}"
        
        profile.voice_clone_id = simulated_clone_id
        profile.voice_clone_name = clone_name
        profile.save(update_fields=['voice_clone_id', 'voice_clone_name', 'updated_at'])
        
        return VoiceCloneResult.succeeded(
            voice_clone_id=simulated_clone_id,
            voice_clone_name=clone_name
        )
    
    def delete_voice_clone(self, user_id: str) -> bool:
        """
        Delete a voice clone.
        
        Args:
            user_id: The user's ID
            
        Returns:
            True if deleted successfully, False otherwise
        """
        try:
            profile = VoiceProfile.objects.get(user_id=user_id)
        except VoiceProfile.DoesNotExist:
            return False
        
        if not profile.has_voice_clone:
            return True
        
        # In a real implementation, this would call ElevenLabs API to delete
        # self._elevenlabs_client.voices.delete(profile.voice_clone_id)
        
        profile.voice_clone_id = None
        profile.voice_clone_name = None
        profile.save(update_fields=['voice_clone_id', 'voice_clone_name', 'updated_at'])
        
        return True
    
    # =========================================================================
    # Voice Session Approval (Requirements: 9.6)
    # =========================================================================
    
    @transaction.atomic
    def approve_voice_session(
        self, 
        user_id: str,
        duration_minutes: Optional[int] = None,
        reason: str = ""
    ) -> VoiceApprovalResult:
        """
        Grant explicit approval for voice cloning session.
        
        Requirements: 9.6
        - Voice cloning requires separate explicit approval per session
        
        Args:
            user_id: The user's ID
            duration_minutes: How long the approval is valid (default 60 minutes)
            reason: Reason for approval
            
        Returns:
            VoiceApprovalResult with expiry time or error
        """
        profile = self.get_or_create_voice_profile(user_id)
        
        # Check if voice clone exists
        if not profile.has_voice_clone:
            return VoiceApprovalResult.failed(
                "No voice clone exists. Create a voice clone first."
            )
        
        # Check if Voice Twin is enabled
        if not profile.is_enabled:
            return VoiceApprovalResult.failed(
                "Voice Twin is not enabled. Enable it first."
            )
        
        duration = duration_minutes or self.DEFAULT_APPROVAL_DURATION_MINUTES
        expires_at = timezone.now() + timedelta(minutes=duration)
        
        profile.is_approved = True
        profile.approval_expires_at = expires_at
        profile.save(update_fields=['is_approved', 'approval_expires_at', 'updated_at'])
        
        # Record approval history
        VoiceApprovalHistory.objects.create(
            voice_profile=profile,
            action=VoiceApprovalHistory.ApprovalAction.APPROVED,
            duration_minutes=duration,
            reason=reason,
        )
        
        return VoiceApprovalResult.succeeded(
            expires_at=expires_at,
            duration_minutes=duration
        )
    
    def revoke_voice_approval(self, user_id: str, reason: str = "") -> bool:
        """
        Revoke voice cloning approval.
        
        Args:
            user_id: The user's ID
            reason: Reason for revocation
            
        Returns:
            True if revoked successfully, False otherwise
        """
        try:
            profile = VoiceProfile.objects.get(user_id=user_id)
        except VoiceProfile.DoesNotExist:
            return False
        
        if not profile.is_approved:
            return True
        
        profile.is_approved = False
        profile.approval_expires_at = None
        profile.save(update_fields=['is_approved', 'approval_expires_at', 'updated_at'])
        
        # Record revocation history
        VoiceApprovalHistory.objects.create(
            voice_profile=profile,
            action=VoiceApprovalHistory.ApprovalAction.REVOKED,
            reason=reason,
        )
        
        return True
    
    def is_voice_approved(self, user_id: str) -> bool:
        """
        Check if voice cloning is currently approved.
        
        Requirements: 9.6
        
        Args:
            user_id: The user's ID
            
        Returns:
            True if approved and not expired, False otherwise
        """
        try:
            profile = VoiceProfile.objects.get(user_id=user_id)
            return profile.is_voice_approved
        except VoiceProfile.DoesNotExist:
            return False
    
    # =========================================================================
    # Call Handling (Requirements: 9.3, 9.4)
    # =========================================================================
    
    def handle_inbound_call(
        self, 
        user_id: str, 
        caller_number: str,
        twilio_call_sid: Optional[str] = None
    ) -> CallResult:
        """
        Handle incoming call with cloned voice and CSM personality.
        
        Requirements: 9.3
        - When a call is received, answer using the cloned voice and CSM personality
        
        Args:
            user_id: The user's ID
            caller_number: The caller's phone number
            twilio_call_sid: Optional Twilio call SID
            
        Returns:
            CallResult with call details or error
        """
        # Verify voice approval
        if not self.is_voice_approved(user_id):
            return CallResult.failed(
                "Voice session not approved. Approve voice session first."
            )
        
        try:
            profile = VoiceProfile.objects.get(user_id=user_id)
        except VoiceProfile.DoesNotExist:
            return CallResult.failed("Voice profile not found")
        
        if not profile.is_enabled:
            return CallResult.failed("Voice Twin is not enabled")
        
        # Create call record
        call_sid = twilio_call_sid or f"CA{uuid.uuid4().hex[:32]}"
        
        call_record = CallRecord.objects.create(
            user_id=user_id,
            voice_profile=profile,
            twilio_call_sid=call_sid,
            direction=CallDirection.INBOUND,
            phone_number=caller_number,
            status=CallStatus.RINGING,
        )
        
        # In a real implementation, this would:
        # 1. Connect to Twilio to answer the call
        # 2. Use ElevenLabs to generate voice responses
        # 3. Use CSM profile to guide conversation
        
        # Start the call
        call_record.start_call()
        
        return CallResult.succeeded(
            call_id=str(call_record.id),
            call_sid=call_sid,
            status=call_record.status
        )
    
    def make_outbound_call(
        self, 
        user_id: str, 
        target_number: str,
        script: Optional[str] = None,
        cognitive_blend: Optional[int] = None
    ) -> CallResult:
        """
        Make outbound call with cloned voice.
        
        Requirements: 9.4
        - When a call is made, use the cloned voice and follow user-defined scripts
        
        Args:
            user_id: The user's ID
            target_number: The target phone number
            script: Optional script for the call
            cognitive_blend: Optional cognitive blend value (0-100)
            
        Returns:
            CallResult with call details or error
        """
        # Verify voice approval
        if not self.is_voice_approved(user_id):
            return CallResult.failed(
                "Voice session not approved. Approve voice session first."
            )
        
        try:
            profile = VoiceProfile.objects.get(user_id=user_id)
        except VoiceProfile.DoesNotExist:
            return CallResult.failed("Voice profile not found")
        
        if not profile.is_enabled:
            return CallResult.failed("Voice Twin is not enabled")
        
        if not profile.has_phone_number:
            return CallResult.failed("No phone number provisioned")
        
        # Validate cognitive blend
        if cognitive_blend is not None and not (0 <= cognitive_blend <= 100):
            return CallResult.failed("Cognitive blend must be between 0 and 100")
        
        # Create call record
        call_sid = f"CA{uuid.uuid4().hex[:32]}"
        
        call_record = CallRecord.objects.create(
            user_id=user_id,
            voice_profile=profile,
            twilio_call_sid=call_sid,
            direction=CallDirection.OUTBOUND,
            phone_number=target_number,
            status=CallStatus.PENDING,
            script=script,
            cognitive_blend=cognitive_blend,
        )
        
        # In a real implementation, this would:
        # 1. Use Twilio to initiate the call
        # 2. Use ElevenLabs to generate voice
        # 3. Follow the script or use CSM for guidance
        
        # Simulate call initiation
        call_record.status = CallStatus.RINGING
        call_record.save(update_fields=['status', 'updated_at'])
        
        return CallResult.succeeded(
            call_id=str(call_record.id),
            call_sid=call_sid,
            status=call_record.status
        )
    
    # =========================================================================
    # Kill Switch (Requirements: 9.7)
    # =========================================================================
    
    def terminate_call(
        self, 
        call_id: str,
        reason: str = "Kill switch activated"
    ) -> TerminateCallResult:
        """
        Kill switch - immediately terminate a call.
        
        Requirements: 9.7
        - Kill switch to immediately terminate any call
        
        Args:
            call_id: The call record ID
            reason: Reason for termination
            
        Returns:
            TerminateCallResult with termination status
        """
        try:
            call_record = CallRecord.objects.get(id=call_id)
        except CallRecord.DoesNotExist:
            return TerminateCallResult.failed("Call not found")
        
        was_active = call_record.is_active
        
        if not was_active:
            return TerminateCallResult.succeeded(
                call_id=str(call_record.id),
                was_active=False
            )
        
        # In a real implementation, this would call Twilio to end the call
        # self._twilio_client.calls(call_record.twilio_call_sid).update(status='completed')
        
        # Terminate the call
        call_record.terminate_call(reason=reason)
        
        return TerminateCallResult.succeeded(
            call_id=str(call_record.id),
            was_active=True
        )
    
    def terminate_all_active_calls(
        self, 
        user_id: str,
        reason: str = "Kill switch activated"
    ) -> int:
        """
        Terminate all active calls for a user.
        
        Requirements: 9.7
        
        Args:
            user_id: The user's ID
            reason: Reason for termination
            
        Returns:
            Number of calls terminated
        """
        active_calls = CallRecord.objects.filter(
            user_id=user_id,
            status__in=[
                CallStatus.PENDING,
                CallStatus.RINGING,
                CallStatus.IN_PROGRESS,
            ]
        )
        
        count = 0
        for call in active_calls:
            call.terminate_call(reason=reason)
            count += 1
        
        return count
    
    def get_active_calls(self, user_id: str) -> List[CallRecordData]:
        """
        Get all active calls for a user.
        
        Args:
            user_id: The user's ID
            
        Returns:
            List of active CallRecordData
        """
        calls = CallRecord.objects.filter(
            user_id=user_id,
            status__in=[
                CallStatus.PENDING,
                CallStatus.RINGING,
                CallStatus.IN_PROGRESS,
            ]
        )
        return [CallRecordData.from_model(call) for call in calls]
    
    # =========================================================================
    # Transcript Management (Requirements: 9.5)
    # =========================================================================
    
    def get_call_transcript(self, call_id: str) -> Optional[str]:
        """
        Retrieve transcript for a call.
        
        Requirements: 9.5
        - Generate and store transcripts for all calls
        
        Args:
            call_id: The call record ID
            
        Returns:
            Transcript string if available, None otherwise
        """
        try:
            call_record = CallRecord.objects.get(id=call_id)
            return call_record.transcript if call_record.has_transcript else None
        except CallRecord.DoesNotExist:
            return None
    
    def update_call_transcript(
        self, 
        call_id: str, 
        transcript: str,
        append: bool = False
    ) -> bool:
        """
        Update the transcript for a call.
        
        Args:
            call_id: The call record ID
            transcript: The transcript text
            append: Whether to append to existing transcript
            
        Returns:
            True if updated successfully, False otherwise
        """
        try:
            call_record = CallRecord.objects.get(id=call_id)
        except CallRecord.DoesNotExist:
            return False
        
        if append and call_record.transcript:
            call_record.transcript = f"{call_record.transcript}\n{transcript}"
        else:
            call_record.transcript = transcript
        
        call_record.save(update_fields=['transcript', 'updated_at'])
        return True
    
    def complete_call_with_transcript(
        self, 
        call_id: str, 
        transcript: str
    ) -> bool:
        """
        Complete a call and store its transcript.
        
        Requirements: 9.5
        
        Args:
            call_id: The call record ID
            transcript: The full call transcript
            
        Returns:
            True if completed successfully, False otherwise
        """
        try:
            call_record = CallRecord.objects.get(id=call_id)
        except CallRecord.DoesNotExist:
            return False
        
        call_record.complete_call(transcript=transcript)
        return True
    
    # =========================================================================
    # Call History
    # =========================================================================
    
    def get_call_history(
        self,
        user_id: str,
        filters: Optional[CallFilterCriteria] = None,
        limit: int = 50,
        offset: int = 0
    ) -> List[CallRecordData]:
        """
        Get call history for a user.
        
        Args:
            user_id: The user's ID
            filters: Optional filter criteria
            limit: Maximum number of records to return
            offset: Number of records to skip
            
        Returns:
            List of CallRecordData
        """
        queryset = CallRecord.objects.filter(user_id=user_id)
        
        if filters:
            queryset = self._apply_call_filters(queryset, filters)
        
        queryset = queryset.order_by('-created_at')[offset:offset + limit]
        
        return [CallRecordData.from_model(call) for call in queryset]
    
    def get_call_record(self, call_id: str) -> Optional[CallRecordData]:
        """
        Get a specific call record.
        
        Args:
            call_id: The call record ID
            
        Returns:
            CallRecordData if found, None otherwise
        """
        try:
            call_record = CallRecord.objects.get(id=call_id)
            return CallRecordData.from_model(call_record)
        except CallRecord.DoesNotExist:
            return None
    
    def _apply_call_filters(
        self,
        queryset,
        filters: CallFilterCriteria
    ):
        """
        Apply filter criteria to a call queryset.
        
        Args:
            queryset: The base queryset
            filters: The filter criteria
            
        Returns:
            Filtered queryset
        """
        if filters.direction:
            queryset = queryset.filter(direction=filters.direction)
        
        if filters.status:
            queryset = queryset.filter(status=filters.status)
        
        if filters.start_date:
            queryset = queryset.filter(created_at__gte=filters.start_date)
        
        if filters.end_date:
            queryset = queryset.filter(created_at__lte=filters.end_date)
        
        if filters.phone_number:
            queryset = queryset.filter(phone_number__icontains=filters.phone_number)
        
        if filters.has_transcript is not None:
            if filters.has_transcript:
                queryset = queryset.exclude(transcript='')
            else:
                queryset = queryset.filter(transcript='')
        
        return queryset
    
    def count_calls(
        self,
        user_id: str,
        filters: Optional[CallFilterCriteria] = None
    ) -> int:
        """
        Count calls matching the criteria.
        
        Args:
            user_id: The user's ID
            filters: Optional filter criteria
            
        Returns:
            Number of matching calls
        """
        queryset = CallRecord.objects.filter(user_id=user_id)
        
        if filters:
            queryset = self._apply_call_filters(queryset, filters)
        
        return queryset.count()
