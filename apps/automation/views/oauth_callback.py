"""
OAuth callback handler view.

Handles OAuth provider redirects after user authorization,
validates state, exchanges code for tokens, and redirects to dashboard.

Requirements: 4.5-4.10
"""

import logging
from django.shortcuts import redirect
from django.contrib import messages
from django.views import View
from django.http import HttpResponse
from django.core.exceptions import ValidationError

from apps.automation.services.installation import InstallationService
from apps.automation.utils.oauth_state import OAuthStateManager


logger = logging.getLogger(__name__)


class OAuthCallbackView(View):
    """
    OAuth callback handler view.
    
    Handles OAuth provider redirects after user authorization.
    Validates state parameter, exchanges authorization code for tokens,
    and redirects to dashboard with success/error messages.
    
    Requirements: 4.5-4.10
    - Validate state parameter matches session
    - Extract authorization code from query params
    - Call InstallationService.complete_oauth_flow
    - Handle success: redirect to dashboard with success message
    - Handle errors: redirect with error message and retry option
    """
    
    def get(self, request):
        """
        Handle OAuth callback GET request.
        
        Query parameters:
            - code: OAuth authorization code
            - state: OAuth state for CSRF protection
            - session_id: Installation session ID (optional, can be in state)
            - error: OAuth error (if authorization was denied)
            - error_description: OAuth error description
        
        Returns:
            HttpResponse: Redirect to dashboard or error page
        """
        # Check for OAuth errors (user cancelled or provider error)
        oauth_error = request.GET.get('error')
        if oauth_error:
            error_description = request.GET.get(
                'error_description',
                'Authorization was cancelled or failed'
            )
            
            logger.warning(
                f"OAuth authorization error: {oauth_error} - {error_description}"
            )
            
            messages.error(
                request,
                f"Installation failed: {error_description}. "
                "You can try again from the App Marketplace."
            )
            
            return redirect('dashboard:apps')
        
        # Extract required parameters
        authorization_code = request.GET.get('code')
        state = request.GET.get('state')
        session_id = request.GET.get('session_id')
        
        # Validate required parameters
        if not authorization_code:
            logger.error("OAuth callback missing authorization code")
            messages.error(
                request,
                "Installation failed: Missing authorization code. Please try again."
            )
            return redirect('dashboard:apps')
        
        if not state:
            logger.error("OAuth callback missing state parameter")
            messages.error(
                request,
                "Installation failed: Missing state parameter (security check failed). "
                "Please try again."
            )
            return redirect('dashboard:apps')
        
        if not session_id:
            logger.error("OAuth callback missing session_id")
            messages.error(
                request,
                "Installation failed: Missing session ID. Please try again."
            )
            return redirect('dashboard:apps')
        
        try:
            # Validate state and get session
            session = OAuthStateManager.validate_and_get_session(
                session_id=session_id,
                state=state
            )
            
            # Verify session belongs to current user
            if session.user_id != request.user.id:
                logger.error(
                    f"Session {session_id} belongs to different user. "
                    f"Session user: {session.user_id}, Request user: {request.user.id}"
                )
                messages.error(
                    request,
                    "Installation failed: Session validation error. Please try again."
                )
                return redirect('dashboard:apps')
            
            # Complete OAuth flow (async operation)
            import asyncio
            
            integration = asyncio.run(
                InstallationService.complete_oauth_flow(
                    session_id=session_id,
                    authorization_code=authorization_code,
                    state=state
                )
            )
            
            # Success - redirect to dashboard with success message
            integration_name = integration.integration_type.name
            
            logger.info(
                f"OAuth callback completed successfully: "
                f"session={session_id}, integration={integration.id}, "
                f"user={request.user.id}, type={integration_name}"
            )
            
            messages.success(
                request,
                f"{integration_name} installed successfully! "
                f"Your automation templates are now available."
            )
            
            # Redirect to automation dashboard to show new workflows
            return redirect('dashboard:automation')
            
        except ValidationError as e:
            # State validation failed (CSRF attack or expired session)
            logger.error(f"OAuth state validation failed: {str(e)}")
            
            messages.error(
                request,
                f"Installation failed: {str(e)}. Please try again."
            )
            
            return redirect('dashboard:apps')
            
        except Exception as e:
            # Token exchange or other error
            logger.error(
                f"OAuth callback failed: session={session_id}, error={str(e)}",
                exc_info=True
            )
            
            # Provide user-friendly error message with retry option
            error_message = str(e)
            
            # Check if it's a token exchange error
            if 'token exchange' in error_message.lower():
                messages.error(
                    request,
                    "Installation failed during authentication setup. "
                    "This might be a temporary issue. Please try again."
                )
            elif 'network' in error_message.lower() or 'connection' in error_message.lower():
                messages.error(
                    request,
                    "Installation failed due to network error. "
                    "Please check your connection and try again."
                )
            else:
                messages.error(
                    request,
                    f"Installation failed: {error_message}. "
                    "Please try again or contact support if the issue persists."
                )
            
            return redirect('dashboard:apps')


class OAuthCallbackAPIView(View):
    """
    OAuth callback handler for API clients (returns JSON instead of redirect).
    
    This is useful for mobile apps or SPAs that handle OAuth in a popup/webview.
    """
    
    def get(self, request):
        """
        Handle OAuth callback and return JSON response.
        
        Returns:
            HttpResponse: JSON response with success/error status
        """
        import json
        from django.http import JsonResponse
        
        # Check for OAuth errors
        oauth_error = request.GET.get('error')
        if oauth_error:
            error_description = request.GET.get(
                'error_description',
                'Authorization was cancelled or failed'
            )
            
            return JsonResponse({
                'success': False,
                'error': oauth_error,
                'message': error_description
            }, status=400)
        
        # Extract parameters
        authorization_code = request.GET.get('code')
        state = request.GET.get('state')
        session_id = request.GET.get('session_id')
        
        # Validate parameters
        if not all([authorization_code, state, session_id]):
            return JsonResponse({
                'success': False,
                'error': 'missing_parameters',
                'message': 'Missing required parameters (code, state, or session_id)'
            }, status=400)
        
        try:
            # Validate state
            session = OAuthStateManager.validate_and_get_session(
                session_id=session_id,
                state=state
            )
            
            # Complete OAuth flow
            import asyncio
            
            integration = asyncio.run(
                InstallationService.complete_oauth_flow(
                    session_id=session_id,
                    authorization_code=authorization_code,
                    state=state
                )
            )
            
            return JsonResponse({
                'success': True,
                'message': 'Integration installed successfully',
                'integration_id': str(integration.id),
                'integration_type': integration.integration_type.name
            })
            
        except ValidationError as e:
            return JsonResponse({
                'success': False,
                'error': 'validation_error',
                'message': str(e)
            }, status=400)
            
        except Exception as e:
            logger.error(f"OAuth callback API failed: {str(e)}", exc_info=True)
            
            return JsonResponse({
                'success': False,
                'error': 'installation_failed',
                'message': str(e)
            }, status=500)
