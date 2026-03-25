"""
CSM API views.

Requirements: 4.1-4.7, 13.1, 13.3
"""

from rest_framework import status
from rest_framework.permissions import IsAuthenticated

from core.api.views import BaseAPIView
from core.api.permissions import IsVerifiedUser
from .services import CSMService
from .serializers import (
    CSMProfileUpdateSerializer,
    CSMRollbackSerializer,
)


class CSMProfileView(BaseAPIView):
    """
    GET /api/v1/csm/profile
    PATCH /api/v1/csm/profile
    
    Get or update the current user's CSM profile.
    Requirements: 4.1, 4.2, 4.7
    """
    permission_classes = [IsAuthenticated, IsVerifiedUser]
    
    def get(self, request):
        """Get current CSM profile."""
        csm_service = CSMService()
        profile = csm_service.get_profile(str(request.user.id))
        
        if not profile:
            return self.error_response(
                message="No CSM profile found. Please complete onboarding first.",
                code="PROFILE_NOT_FOUND",
                status_code=status.HTTP_404_NOT_FOUND
            )
        
        profile_data = profile.get_profile_data()
        
        return self.success_response(
            data={
                "id": str(profile.id),
                "user_id": str(profile.user_id),
                "version": profile.version,
                "profile_data": profile_data.to_dict(),
                "is_current": profile.is_current,
                "created_at": profile.created_at.isoformat(),
                "updated_at": profile.updated_at.isoformat(),
            }
        )
    
    def patch(self, request):
        """Update CSM profile (creates new version)."""
        serializer = CSMProfileUpdateSerializer(data=request.data)
        if not serializer.is_valid():
            return self.error_response(
                message="Validation error",
                code="VALIDATION_ERROR",
                details=serializer.errors,
                status_code=status.HTTP_400_BAD_REQUEST
            )
        
        csm_service = CSMService()
        
        try:
            updated_profile = csm_service.update_profile(
                user_id=str(request.user.id),
                updates=serializer.validated_data
            )
            
            profile_data = updated_profile.get_profile_data()
            
            return self.success_response(
                data={
                    "id": str(updated_profile.id),
                    "user_id": str(updated_profile.user_id),
                    "version": updated_profile.version,
                    "profile_data": profile_data.to_dict(),
                    "is_current": updated_profile.is_current,
                    "created_at": updated_profile.created_at.isoformat(),
                    "updated_at": updated_profile.updated_at.isoformat(),
                },
                message=f"Profile updated to version {updated_profile.version}"
            )
            
        except ValueError as e:
            return self.error_response(
                message=str(e),
                code="UPDATE_FAILED",
                status_code=status.HTTP_400_BAD_REQUEST
            )


class CSMPersonalityProfileView(BaseAPIView):
    """
    GET /api/v1/csm/profile
    
    Get personality profile in frontend-friendly format.
    Transforms CSM profile data into simplified PersonalityProfile structure.
    Requirements: 4.1, 4.6
    """
    permission_classes = [IsAuthenticated, IsVerifiedUser]
    
    def get(self, request):
        csm_service = CSMService()
        profile = csm_service.get_profile(str(request.user.id))
        
        if not profile:
            return self.error_response(
                message="No CSM profile found. Complete onboarding to create your profile.",
                status_code=404
            )
        
        # Transform CSM profile to PersonalityProfile format
        profile_data = profile.get_profile_data()
        
        # Extract traits as readable strings
        traits = []
        personality = profile_data.personality
        if personality.openness > 0.6:
            traits.append("Creative & Open-minded")
        elif personality.openness < 0.4:
            traits.append("Practical & Traditional")
        
        if personality.conscientiousness > 0.6:
            traits.append("Organized & Disciplined")
        elif personality.conscientiousness < 0.4:
            traits.append("Flexible & Spontaneous")
        
        if personality.extraversion > 0.6:
            traits.append("Outgoing & Energetic")
        elif personality.extraversion < 0.4:
            traits.append("Reserved & Thoughtful")
        
        if personality.agreeableness > 0.6:
            traits.append("Cooperative & Empathetic")
        elif personality.agreeableness < 0.4:
            traits.append("Analytical & Direct")
        
        # Extract tone preferences
        tone_prefs = []
        tone = profile_data.tone
        if tone.formality > 0.6:
            tone_prefs.append("Formal & Professional")
        elif tone.formality < 0.4:
            tone_prefs.append("Casual & Relaxed")
        
        if tone.warmth > 0.6:
            tone_prefs.append("Warm & Friendly")
        elif tone.warmth < 0.4:
            tone_prefs.append("Neutral & Reserved")
        
        if tone.directness > 0.6:
            tone_prefs.append("Direct & Clear")
        elif tone.directness < 0.4:
            tone_prefs.append("Diplomatic & Nuanced")
        
        if tone.humor_level > 0.5:
            tone_prefs.append("Humorous & Lighthearted")
        
        # Format communication style
        comm = profile_data.communication
        comm_style = f"{comm.response_length.capitalize()} responses with {comm.emoji_usage} emoji usage"
        
        # Extract decision patterns
        decision_patterns = []
        decision = profile_data.decision_style
        if decision.risk_tolerance > 0.6:
            decision_patterns.append("Comfortable with calculated risks")
        elif decision.risk_tolerance < 0.4:
            decision_patterns.append("Prefers safe and proven approaches")
        
        if decision.speed_vs_accuracy > 0.6:
            decision_patterns.append("Values speed and quick decisions")
        elif decision.speed_vs_accuracy < 0.4:
            decision_patterns.append("Values thoroughness and accuracy")
        
        if decision.collaboration_preference > 0.6:
            decision_patterns.append("Prefers collaborative decision-making")
        elif decision.collaboration_preference < 0.4:
            decision_patterns.append("Prefers independent decision-making")
        
        return self.success_response(
            data={
                "userId": str(request.user.id),
                "traits": traits,
                "tonePreferences": tone_prefs,
                "communicationStyle": comm_style,
                "decisionPatterns": decision_patterns,
                "updatedAt": profile.updated_at.isoformat(),
            }
        )


class CSMHistoryView(BaseAPIView):
    """
    GET /api/v1/csm/history
    
    Get version history of CSM profile.
    Requirements: 4.7
    """
    permission_classes = [IsAuthenticated, IsVerifiedUser]
    
    def get(self, request):
        csm_service = CSMService()
        versions = csm_service.get_version_history(str(request.user.id))
        
        history = [
            {
                "id": str(v.id),
                "version": v.version,
                "is_current": v.is_current,
                "created_at": v.created_at.isoformat(),
            }
            for v in versions
        ]
        
        return self.success_response(
            data={
                "versions": history,
                "total": len(history),
            }
        )


class CSMVersionDetailView(BaseAPIView):
    """
    GET /api/v1/csm/history/<version>
    
    Get a specific version of the CSM profile.
    Requirements: 4.7
    """
    permission_classes = [IsAuthenticated, IsVerifiedUser]
    
    def get(self, request, version):
        from .models import CSMProfile
        
        profile = CSMProfile.get_version_for_user(str(request.user.id), version)
        
        if not profile:
            return self.error_response(
                message=f"Version {version} not found",
                code="VERSION_NOT_FOUND",
                status_code=status.HTTP_404_NOT_FOUND
            )
        
        profile_data = profile.get_profile_data()
        
        return self.success_response(
            data={
                "id": str(profile.id),
                "user_id": str(profile.user_id),
                "version": profile.version,
                "profile_data": profile_data.to_dict(),
                "is_current": profile.is_current,
                "created_at": profile.created_at.isoformat(),
                "updated_at": profile.updated_at.isoformat(),
            }
        )


class CSMRollbackView(BaseAPIView):
    """
    POST /api/v1/csm/rollback
    
    Rollback CSM profile to a previous version.
    Requirements: 4.7, 12.4, 12.5
    """
    permission_classes = [IsAuthenticated, IsVerifiedUser]
    
    def post(self, request):
        serializer = CSMRollbackSerializer(data=request.data)
        if not serializer.is_valid():
            return self.error_response(
                message="Validation error",
                code="VALIDATION_ERROR",
                details=serializer.errors,
                status_code=status.HTTP_400_BAD_REQUEST
            )
        
        csm_service = CSMService()
        
        try:
            restored_profile = csm_service.rollback_to_version(
                user_id=str(request.user.id),
                version=serializer.validated_data['version']
            )
            
            profile_data = restored_profile.get_profile_data()
            
            return self.success_response(
                data={
                    "id": str(restored_profile.id),
                    "user_id": str(restored_profile.user_id),
                    "version": restored_profile.version,
                    "profile_data": profile_data.to_dict(),
                    "is_current": restored_profile.is_current,
                    "created_at": restored_profile.created_at.isoformat(),
                    "rolled_back_from": serializer.validated_data['version'],
                },
                message=f"Profile rolled back to version {serializer.validated_data['version']} (now version {restored_profile.version})"
            )
            
        except ValueError as e:
            return self.error_response(
                message=str(e),
                code="ROLLBACK_FAILED",
                status_code=status.HTTP_400_BAD_REQUEST
            )
