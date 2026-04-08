"""
API Key completion view for API key authentication.

Handles API key validation and completes API key authentication flow.
Requirements: 12.4-12.6
"""

import logging
from rest_framework import status
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated

from apps.automation.models import InstallationSession
from apps.automation.serializers import IntegrationSerializer
from apps.automation.services import InstallationService, AppMarketplaceService

logger = logging.getLogger(__name__)


class APIKeyCompleteView(APIView):
    """
    Complete API key authentication flow.
    
    POST /api/v1/integrations/api-key/complete/
    
    Request body:
        {
            "session_id": "uuid",
            "api_key": "secret_key_here"
        }
    
    Response:
        {
            "success": true,
            "message": "Integration installed successfully",
            "integration": {
                "id": "uuid",
                "integration_type": {...},
                "is_active": true,
                ...
            }
        }
    
    This endpoint validates the API key and creates the Integration record
    with encrypted API key.
    
    Requirements: 12.4-12.6
    """
    
    permission_classes = [IsAuthenticated]
    
    def post(self, request):
        """
        Complete API key authentication.
        
        Requirements: 12.4-12.6
        """
        # Extract parameters (Requirement 12.4)
        session_id = request.data.get('session_id')
        api_key = request.data.get('api_key')
        
        # Validate parameters
        if not session_id:
            return Response(
                {
                    'success': False,
                    'error': 'Missing session_id',
                    'error_code': 'API_KEY_MISSING_SESSION'
                },
                status=status.HTTP_400_BAD_REQUEST
            )
        
        if not api_key:
            return Response(
                {
                    'success': False,
                    'error': 'Missing api_key',
                    'error_code': 'API_KEY_MISSING_KEY'
                },
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            # Get installation session (Requirement 12.5)
            session = InstallationSession.objects.get(id=session_id)
            
            # Verify session belongs to current user
            if session.user != request.user:
                logger.error(
                    f'API key completion unauthorized: session={session_id}, '
                    f'session_user={session.user.id}, request_user={request.user.id}'
                )
                return Response(
                    {
                        'success': False,
                        'error': 'Unauthorized',
                        'error_code': 'API_KEY_UNAUTHORIZED'
                    },
                    status=status.HTTP_403_FORBIDDEN
                )
            
            # Verify session is for API key auth
            if session.auth_type != 'api_key':
                logger.error(
                    f'API key completion wrong auth type: session={session_id}, '
                    f'auth_type={session.auth_type}'
                )
                return Response(
                    {
                        'success': False,
                        'error': 'Invalid session type',
                        'error_code': 'API_KEY_INVALID_SESSION_TYPE'
                    },
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            # Check if session is expired
            if session.is_expired:
                logger.error(f'API key completion session expired: session={session_id}')
                return Response(
                    {
                        'success': False,
                        'error': 'Installation session expired',
                        'error_code': 'API_KEY_SESSION_EXPIRED'
                    },
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            # Complete API key authentication (Requirement 12.5)
            import asyncio
            
            integration = asyncio.run(
                InstallationService.complete_authentication_flow(
                    session_id=session_id,
                    authorization_code='',  # Not used for API key
                    state=session.oauth_state,
                    api_key=api_key  # Pass API key as kwarg
                )
            )
            
            # Invalidate user's installed integrations cache
            AppMarketplaceService.invalidate_user_installed_cache(request.user.id)
            
            logger.info(
                f'API key completion successful: session={session_id}, '
                f'integration={integration.id}, user={request.user.id}'
            )
            
            # Serialize integration
            serializer = IntegrationSerializer(integration)
            
            # Return success response (Requirement 12.6)
            return Response(
                {
                    'success': True,
                    'message': f'Successfully connected to {integration.integration_type.name}',
                    'integration': serializer.data,
                    'integration_id': str(integration.id)
                },
                status=status.HTTP_201_CREATED
            )
            
        except InstallationSession.DoesNotExist:
            logger.error(f'API key completion session not found: session={session_id}')
            return Response(
                {
                    'success': False,
                    'error': 'Installation session not found',
                    'error_code': 'API_KEY_SESSION_NOT_FOUND'
                },
                status=status.HTTP_404_NOT_FOUND
            )
        
        except ValueError as e:
            # API key validation failed
            logger.error(
                f'API key validation failed: session={session_id}, error={str(e)}'
            )
            
            # Update session status
            try:
                session = InstallationSession.objects.get(id=session_id)
                session.status = 'failed'
                session.error_message = str(e)
                session.increment_retry()
            except:
                pass
            
            return Response(
                {
                    'success': False,
                    'error': 'Invalid API key',
                    'error_code': 'API_KEY_INVALID',
                    'detail': str(e),
                    'retry': True
                },
                status=status.HTTP_400_BAD_REQUEST
            )
        
        except Exception as e:
            logger.error(
                f'API key completion failed: session={session_id}, error={str(e)}',
                exc_info=True
            )
            
            # Update session status
            try:
                session = InstallationSession.objects.get(id=session_id)
                session.status = 'failed'
                session.error_message = str(e)
                session.increment_retry()
            except:
                pass
            
            return Response(
                {
                    'success': False,
                    'error': 'API key authentication failed',
                    'error_code': 'API_KEY_COMPLETION_FAILED',
                    'detail': str(e),
                    'retry': True
                },
                status=status.HTTP_400_BAD_REQUEST
            )
