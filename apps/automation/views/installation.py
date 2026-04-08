"""
InstallationViewSet for integration installation workflows.

Handles installation, progress tracking, OAuth callback, and uninstallation.
Requirements: 10.4-10.6, 18.7
"""

import logging
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated

from apps.automation.models import Integration, InstallationSession
from apps.automation.serializers import (
    IntegrationSerializer,
    InstallationSessionSerializer,
    InstallationProgressSerializer,
    InstallationStartSerializer,
    InstallationResponseSerializer,
)
from apps.automation.services import InstallationService, AppMarketplaceService
from apps.automation.exceptions import MetaInstallationRateLimitExceeded
from apps.automation.services.installation import InstallationRateLimitExceeded
from apps.automation.throttling import InstallationRateThrottle, APIRateThrottle

logger = logging.getLogger(__name__)


class InstallationViewSet(viewsets.ViewSet):
    """
    ViewSet for integration installation workflows.
    
    Provides:
    - install: POST /api/v1/integrations/install/ - Start installation
    - progress: GET /api/v1/integrations/install/{id}/progress/ - Get installation progress
    - oauth_callback: GET /api/v1/integrations/oauth/callback/ - Handle OAuth callback
    - uninstall: DELETE /api/v1/integrations/{id}/uninstall/ - Uninstall integration
    - installed: GET /api/v1/integrations/installed/ - List installed integrations
    
    Requirements: 10.4-10.6, 18.7
    """
    
    permission_classes = [IsAuthenticated]
    
    def get_throttles(self):
        """
        Apply rate limiting to install action.
        
        Requirements: 18.7
        """
        if self.action == 'install':
            return [InstallationRateThrottle()]
        return []
    
    @action(detail=False, methods=['post'], throttle_classes=[InstallationRateThrottle])
    def install(self, request):
        """
        Start installation process.
        
        POST /api/v1/integrations/install/
        
        Request body:
            {
                "integration_type_id": "uuid"
            }
        
        Response (OAuth/Meta):
            {
                "session_id": "uuid",
                "authorization_url": "https://...",
                "requires_redirect": true,
                "requires_api_key": false,
                "auth_type": "oauth",
                "status": "oauth_setup",
                "message": "Installation started"
            }
        
        Response (API Key):
            {
                "session_id": "uuid",
                "authorization_url": null,
                "requires_redirect": false,
                "requires_api_key": true,
                "auth_type": "api_key",
                "status": "downloading",
                "message": "Installation started"
            }
        
        Requirements: 10.4, 12.1, 12.2, 12.3, 18.7
        """
        serializer = InstallationStartSerializer(
            data=request.data,
            context={'request': request}
        )
        
        if not serializer.is_valid():
            return Response(
                serializer.errors,
                status=status.HTTP_400_BAD_REQUEST
            )
        
        integration_type_id = serializer.validated_data['integration_type_id']
        
        try:
            # Start installation using updated service method
            result = InstallationService.start_installation(
                user=request.user,
                integration_type_id=str(integration_type_id)
            )
            
            # Build response based on auth_type
            response_data = {
                'session_id': result['session_id'],
                'authorization_url': result.get('authorization_url'),
                'requires_redirect': result['requires_redirect'],
                'requires_api_key': result['requires_api_key'],
                'auth_type': result['auth_type'],
                'status': result.get('status', 'downloading'),
                'message': self._get_install_message(result['auth_type'], result['requires_redirect'])
            }
            
            logger.info(
                f'Installation started: session={result["session_id"]}, '
                f'user={request.user.id}, integration_type={integration_type_id}, '
                f'auth_type={result["auth_type"]}'
            )
            
            return Response(
                response_data,
                status=status.HTTP_201_CREATED
            )
        
        except MetaInstallationRateLimitExceeded as e:
            # Get retry_after from exception details
            wait_seconds = e.details.get('retry_after', 60)
            
            logger.warning(
                f'Meta installation rate limit exceeded: user={request.user.id}, '
                f'integration_type={integration_type_id}, wait_seconds={wait_seconds}'
            )
            
            # Return HTTP 429 with Retry-After header (Requirements 14.3-14.4)
            response = Response(
                {
                    'error': 'Rate limit exceeded',
                    'detail': e.message,
                    'retry_after': wait_seconds
                },
                status=status.HTTP_429_TOO_MANY_REQUESTS
            )
            response['Retry-After'] = str(wait_seconds)
            return response
        
        except InstallationRateLimitExceeded as e:
            logger.warning(
                f'Installation rate limit exceeded: user={request.user.id}, '
                f'integration_type={integration_type_id}'
            )
            
            return Response(
                {
                    'error': 'Rate limit exceeded',
                    'detail': str(e)
                },
                status=status.HTTP_429_TOO_MANY_REQUESTS
            )
            
        except Exception as e:
            logger.error(
                f'Installation failed: user={request.user.id}, '
                f'integration_type={integration_type_id}, error={str(e)}'
            )
            
            return Response(
                {
                    'error': 'Installation failed',
                    'detail': str(e)
                },
                status=status.HTTP_400_BAD_REQUEST
            )
    
    def _get_install_message(self, auth_type: str, requires_redirect: bool) -> str:
        """Get appropriate installation message based on auth type."""
        if auth_type == 'api_key':
            return 'Installation started. Please provide your API key.'
        elif requires_redirect:
            return 'Installation started. Please complete authorization.'
        else:
            return 'Installation started.'
    
    @action(detail=True, methods=['get'], url_path='progress')
    def progress(self, request, pk=None):
        """
        Get installation progress.
        
        GET /api/v1/integrations/install/{session_id}/progress/
        
        Response:
            {
                "session_id": "uuid",
                "status": "oauth_setup",
                "progress": 50,
                "message": "Setting up authentication...",
                "error_message": null,
                "is_complete": false,
                "can_retry": false
            }
        
        Used for polling during installation.
        Requirements: 11.2-11.5
        """
        try:
            # Get progress from service
            progress_data = InstallationService.get_installation_progress(
                session_id=pk
            )
            
            # Serialize response
            serializer = InstallationProgressSerializer(
                data=progress_data,
                context={'request': request}
            )
            serializer.is_valid(raise_exception=True)
            
            return Response(serializer.data)
            
        except InstallationSession.DoesNotExist:
            return Response(
                {
                    'error': 'Installation session not found',
                    'detail': f'No installation session found with id {pk}'
                },
                status=status.HTTP_404_NOT_FOUND
            )
        except Exception as e:
            logger.error(
                f'Failed to get installation progress: session={pk}, error={str(e)}'
            )
            
            return Response(
                {
                    'error': 'Failed to get progress',
                    'detail': str(e)
                },
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    @action(detail=False, methods=['get'], url_path='oauth/callback')
    def oauth_callback(self, request):
        """
        Handle OAuth callback.
        
        GET /api/v1/integrations/oauth/callback/?code=...&state=...&session_id=...
        
        Query parameters:
            - code: OAuth authorization code
            - state: OAuth state for CSRF protection
            - session_id: Installation session ID
        
        This endpoint completes the OAuth flow and creates the Integration record.
        Requirements: 4.5-4.10
        """
        # Extract parameters
        authorization_code = request.query_params.get('code')
        state = request.query_params.get('state')
        session_id = request.query_params.get('session_id')
        
        # Validate parameters
        if not authorization_code:
            return Response(
                {
                    'error': 'Missing authorization code',
                    'detail': 'OAuth callback must include code parameter'
                },
                status=status.HTTP_400_BAD_REQUEST
            )
        
        if not state:
            return Response(
                {
                    'error': 'Missing state parameter',
                    'detail': 'OAuth callback must include state parameter'
                },
                status=status.HTTP_400_BAD_REQUEST
            )
        
        if not session_id:
            return Response(
                {
                    'error': 'Missing session_id',
                    'detail': 'OAuth callback must include session_id parameter'
                },
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            # Complete OAuth flow (async operation)
            import asyncio
            
            integration = asyncio.run(
                InstallationService.complete_oauth_flow(
                    session_id=session_id,
                    authorization_code=authorization_code,
                    state=state
                )
            )
            
            # Invalidate user's installed integrations cache
            AppMarketplaceService.invalidate_user_installed_cache(request.user.id)
            
            # Serialize integration
            serializer = IntegrationSerializer(integration)
            
            logger.info(
                f'OAuth callback completed: session={session_id}, '
                f'integration={integration.id}, user={request.user.id}'
            )
            
            return Response(
                {
                    'success': True,
                    'message': 'Integration installed successfully',
                    'integration': serializer.data
                },
                status=status.HTTP_200_OK
            )
            
        except Exception as e:
            logger.error(
                f'OAuth callback failed: session={session_id}, error={str(e)}'
            )
            
            return Response(
                {
                    'error': 'OAuth callback failed',
                    'detail': str(e)
                },
                status=status.HTTP_400_BAD_REQUEST
            )
    
    @action(detail=True, methods=['delete'], url_path='uninstall')
    def uninstall(self, request, pk=None):
        """
        Uninstall an integration.
        
        DELETE /api/v1/integrations/{integration_id}/uninstall/
        
        Query parameters:
            - force: Set to 'true' to skip confirmation for dependent workflows
        
        Response:
            {
                "success": true,
                "disabled_workflows": 2,
                "requires_confirmation": false,
                "dependent_workflows": ["Workflow 1", "Workflow 2"]
            }
        
        Requirements: 5.4-5.6, 18.5-18.6
        """
        force = request.query_params.get('force', 'false').lower() == 'true'
        
        try:
            # Uninstall integration
            result = InstallationService.uninstall_integration(
                user=request.user,
                integration_id=pk,
                force=force
            )
            
            if result['success']:
                # Invalidate user's installed integrations cache
                AppMarketplaceService.invalidate_user_installed_cache(request.user.id)
                
                logger.info(
                    f'Integration uninstalled: id={pk}, user={request.user.id}, '
                    f'disabled_workflows={result["disabled_workflows"]}'
                )
                
                return Response(result, status=status.HTTP_200_OK)
            else:
                # Confirmation required
                return Response(
                    result,
                    status=status.HTTP_409_CONFLICT
                )
                
        except Integration.DoesNotExist:
            return Response(
                {
                    'error': 'Integration not found',
                    'detail': f'No integration found with id {pk}'
                },
                status=status.HTTP_404_NOT_FOUND
            )
        except Exception as e:
            logger.error(
                f'Uninstallation failed: integration={pk}, '
                f'user={request.user.id}, error={str(e)}'
            )
            
            return Response(
                {
                    'error': 'Uninstallation failed',
                    'detail': str(e)
                },
                status=status.HTTP_400_BAD_REQUEST
            )
    
    @action(detail=False, methods=['get'])
    def installed(self, request):
        """
        List user's installed integrations.
        
        GET /api/v1/integrations/installed/
        
        Response:
            {
                "integrations": [
                    {
                        "id": "uuid",
                        "integration_type": {...},
                        "is_active": true,
                        "created_at": "2026-03-07T...",
                        ...
                    }
                ],
                "total": 5
            }
        
        Requirements: 10.6
        """
        # Get user's integrations
        integrations = Integration.objects.filter(
            user=request.user
        ).select_related('integration_type').order_by('-created_at')
        
        # Serialize
        serializer = IntegrationSerializer(integrations, many=True)
        
        return Response({
            'integrations': serializer.data,
            'total': integrations.count()
        })
