"""
Integration management API views.

Provides endpoints for listing, viewing, and deleting integrations
with proper ownership verification and credential revocation.

Requirements: 20.1-20.3, 23.1-23.7, 28.1-28.7, 33.6
"""

import logging
from typing import Optional

from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from django.db.models import Prefetch

from core.api.views import BaseAPIView
from core.api.permissions import IsVerifiedUser

from ..models import Integration, IntegrationTypeModel, Conversation, Message, WebhookEvent
from ..services.auth_strategy_factory import AuthStrategyFactory
from ..serializers.integration import IntegrationSerializer
from ..security import SecurityEventLogger, get_client_ip

logger = logging.getLogger(__name__)


class IntegrationListView(BaseAPIView):
    """
    GET /api/v1/integrations/
    
    List user's integrations with select_related optimization.
    Supports filtering by status.
    
    Requirements: 20.1-20.3
    """
    permission_classes = [IsAuthenticated, IsVerifiedUser]
    
    def get(self, request):
        """
        List all integrations for the authenticated user.
        
        Query Parameters:
            status: Optional filter by status (active, disconnected, expired, revoked)
        
        Returns:
            200: List of integrations with integration_type details
        """
        # Get query parameters
        status_filter = request.query_params.get('status')
        
        # Build queryset with select_related to avoid N+1 queries
        queryset = Integration.objects.filter(
            user=request.user
        ).select_related(
            'integration_type'
        ).order_by('-created_at')
        
        # Apply status filter if provided
        if status_filter:
            queryset = queryset.filter(status=status_filter)
        
        # Serialize integrations
        serializer = IntegrationSerializer(queryset, many=True)
        
        return self.success_response(
            data={
                'integrations': serializer.data,
                'total': queryset.count(),
            }
        )


class IntegrationDetailView(BaseAPIView):
    """
    GET /api/v1/integrations/{id}/
    
    Get integration details including health status.
    Verifies user ownership.
    
    Requirements: 23.1-23.7
    """
    permission_classes = [IsAuthenticated, IsVerifiedUser]
    
    def get(self, request, integration_id):
        """
        Get detailed information about a specific integration.
        
        Path Parameters:
            integration_id: UUID of the integration
        
        Returns:
            200: Integration details with health status
            404: Integration not found or user doesn't own it
        """
        # Get integration with select_related
        integration = self._get_user_integration(request.user.id, integration_id)
        
        if not integration:
            return self.error_response(
                message="Integration not found",
                code="NOT_FOUND",
                status_code=status.HTTP_404_NOT_FOUND
            )
        
        # Serialize with full details
        serializer = IntegrationSerializer(integration)
        
        return self.success_response(data=serializer.data)
    
    def _get_user_integration(self, user_id: int, integration_id: str) -> Optional[Integration]:
        """
        Get integration if it belongs to the user.
        
        Args:
            user_id: User ID
            integration_id: Integration UUID
            
        Returns:
            Integration if found and owned by user, None otherwise
        """
        try:
            return Integration.objects.select_related(
                'integration_type'
            ).get(
                id=integration_id,
                user_id=user_id
            )
        except Integration.DoesNotExist:
            return None


class IntegrationDeleteView(BaseAPIView):
    """
    DELETE /api/v1/integrations/{id}/
    
    Delete integration with credential revocation and cascade deletion.
    Continues deletion even if revocation fails.
    
    Requirements: 28.1-28.7
    """
    permission_classes = [IsAuthenticated, IsVerifiedUser]
    
    def delete(self, request, integration_id):
        """
        Delete an integration and all associated data.
        
        This endpoint:
        1. Verifies user ownership
        2. Attempts to revoke credentials with the provider
        3. Deletes associated Conversation, Message, and WebhookEvent records
        4. Logs the uninstallation event
        5. Continues deletion even if revocation fails
        
        Path Parameters:
            integration_id: UUID of the integration
        
        Returns:
            204: Integration deleted successfully
            404: Integration not found or user doesn't own it
        """
        # Get integration with select_related
        integration = self._get_user_integration(request.user.id, integration_id)
        
        if not integration:
            return self.error_response(
                message="Integration not found",
                code="NOT_FOUND",
                status_code=status.HTTP_404_NOT_FOUND
            )
        
        # Store integration details for logging
        integration_type_name = integration.integration_type.name
        integration_type_id = str(integration.integration_type.id)
        auth_type = integration.integration_type.auth_type
        
        # Attempt to revoke credentials with provider
        revocation_success = self._revoke_credentials(integration)
        
        if not revocation_success:
            logger.warning(
                f"Failed to revoke credentials for integration {integration_id}, "
                f"but continuing with deletion"
            )
        
        # Delete associated records (cascade will handle this, but we log it)
        conversation_count = Conversation.objects.filter(integration=integration).count()
        message_count = Message.objects.filter(conversation__integration=integration).count()
        webhook_count = WebhookEvent.objects.filter(integration=integration).count()
        
        # Delete the integration (cascade will delete related records)
        integration.delete()
        
        # Log uninstallation event with SecurityEventLogger
        SecurityEventLogger.log_integration_deletion(
            user_id=str(request.user.id),
            integration_id=str(integration_id),
            integration_type=integration_type_name,
            revocation_success=revocation_success,
            ip_address=get_client_ip(request)
        )
        
        # Also log detailed information
        logger.info(
            f"Integration uninstalled: user_id={request.user.id}, "
            f"integration_id={integration_id}, "
            f"integration_type={integration_type_name}, "
            f"auth_type={auth_type}, "
            f"revocation_success={revocation_success}, "
            f"deleted_conversations={conversation_count}, "
            f"deleted_messages={message_count}, "
            f"deleted_webhooks={webhook_count}"
        )
        
        return self.no_content_response()
    
    def _get_user_integration(self, user_id: int, integration_id: str) -> Optional[Integration]:
        """
        Get integration if it belongs to the user.
        
        Args:
            user_id: User ID
            integration_id: Integration UUID
            
        Returns:
            Integration if found and owned by user, None otherwise
        """
        try:
            return Integration.objects.select_related(
                'integration_type'
            ).get(
                id=integration_id,
                user_id=user_id
            )
        except Integration.DoesNotExist:
            return None
    
    def _revoke_credentials(self, integration: Integration) -> bool:
        """
        Attempt to revoke credentials with the provider.
        
        Uses the appropriate authentication strategy to revoke credentials.
        Logs errors but doesn't raise exceptions.
        
        Args:
            integration: Integration to revoke credentials for
            
        Returns:
            True if revocation succeeded, False otherwise
        """
        try:
            # Create authentication strategy for this integration type
            strategy = AuthStrategyFactory.create_strategy(integration.integration_type)
            
            # Attempt to revoke credentials
            success = strategy.revoke_credentials(integration)
            
            if success:
                logger.info(
                    f"Successfully revoked credentials for integration {integration.id}"
                )
            else:
                logger.warning(
                    f"Credential revocation returned False for integration {integration.id}"
                )
            
            return success
            
        except Exception as e:
            logger.error(
                f"Error revoking credentials for integration {integration.id}: {str(e)}",
                exc_info=True
            )
            return False
