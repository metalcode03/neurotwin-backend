"""
Dataclasses for the voice app.

Provides data transfer objects for voice operations.
Requirements: 9.1-9.7
"""

from dataclasses import dataclass
from typing import Optional, List
from datetime import datetime


@dataclass
class VoiceProfileData:
    """
    Data transfer object for voice profile information.
    
    Attributes:
        id: Unique identifier
        user_id: The user who owns this profile
        phone_number: Provisioned phone number
        voice_clone_id: ElevenLabs voice clone ID
        is_enabled: Whether Voice Twin is enabled
        is_approved: Whether voice cloning is currently approved
        approval_expires_at: When the approval expires
        has_phone_number: Whether a phone number is provisioned
        has_voice_clone: Whether a voice clone exists
    """
    
    id: str
    user_id: str
    phone_number: Optional[str]
    voice_clone_id: Optional[str]
    voice_clone_name: Optional[str]
    is_enabled: bool
    is_approved: bool
    approval_expires_at: Optional[datetime]
    has_phone_number: bool
    has_voice_clone: bool
    is_voice_approved: bool
    created_at: datetime
    
    @classmethod
    def from_model(cls, voice_profile) -> 'VoiceProfileData':
        """Create from a VoiceProfile model instance."""
        return cls(
            id=str(voice_profile.id),
            user_id=str(voice_profile.user_id),
            phone_number=voice_profile.phone_number,
            voice_clone_id=voice_profile.voice_clone_id,
            voice_clone_name=voice_profile.voice_clone_name,
            is_enabled=voice_profile.is_enabled,
            is_approved=voice_profile.is_approved,
            approval_expires_at=voice_profile.approval_expires_at,
            has_phone_number=voice_profile.has_phone_number,
            has_voice_clone=voice_profile.has_voice_clone,
            is_voice_approved=voice_profile.is_voice_approved,
            created_at=voice_profile.created_at,
        )


@dataclass
class CallRecordData:
    """
    Data transfer object for call record information.
    
    Requirements: 9.5
    
    Attributes:
        id: Unique identifier
        user_id: The user who owns this call
        direction: Inbound or outbound
        phone_number: External phone number
        status: Current call status
        transcript: Call transcript
        duration_seconds: Call duration
        cognitive_blend: Cognitive blend used
        was_terminated: Whether terminated via kill switch
        started_at: When the call started
        ended_at: When the call ended
    """
    
    id: str
    user_id: str
    direction: str
    phone_number: str
    status: str
    transcript: str
    duration_seconds: int
    cognitive_blend: Optional[int]
    was_terminated: bool
    termination_reason: str
    started_at: Optional[datetime]
    ended_at: Optional[datetime]
    created_at: datetime
    is_active: bool
    has_transcript: bool
    
    @classmethod
    def from_model(cls, call_record) -> 'CallRecordData':
        """Create from a CallRecord model instance."""
        return cls(
            id=str(call_record.id),
            user_id=str(call_record.user_id),
            direction=call_record.direction,
            phone_number=call_record.phone_number,
            status=call_record.status,
            transcript=call_record.transcript,
            duration_seconds=call_record.duration_seconds,
            cognitive_blend=call_record.cognitive_blend,
            was_terminated=call_record.was_terminated,
            termination_reason=call_record.termination_reason,
            started_at=call_record.started_at,
            ended_at=call_record.ended_at,
            created_at=call_record.created_at,
            is_active=call_record.is_active,
            has_transcript=call_record.has_transcript,
        )


@dataclass
class ProvisionPhoneResult:
    """
    Result of phone number provisioning.
    
    Requirements: 9.1
    
    Attributes:
        success: Whether provisioning succeeded
        phone_number: The provisioned phone number
        phone_sid: Twilio phone SID
        error: Error message if failed
    """
    
    success: bool
    phone_number: Optional[str] = None
    phone_sid: Optional[str] = None
    error: Optional[str] = None
    
    @classmethod
    def succeeded(cls, phone_number: str, phone_sid: str) -> 'ProvisionPhoneResult':
        """Create a successful result."""
        return cls(
            success=True,
            phone_number=phone_number,
            phone_sid=phone_sid,
        )
    
    @classmethod
    def failed(cls, error: str) -> 'ProvisionPhoneResult':
        """Create a failed result."""
        return cls(success=False, error=error)


@dataclass
class VoiceCloneResult:
    """
    Result of voice clone creation.
    
    Requirements: 9.2
    
    Attributes:
        success: Whether creation succeeded
        voice_clone_id: The created voice clone ID
        voice_clone_name: Name of the voice clone
        error: Error message if failed
    """
    
    success: bool
    voice_clone_id: Optional[str] = None
    voice_clone_name: Optional[str] = None
    error: Optional[str] = None
    
    @classmethod
    def succeeded(cls, voice_clone_id: str, voice_clone_name: str) -> 'VoiceCloneResult':
        """Create a successful result."""
        return cls(
            success=True,
            voice_clone_id=voice_clone_id,
            voice_clone_name=voice_clone_name,
        )
    
    @classmethod
    def failed(cls, error: str) -> 'VoiceCloneResult':
        """Create a failed result."""
        return cls(success=False, error=error)


@dataclass
class CallResult:
    """
    Result of a call operation.
    
    Requirements: 9.3, 9.4
    
    Attributes:
        success: Whether the operation succeeded
        call_id: The call record ID
        call_sid: Twilio call SID
        status: Current call status
        error: Error message if failed
    """
    
    success: bool
    call_id: Optional[str] = None
    call_sid: Optional[str] = None
    status: Optional[str] = None
    error: Optional[str] = None
    
    @classmethod
    def succeeded(cls, call_id: str, call_sid: str, status: str) -> 'CallResult':
        """Create a successful result."""
        return cls(
            success=True,
            call_id=call_id,
            call_sid=call_sid,
            status=status,
        )
    
    @classmethod
    def failed(cls, error: str) -> 'CallResult':
        """Create a failed result."""
        return cls(success=False, error=error)


@dataclass
class TerminateCallResult:
    """
    Result of call termination.
    
    Requirements: 9.7
    
    Attributes:
        success: Whether termination succeeded
        call_id: The call record ID
        was_active: Whether the call was active when terminated
        error: Error message if failed
    """
    
    success: bool
    call_id: Optional[str] = None
    was_active: bool = False
    error: Optional[str] = None
    
    @classmethod
    def succeeded(cls, call_id: str, was_active: bool) -> 'TerminateCallResult':
        """Create a successful result."""
        return cls(
            success=True,
            call_id=call_id,
            was_active=was_active,
        )
    
    @classmethod
    def failed(cls, error: str) -> 'TerminateCallResult':
        """Create a failed result."""
        return cls(success=False, error=error)


@dataclass
class VoiceApprovalResult:
    """
    Result of voice session approval.
    
    Requirements: 9.6
    
    Attributes:
        success: Whether approval succeeded
        expires_at: When the approval expires
        duration_minutes: Duration of the approval
        error: Error message if failed
    """
    
    success: bool
    expires_at: Optional[datetime] = None
    duration_minutes: Optional[int] = None
    error: Optional[str] = None
    
    @classmethod
    def succeeded(cls, expires_at: datetime, duration_minutes: int) -> 'VoiceApprovalResult':
        """Create a successful result."""
        return cls(
            success=True,
            expires_at=expires_at,
            duration_minutes=duration_minutes,
        )
    
    @classmethod
    def failed(cls, error: str) -> 'VoiceApprovalResult':
        """Create a failed result."""
        return cls(success=False, error=error)


@dataclass
class CallFilterCriteria:
    """
    Filter criteria for querying call records.
    
    Attributes:
        direction: Filter by call direction
        status: Filter by call status
        start_date: Filter calls from this date
        end_date: Filter calls until this date
        phone_number: Filter by phone number
        has_transcript: Filter by transcript availability
    """
    
    direction: Optional[str] = None
    status: Optional[str] = None
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    phone_number: Optional[str] = None
    has_transcript: Optional[bool] = None
