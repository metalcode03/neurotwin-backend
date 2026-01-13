"""
Voice API views.

Requirements: 9.1-9.7, 13.1, 13.3
"""

from rest_framework import status
from rest_framework.permissions import IsAuthenticated

from core.api.views import BaseAPIView
from core.api.permissions import IsVerifiedUser, HasTwin
from .services import VoiceTwinService
from .dataclasses import CallFilterCriteria
from .serializers import (
    EnableVoiceSerializer,
    ApproveSessionSerializer,
    MakeCallSerializer,
    CallFilterSerializer,
)


class VoiceEnableView(BaseAPIView):
    """
    POST /api/v1/voice/enable
    DELETE /api/v1/voice/enable
    
    Enable or disable Voice Twin.
    Requirements: 9.1
    """
    permission_classes = [IsAuthenticated, IsVerifiedUser, HasTwin]
    
    def post(self, request):
        serializer = EnableVoiceSerializer(data=request.data)
        if not serializer.is_valid():
            return self.error_response(
                message="Validation error",
                code="VALIDATION_ERROR",
                details=serializer.errors,
                status_code=status.HTTP_400_BAD_REQUEST
            )
        
        voice_service = VoiceTwinService()
        
        # Provision phone number
        result = voice_service.provision_phone_number(
            user_id=str(request.user.id),
            area_code=serializer.validated_data.get('area_code'),
            country_code=serializer.validated_data.get('country_code', 'US')
        )
        
        if not result.success:
            return self.error_response(
                message=result.error,
                code="PROVISIONING_FAILED",
                status_code=status.HTTP_400_BAD_REQUEST
            )
        
        profile = voice_service.get_voice_profile(str(request.user.id))
        
        return self.created_response(
            data={
                "is_enabled": profile.is_enabled,
                "phone_number": profile.phone_number,
                "has_voice_clone": profile.has_voice_clone,
            },
            message="Voice Twin enabled"
        )
    
    def delete(self, request):
        voice_service = VoiceTwinService()
        
        # Terminate any active calls first
        voice_service.terminate_all_active_calls(
            user_id=str(request.user.id),
            reason="Voice Twin disabled"
        )
        
        # Disable voice twin
        profile = voice_service.disable_voice_twin(str(request.user.id))
        
        return self.success_response(
            data={"is_enabled": profile.is_enabled},
            message="Voice Twin disabled"
        )



class VoiceProfileView(BaseAPIView):
    """
    GET /api/v1/voice
    
    Get voice profile status.
    Requirements: 9.1
    """
    permission_classes = [IsAuthenticated, IsVerifiedUser]
    
    def get(self, request):
        voice_service = VoiceTwinService()
        profile = voice_service.get_voice_profile(str(request.user.id))
        
        if not profile:
            return self.success_response(
                data={
                    "is_enabled": False,
                    "has_phone_number": False,
                    "has_voice_clone": False,
                    "is_approved": False,
                }
            )
        
        return self.success_response(
            data={
                "id": profile.id,
                "is_enabled": profile.is_enabled,
                "phone_number": profile.phone_number,
                "has_phone_number": profile.has_phone_number,
                "has_voice_clone": profile.has_voice_clone,
                "voice_clone_name": profile.voice_clone_name,
                "is_approved": profile.is_approved,
                "is_voice_approved": profile.is_voice_approved,
                "approval_expires_at": profile.approval_expires_at.isoformat() if profile.approval_expires_at else None,
            }
        )


class VoiceApproveSessionView(BaseAPIView):
    """
    POST /api/v1/voice/approve-session
    DELETE /api/v1/voice/approve-session
    
    Approve or revoke voice session.
    Requirements: 9.6
    """
    permission_classes = [IsAuthenticated, IsVerifiedUser, HasTwin]
    
    def post(self, request):
        serializer = ApproveSessionSerializer(data=request.data)
        if not serializer.is_valid():
            return self.error_response(
                message="Validation error",
                code="VALIDATION_ERROR",
                details=serializer.errors,
                status_code=status.HTTP_400_BAD_REQUEST
            )
        
        voice_service = VoiceTwinService()
        
        result = voice_service.approve_voice_session(
            user_id=str(request.user.id),
            duration_minutes=serializer.validated_data.get('duration_minutes', 60),
            reason=serializer.validated_data.get('reason', '')
        )
        
        if not result.success:
            return self.error_response(
                message=result.error,
                code="APPROVAL_FAILED",
                status_code=status.HTTP_400_BAD_REQUEST
            )
        
        return self.success_response(
            data={
                "approved": True,
                "expires_at": result.expires_at.isoformat(),
                "duration_minutes": result.duration_minutes,
            },
            message="Voice session approved"
        )
    
    def delete(self, request):
        voice_service = VoiceTwinService()
        
        voice_service.revoke_voice_approval(
            user_id=str(request.user.id),
            reason="User revoked approval"
        )
        
        return self.success_response(
            data={"approved": False},
            message="Voice session approval revoked"
        )


class VoiceCallView(BaseAPIView):
    """
    POST /api/v1/voice/call
    
    Make an outbound call.
    Requirements: 9.4
    """
    permission_classes = [IsAuthenticated, IsVerifiedUser, HasTwin]
    
    def post(self, request):
        serializer = MakeCallSerializer(data=request.data)
        if not serializer.is_valid():
            return self.error_response(
                message="Validation error",
                code="VALIDATION_ERROR",
                details=serializer.errors,
                status_code=status.HTTP_400_BAD_REQUEST
            )
        
        # Check permission flag for impersonation safeguard
        if not serializer.validated_data.get('permission_flag', False):
            return self.error_response(
                message="Permission flag required to make calls as user",
                code="PERMISSION_REQUIRED",
                status_code=status.HTTP_403_FORBIDDEN
            )
        
        voice_service = VoiceTwinService()
        
        result = voice_service.make_outbound_call(
            user_id=str(request.user.id),
            target_number=serializer.validated_data['target_number'],
            script=serializer.validated_data.get('script'),
            cognitive_blend=serializer.validated_data.get('cognitive_blend')
        )
        
        if not result.success:
            return self.error_response(
                message=result.error,
                code="CALL_FAILED",
                status_code=status.HTTP_400_BAD_REQUEST
            )
        
        return self.created_response(
            data={
                "call_id": result.call_id,
                "status": result.status,
            },
            message="Call initiated"
        )


class VoiceCallDetailView(BaseAPIView):
    """
    GET /api/v1/voice/calls/{id}
    DELETE /api/v1/voice/calls/{id}
    
    Get call details or terminate a call.
    Requirements: 9.5, 9.7
    """
    permission_classes = [IsAuthenticated, IsVerifiedUser]
    
    def get(self, request, call_id):
        voice_service = VoiceTwinService()
        call = voice_service.get_call_record(call_id)
        
        if not call:
            return self.error_response(
                message="Call not found",
                code="NOT_FOUND",
                status_code=status.HTTP_404_NOT_FOUND
            )
        
        if call.user_id != str(request.user.id):
            return self.error_response(
                message="Call not found",
                code="NOT_FOUND",
                status_code=status.HTTP_404_NOT_FOUND
            )
        
        return self.success_response(
            data={
                "id": call.id,
                "direction": call.direction,
                "phone_number": call.phone_number,
                "status": call.status,
                "duration_seconds": call.duration_seconds,
                "cognitive_blend": call.cognitive_blend,
                "is_active": call.is_active,
                "has_transcript": call.has_transcript,
                "started_at": call.started_at.isoformat() if call.started_at else None,
                "ended_at": call.ended_at.isoformat() if call.ended_at else None,
                "created_at": call.created_at.isoformat(),
            }
        )
    
    def delete(self, request, call_id):
        voice_service = VoiceTwinService()
        call = voice_service.get_call_record(call_id)
        
        if not call:
            return self.error_response(
                message="Call not found",
                code="NOT_FOUND",
                status_code=status.HTTP_404_NOT_FOUND
            )
        
        if call.user_id != str(request.user.id):
            return self.error_response(
                message="Call not found",
                code="NOT_FOUND",
                status_code=status.HTTP_404_NOT_FOUND
            )
        
        result = voice_service.terminate_call(
            call_id=call_id,
            reason="User terminated call"
        )
        
        if not result.success:
            return self.error_response(
                message=result.error,
                code="TERMINATION_FAILED",
                status_code=status.HTTP_400_BAD_REQUEST
            )
        
        return self.success_response(
            data={
                "call_id": result.call_id,
                "was_active": result.was_active,
            },
            message="Call terminated" if result.was_active else "Call was not active"
        )


class VoiceCallListView(BaseAPIView):
    """
    GET /api/v1/voice/calls
    
    Get call history.
    Requirements: 9.5
    """
    permission_classes = [IsAuthenticated, IsVerifiedUser]
    
    def get(self, request):
        serializer = CallFilterSerializer(data=request.query_params)
        if not serializer.is_valid():
            return self.error_response(
                message="Validation error",
                code="VALIDATION_ERROR",
                details=serializer.errors,
                status_code=status.HTTP_400_BAD_REQUEST
            )
        
        voice_service = VoiceTwinService()
        
        filters = CallFilterCriteria(
            direction=serializer.validated_data.get('direction'),
            status=serializer.validated_data.get('status'),
            start_date=serializer.validated_data.get('start_date'),
            end_date=serializer.validated_data.get('end_date'),
        )
        
        calls = voice_service.get_call_history(
            user_id=str(request.user.id),
            filters=filters,
            limit=serializer.validated_data.get('limit', 50),
            offset=serializer.validated_data.get('offset', 0)
        )
        
        total = voice_service.count_calls(
            user_id=str(request.user.id),
            filters=filters
        )
        
        data = [
            {
                "id": c.id,
                "direction": c.direction,
                "phone_number": c.phone_number,
                "status": c.status,
                "duration_seconds": c.duration_seconds,
                "is_active": c.is_active,
                "has_transcript": c.has_transcript,
                "started_at": c.started_at.isoformat() if c.started_at else None,
                "ended_at": c.ended_at.isoformat() if c.ended_at else None,
                "created_at": c.created_at.isoformat(),
            }
            for c in calls
        ]
        
        return self.success_response(
            data={
                "calls": data,
                "total": total,
            }
        )


class VoiceCallTranscriptView(BaseAPIView):
    """
    GET /api/v1/voice/calls/{id}/transcript
    
    Get call transcript.
    Requirements: 9.5
    """
    permission_classes = [IsAuthenticated, IsVerifiedUser]
    
    def get(self, request, call_id):
        voice_service = VoiceTwinService()
        call = voice_service.get_call_record(call_id)
        
        if not call:
            return self.error_response(
                message="Call not found",
                code="NOT_FOUND",
                status_code=status.HTTP_404_NOT_FOUND
            )
        
        if call.user_id != str(request.user.id):
            return self.error_response(
                message="Call not found",
                code="NOT_FOUND",
                status_code=status.HTTP_404_NOT_FOUND
            )
        
        if not call.has_transcript:
            return self.error_response(
                message="Transcript not available",
                code="NO_TRANSCRIPT",
                status_code=status.HTTP_404_NOT_FOUND
            )
        
        return self.success_response(
            data={
                "call_id": call.id,
                "transcript": call.transcript,
                "duration_seconds": call.duration_seconds,
            }
        )
