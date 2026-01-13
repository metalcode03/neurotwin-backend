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
