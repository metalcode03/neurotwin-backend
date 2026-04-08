"""
Meta callback view for Meta Business authentication.

Handles Meta OAuth callback and completes Meta authentication flow.
Requirements: 9.1-9.8
"""

import logging
from django.shortcuts import redirect
from django.conf import settings
from rest_framework import status
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated

from apps.automation.models import InstallationSession
from apps.automation.services import InstallationService, AppMarketplaceService

logger = logging.getLogger(__name__)


class MetaCallbackView(APIView):
    """
    Handle Meta Business OAuth callback.
    
    GET /api/v1/integrations/meta/callback/
    
    Query parameters:
        - code: Meta authorization code
        - state: OAuth state for CSRF protection
        - session_id: Installation session ID
    
    This endpoint completes the Meta authentication flow and creates
    the Integration record with Meta-specific fields.
    
    Requirements: 9.1-9.8
    """
    
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        """
        Handle Meta OAuth callback.
        
        Requirements: 9.1-9.8
        """
        # Extract parameters
        authorization_code = request.query_params.get('code')
        state = request.query_params.get('state')
        session_id = request.query_params.get('session_id')
        
        # Validate parameters (Requirement 9.1)
        if not authorization_code:
            logger.error('Meta callback missing authorization code')
            return self._redirect_with_error(
                'Missing authorization code',
                'META_CALLBACK_MISSING_CODE'
            )
        
        if not state:
            logger.error('Meta callback missing state parameter')
            return self._redirect_with_error(
                'Missing state parameter',
                'META_CALLBACK_MISSING_STATE'
            )
        
        if not session_id:
            logger.error('Meta callback missing session_id')
            return self._redirect_with_error(
                'Missing session_id',
                'META_CALLBACK_MISSING_SESSION'
            )
        
        try:
            # Get installation session
            session = InstallationSession.objects.get(id=session_id)
            
            # Validate state parameter (Requirement 9.3)
            if session.oauth_state != state:
                logger.error(
                    f'Meta callback state mismatch: session={session_id}, '
                    f'expected={session.oauth_state}, received={state}'
                )
                session.status = 'failed'
                session.error_message = 'Invalid state parameter (CSRF check failed)'
                session.save()
                
                return self._redirect_with_error(
                    'Invalid state parameter',
                    'META_CALLBACK_INVALID_STATE'
                )
            
            # Complete Meta authentication (Requirements 9.4, 9.5)
            import asyncio
            
            integration = asyncio.run(
                InstallationService.complete_authentication_flow(
                    session_id=session_id,
                    authorization_code=authorization_code,
                    state=state
                )
            )
            
            # Invalidate user's installed integrations cache
            AppMarketplaceService.invalidate_user_installed_cache(request.user.id)
            
            logger.info(
                f'Meta callback completed: session={session_id}, '
                f'integration={integration.id}, user={request.user.id}, '
                f'business_id={integration.meta_business_id}'
            )
            
            # Redirect to dashboard with success message (Requirement 9.7)
            return self._redirect_with_success(
                integration_name=integration.integration_type.name,
                integration_id=str(integration.id)
            )
            
        except InstallationSession.DoesNotExist:
            logger.error(f'Meta callback session not found: session={session_id}')
            return self._redirect_with_error(
                'Installation session not found',
                'META_CALLBACK_SESSION_NOT_FOUND'
            )
        
        except Exception as e:
            logger.error(
                f'Meta callback failed: session={session_id}, error={str(e)}',
                exc_info=True
            )
            
            # Update session status (Requirement 9.8)
            try:
                session = InstallationSession.objects.get(id=session_id)
                session.status = 'failed'
                session.error_message = str(e)
                session.save()
            except:
                pass
            
            # Redirect with error message (Requirement 9.8)
            return self._redirect_with_error(
                str(e),
                'META_CALLBACK_FAILED'
            )
    
    def _redirect_with_success(self, integration_name: str, integration_id: str):
        """
        Redirect to dashboard with success message.
        
        Requirements: 9.7
        """
        dashboard_url = f"{settings.FRONTEND_URL}/dashboard/apps"
        redirect_url = (
            f"{dashboard_url}?success=true"
            f"&message=Successfully connected to {integration_name}"
            f"&integration_id={integration_id}"
        )
        return redirect(redirect_url)
    
    def _redirect_with_error(self, error_message: str, error_code: str):
        """
        Redirect to dashboard with error message and retry option.
        
        Requirements: 9.8
        """
        dashboard_url = f"{settings.FRONTEND_URL}/dashboard/apps"
        redirect_url = (
            f"{dashboard_url}?success=false"
            f"&error={error_message}"
            f"&error_code={error_code}"
            f"&retry=true"
        )
        return redirect(redirect_url)


class MetaCallbackAPIView(APIView):
    """
    API version of Meta callback (returns JSON instead of redirect).
    
    GET /api/v1/integrations/meta/callback/api/
    
    Useful for mobile apps or SPAs that prefer JSON responses.
    
    Requirements: 9.1-9.8
    """
    
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        """
        Handle Meta OAuth callback and return JSON response.
        
        Requirements: 9.1-9.8
        """
        # Extract parameters
        authorization_code = request.query_params.get('code')
        state = request.query_params.get('state')
        session_id = request.query_params.get('session_id')
        
        # Validate parameters
        if not authorization_code:
            return Response(
                {
                    'success': False,
                    'error': 'Missing authorization code',
                    'error_code': 'META_CALLBACK_MISSING_CODE'
                },
                status=status.HTTP_400_BAD_REQUEST
            )
        
        if not state:
            return Response(
                {
                    'success': False,
                    'error': 'Missing state parameter',
                    'error_code': 'META_CALLBACK_MISSING_STATE'
                },
                status=status.HTTP_400_BAD_REQUEST
            )
        
        if not session_id:
            return Response(
                {
                    'success': False,
                    'error': 'Missing session_id',
                    'error_code': 'META_CALLBACK_MISSING_SESSION'
                },
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            # Get installation session
            session = InstallationSession.objects.get(id=session_id)
            
            # Validate state parameter
            if session.oauth_state != state:
                logger.error(
                    f'Meta callback state mismatch: session={session_id}'
                )
                session.status = 'failed'
                session.error_message = 'Invalid state parameter'
                session.save()
                
                return Response(
                    {
                        'success': False,
                        'error': 'Invalid state parameter (CSRF check failed)',
                        'error_code': 'META_CALLBACK_INVALID_STATE'
                    },
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            # Complete Meta authentication
            import asyncio
            
            integration = asyncio.run(
                InstallationService.complete_authentication_flow(
                    session_id=session_id,
                    authorization_code=authorization_code,
                    state=state
                )
            )
            
            # Invalidate cache
            AppMarketplaceService.invalidate_user_installed_cache(request.user.id)
            
            logger.info(
                f'Meta callback completed: session={session_id}, '
                f'integration={integration.id}'
            )
            
            return Response(
                {
                    'success': True,
                    'message': f'Successfully connected to {integration.integration_type.name}',
                    'integration': {
                        'id': str(integration.id),
                        'type': integration.integration_type.type,
                        'name': integration.integration_type.name,
                        'meta_business_id': integration.meta_business_id,
                        'meta_waba_id': integration.meta_waba_id,
                        'meta_phone_number_id': integration.meta_phone_number_id,
                    }
                },
                status=status.HTTP_200_OK
            )
            
        except InstallationSession.DoesNotExist:
            return Response(
                {
                    'success': False,
                    'error': 'Installation session not found',
                    'error_code': 'META_CALLBACK_SESSION_NOT_FOUND'
                },
                status=status.HTTP_404_NOT_FOUND
            )
        
        except Exception as e:
            logger.error(
                f'Meta callback failed: session={session_id}, error={str(e)}',
                exc_info=True
            )
            
            # Update session status
            try:
                session = InstallationSession.objects.get(id=session_id)
                session.status = 'failed'
                session.error_message = str(e)
                session.save()
            except:
                pass
            
            return Response(
                {
                    'success': False,
                    'error': str(e),
                    'error_code': 'META_CALLBACK_FAILED',
                    'retry': True
                },
                status=status.HTTP_400_BAD_REQUEST
            )
