"""
Voice models for NeuroTwin platform.

Defines VoiceProfile model with phone_number and voice_clone_id.
Defines CallRecord model for storing call transcripts.

Requirements: 9.1, 9.5, 9.6, 9.7
"""

import uuid
from datetime import datetime
from typing import Optional

from django.db import models
from django.conf import settings
from django.utils import timezone


class CallDirection(models.TextChoices):
    """Direction of a phone call."""
    
    INBOUND = 'inbound', 'Inbound'
    OUTBOUND = 'outbound', 'Outbound'


class CallStatus(models.TextChoices):
    """Status of a phone call."""
    
    PENDING = 'pending', 'Pending'
    RINGING = 'ringing', 'Ringing'
    IN_PROGRESS = 'in_progress', 'In Progress'
    COMPLETED = 'completed', 'Completed'
    FAILED = 'failed', 'Failed'
    TERMINATED = 'terminated', 'Terminated'  # Kill switch activated
    NO_ANSWER = 'no_answer', 'No Answer'
    BUSY = 'busy', 'Busy'


class VoiceProfile(models.Model):
    """
    Voice profile for a user's Voice Twin.
    
    Stores the provisioned phone number and voice clone configuration.
    Voice cloning requires separate explicit approval per session.
    
    Requirements: 9.1, 9.6
    - Provision virtual phone number via Twilio
    - Voice cloning requires separate explicit approval per session
    """
    
    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False
    )
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='voice_profile'
    )
    
    # Phone number provisioned via Twilio
    phone_number = models.CharField(
        max_length=20,
        blank=True,
        null=True,
        unique=True,
        help_text='Virtual phone number provisioned via Twilio'
    )
    twilio_phone_sid = models.CharField(
        max_length=50,
        blank=True,
        null=True,
        help_text='Twilio phone number SID for management'
    )
    
    # Voice clone via ElevenLabs
    voice_clone_id = models.CharField(
        max_length=255,
        blank=True,
        null=True,
        help_text='ElevenLabs voice clone ID'
    )
    voice_clone_name = models.CharField(
        max_length=100,
        blank=True,
        null=True,
        help_text='Name of the voice clone'
    )
    
    # Voice session approval (Requirements: 9.6)
    is_approved = models.BooleanField(
        default=False,
        help_text='Whether voice cloning is currently approved'
    )
    approval_expires_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text='When the current voice approval expires'
    )
    
    # Status flags
    is_enabled = models.BooleanField(
        default=False,
        help_text='Whether Voice Twin is enabled for this user'
    )
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'voice_profiles'
        verbose_name = 'voice profile'
        verbose_name_plural = 'voice profiles'
        indexes = [
            models.Index(fields=['phone_number']),
            models.Index(fields=['is_enabled']),
        ]
    
    def __str__(self) -> str:
        status = 'enabled' if self.is_enabled else 'disabled'
        phone = self.phone_number or 'no phone'
        return f"{self.user.email}: {phone} ({status})"
    
    @property
    def has_phone_number(self) -> bool:
        """Check if a phone number has been provisioned."""
        return bool(self.phone_number)
    
    @property
    def has_voice_clone(self) -> bool:
        """Check if a voice clone has been created."""
        return bool(self.voice_clone_id)
    
    @property
    def is_voice_approved(self) -> bool:
        """
        Check if voice cloning is currently approved and not expired.
        
        Requirements: 9.6
        - Voice cloning requires separate explicit approval per session
        """
        if not self.is_approved:
            return False
        
        if self.approval_expires_at is None:
            return False
        
        return timezone.now() < self.approval_expires_at
    
    def approve_voice_session(self, duration_minutes: int = 60) -> None:
        """
        Approve voice cloning for a session.
        
        Requirements: 9.6
        
        Args:
            duration_minutes: How long the approval is valid (default 60 minutes)
        """
        from datetime import timedelta
        
        self.is_approved = True
        self.approval_expires_at = timezone.now() + timedelta(minutes=duration_minutes)
        self.save(update_fields=['is_approved', 'approval_expires_at', 'updated_at'])
    
    def revoke_voice_approval(self) -> None:
        """Revoke voice cloning approval."""
        self.is_approved = False
        self.approval_expires_at = None
        self.save(update_fields=['is_approved', 'approval_expires_at', 'updated_at'])


class CallRecord(models.Model):
    """
    Record of a phone call made or received by the Voice Twin.
    
    Stores call metadata and transcript for all calls.
    
    Requirements: 9.3, 9.4, 9.5, 9.7
    - Handle incoming calls with cloned voice and CSM personality
    - Make outbound calls with cloned voice
    - Generate and store transcripts for all calls
    - Kill switch to immediately terminate any call
    """
    
    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='call_records'
    )
    voice_profile = models.ForeignKey(
        VoiceProfile,
        on_delete=models.CASCADE,
        related_name='call_records',
        null=True,
        blank=True
    )
    
    # Call identifiers
    twilio_call_sid = models.CharField(
        max_length=50,
        blank=True,
        null=True,
        unique=True,
        help_text='Twilio call SID for tracking'
    )
    
    # Call details
    direction = models.CharField(
        max_length=10,
        choices=CallDirection.choices,
        db_index=True,
        help_text='Whether the call was inbound or outbound'
    )
    phone_number = models.CharField(
        max_length=20,
        help_text='The external phone number (caller for inbound, callee for outbound)'
    )
    status = models.CharField(
        max_length=20,
        choices=CallStatus.choices,
        default=CallStatus.PENDING,
        db_index=True,
        help_text='Current status of the call'
    )
    
    # Call content
    transcript = models.TextField(
        blank=True,
        help_text='Full transcript of the call'
    )
    script = models.TextField(
        blank=True,
        null=True,
        help_text='Script used for outbound calls (if any)'
    )
    
    # Call metrics
    duration_seconds = models.IntegerField(
        default=0,
        help_text='Duration of the call in seconds'
    )
    
    # Cognitive blend used during the call
    cognitive_blend = models.IntegerField(
        null=True,
        blank=True,
        help_text='Cognitive blend value used during the call (0-100)'
    )
    
    # Kill switch tracking (Requirements: 9.7)
    was_terminated = models.BooleanField(
        default=False,
        help_text='Whether the call was terminated via kill switch'
    )
    termination_reason = models.CharField(
        max_length=255,
        blank=True,
        help_text='Reason for termination (if terminated)'
    )
    
    # Timestamps
    started_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text='When the call started'
    )
    ended_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text='When the call ended'
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'call_records'
        verbose_name = 'call record'
        verbose_name_plural = 'call records'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['user', '-created_at']),
            models.Index(fields=['user', 'direction']),
            models.Index(fields=['user', 'status']),
            models.Index(fields=['phone_number']),
            models.Index(fields=['twilio_call_sid']),
        ]
    
    def __str__(self) -> str:
        return f"{self.user.email}: {self.direction} call to/from {self.phone_number} ({self.status})"
    
    @property
    def is_active(self) -> bool:
        """Check if the call is currently active."""
        return self.status in [
            CallStatus.PENDING,
            CallStatus.RINGING,
            CallStatus.IN_PROGRESS,
        ]
    
    @property
    def has_transcript(self) -> bool:
        """Check if a transcript is available."""
        return bool(self.transcript)
    
    def start_call(self) -> None:
        """Mark the call as started."""
        self.status = CallStatus.IN_PROGRESS
        self.started_at = timezone.now()
        self.save(update_fields=['status', 'started_at', 'updated_at'])
    
    def complete_call(self, transcript: str = "") -> None:
        """
        Mark the call as completed.
        
        Args:
            transcript: The call transcript
        """
        self.status = CallStatus.COMPLETED
        self.ended_at = timezone.now()
        self.transcript = transcript
        
        if self.started_at:
            delta = self.ended_at - self.started_at
            self.duration_seconds = int(delta.total_seconds())
        
        self.save(update_fields=[
            'status', 'ended_at', 'transcript', 
            'duration_seconds', 'updated_at'
        ])
    
    def terminate_call(self, reason: str = "Kill switch activated") -> None:
        """
        Terminate the call via kill switch.
        
        Requirements: 9.7
        - Kill switch to immediately terminate any call
        
        Args:
            reason: Reason for termination
        """
        self.status = CallStatus.TERMINATED
        self.ended_at = timezone.now()
        self.was_terminated = True
        self.termination_reason = reason
        
        if self.started_at:
            delta = self.ended_at - self.started_at
            self.duration_seconds = int(delta.total_seconds())
        
        self.save(update_fields=[
            'status', 'ended_at', 'was_terminated',
            'termination_reason', 'duration_seconds', 'updated_at'
        ])
    
    def fail_call(self, reason: str = "") -> None:
        """
        Mark the call as failed.
        
        Args:
            reason: Reason for failure
        """
        self.status = CallStatus.FAILED
        self.ended_at = timezone.now()
        self.termination_reason = reason
        self.save(update_fields=['status', 'ended_at', 'termination_reason', 'updated_at'])


class VoiceApprovalHistory(models.Model):
    """
    Track voice approval history for audit purposes.
    
    Requirements: 9.6
    """
    
    class ApprovalAction(models.TextChoices):
        APPROVED = 'approved', 'Approved'
        REVOKED = 'revoked', 'Revoked'
        EXPIRED = 'expired', 'Expired'
    
    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False
    )
    voice_profile = models.ForeignKey(
        VoiceProfile,
        on_delete=models.CASCADE,
        related_name='approval_history'
    )
    action = models.CharField(
        max_length=20,
        choices=ApprovalAction.choices,
        help_text='Type of approval action'
    )
    duration_minutes = models.IntegerField(
        null=True,
        blank=True,
        help_text='Duration of approval (for approved actions)'
    )
    reason = models.CharField(
        max_length=255,
        blank=True,
        help_text='Reason for the action'
    )
    timestamp = models.DateTimeField(
        default=timezone.now,
        db_index=True
    )
    
    class Meta:
        db_table = 'voice_approval_history'
        verbose_name = 'voice approval history'
        verbose_name_plural = 'voice approval histories'
        ordering = ['-timestamp']
        indexes = [
            models.Index(fields=['voice_profile', '-timestamp']),
        ]
    
    def __str__(self) -> str:
        return f"{self.voice_profile.user.email}: {self.action} at {self.timestamp}"
