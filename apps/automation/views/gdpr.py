"""
GDPR compliance API views.

Provides endpoints for data export and deletion to comply with GDPR
requirements for user data portability and right to be forgotten.

Requirements: 33.7
"""

import logging
from typing import Dict, Any, List

from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from django.db import transaction

from core.api.views import BaseAPIView
from core.api.permissions import IsVerifiedUser

from ..models import Integration, Conversation, Message, WebhookEvent
from ..services.auth_strategy_factory import AuthStrategyFactory

logger = logging.getLogger(__name__)


class DataExportView(BaseAPIView):
    """
    GET /api/v1/integrations/export/
    
    Export all user integration data as JSON for GDPR compliance.
    Includes integrations, conversations, messages, and webhook events.
    
    Requirements: 33.7
    """
    permission_classes = [IsAuthenticated, IsVerifiedUser]
    
    def get(self, request):
        """
        Export all integration data for the authenticated user.
        
        Returns:
            200: Complete data export as JSON
                - integrations: List of integration records
                - conversations: List of conversation records
                - messages: List of message records
                - webhook_events: List of webhook event records
                - export_metadata: Timestamp and record counts
        """
        user_id = request.user.id
        
        logger.info(f"Starting data export for user_id={user_id}")
        
        # Export integrations
        integrations_data = self._export_integrations(user_id)
        
        # Export conversations
        conversations_data = self._export_conversations(user_id)
        
        # Export messages
        messages_data = self._export_messages(user_id)
        
        # Export webhook events
        webhook_events_data = self._export_webhook_events(user_id)
        
        # Build export response
        export_data = {
            'integrations': integrations_data,
            'conversations': conversations_data,
            'messages': messages_data,
            'webhook_events': webhook_events_data,
            'export_metadata': {
                'user_id': user_id,
                'export_timestamp': self._get_current_timestamp(),
                'total_integrations': len(integrations_data),
                'total_conversations': len(conversations_data),
                'total_messages': len(messages_data),
                'total_webhook_events': len(webhook_events_data),
            }
        }
        
        logger.info(
            f"Data export completed for user_id={user_id}: "
            f"{len(integrations_data)} integrations, "
            f"{len(conversations_data)} conversations, "
            f"{len(messages_data)} messages, "
            f"{len(webhook_events_data)} webhook events"
        )
        
        return self.success_response(data=export_data)
    
    def _export_integrations(self, user_id: int) -> List[Dict[str, Any]]:
        """
        Export all integrations for the user.
        
        Note: Excludes encrypted credential fields for security.
        """
        integrations = Integration.objects.filter(
            user_id=user_id
        ).select_related('integration_type')
        
        return [
            {
                'id': str(integration.id),
                'integration_type': {
                    'id': str(integration.integration_type.id),
                    'name': integration.integration_type.name,
                    'key': integration.integration_type.key,
                    'auth_type': integration.integration_type.auth_type,
                    'category': integration.integration_type.category,
                },
                'status': integration.status,
                'health_status': integration.health_status,
                'token_expires_at': integration.token_expires_at.isoformat() if integration.token_expires_at else None,
                'user_config': integration.user_config,
                'waba_id': integration.waba_id,
                'phone_number_id': integration.phone_number_id,
                'business_id': integration.business_id,
                'last_successful_sync_at': integration.last_successful_sync_at.isoformat() if integration.last_successful_sync_at else None,
                'consecutive_failures': integration.consecutive_failures,
                'created_at': integration.created_at.isoformat(),
                'updated_at': integration.updated_at.isoformat(),
            }
            for integration in integrations
        ]
    
    def _export_conversations(self, user_id: int) -> List[Dict[str, Any]]:
        """Export all conversations for the user's integrations."""
        conversations = Conversation.objects.filter(
            integration__user_id=user_id
        ).select_related('integration')
        
        return [
            {
                'id': str(conversation.id),
                'integration_id': str(conversation.integration.id),
                'external_contact_id': conversation.external_contact_id,
                'external_contact_name': conversation.external_contact_name,
                'status': conversation.status,
                'last_message_at': conversation.last_message_at.isoformat() if conversation.last_message_at else None,
                'created_at': conversation.created_at.isoformat(),
                'updated_at': conversation.updated_at.isoformat(),
            }
            for conversation in conversations
        ]
    
    def _export_messages(self, user_id: int) -> List[Dict[str, Any]]:
        """Export all messages for the user's conversations."""
        messages = Message.objects.filter(
            conversation__integration__user_id=user_id
        ).select_related('conversation')
        
        return [
            {
                'id': str(message.id),
                'conversation_id': str(message.conversation.id),
                'direction': message.direction,
                'content': message.content,
                'status': message.status,
                'external_message_id': message.external_message_id,
                'retry_count': message.retry_count,
                'last_retry_at': message.last_retry_at.isoformat() if message.last_retry_at else None,
                'metadata': message.metadata,
                'created_at': message.created_at.isoformat(),
                'updated_at': message.updated_at.isoformat(),
            }
            for message in messages
        ]
    
    def _export_webhook_events(self, user_id: int) -> List[Dict[str, Any]]:
        """Export all webhook events for the user's integrations."""
        webhook_events = WebhookEvent.objects.filter(
            integration__user_id=user_id
        ).select_related('integration', 'integration_type')
        
        return [
            {
                'id': str(event.id),
                'integration_type_id': str(event.integration_type.id) if event.integration_type else None,
                'integration_id': str(event.integration.id) if event.integration else None,
                'payload': event.payload,
                'signature': event.signature,
                'status': event.status,
                'error_message': event.error_message,
                'processed_at': event.processed_at.isoformat() if event.processed_at else None,
                'created_at': event.created_at.isoformat(),
                'updated_at': event.updated_at.isoformat(),
            }
            for event in webhook_events
        ]
    
    def _get_current_timestamp(self) -> str:
        """Get current timestamp in ISO format."""
        from django.utils import timezone
        return timezone.now().isoformat()


class DataDeletionView(BaseAPIView):
    """
    DELETE /api/v1/integrations/delete-all/
    
    Delete all user integration data for GDPR compliance.
    Revokes credentials with providers and cascades deletion.
    
    Requirements: 33.7
    """
    permission_classes = [IsAuthenticated, IsVerifiedUser]
    
    def delete(self, request):
        """
        Delete all integration data for the authenticated user.
        
        This endpoint:
        1. Retrieves all user integrations
        2. Attempts to revoke credentials with each provider
        3. Deletes all integrations (cascade deletes conversations, messages, webhooks)
        4. Logs deletion for audit trail
        5. Continues deletion even if revocation fails
        
        Returns:
            200: Deletion summary with counts and revocation status
        """
        user_id = request.user.id
        
        logger.info(f"Starting complete data deletion for user_id={user_id}")
        
        # Get all integrations for the user
        integrations = Integration.objects.filter(
            user_id=user_id
        ).select_related('integration_type')
        
        if not integrations.exists():
            return self.success_response(
                data={
                    'message': 'No integration data found to delete',
                    'deleted_integrations': 0,
                    'deleted_conversations': 0,
                    'deleted_messages': 0,
                    'deleted_webhook_events': 0,
                }
            )
        
        # Count records before deletion
        integration_count = integrations.count()
        conversation_count = Conversation.objects.filter(integration__user_id=user_id).count()
        message_count = Message.objects.filter(conversation__integration__user_id=user_id).count()
        webhook_count = WebhookEvent.objects.filter(integration__user_id=user_id).count()
        
        # Revoke credentials for each integration
        revocation_results = []
        for integration in integrations:
            revocation_success = self._revoke_credentials(integration)
            revocation_results.append({
                'integration_id': str(integration.id),
                'integration_type': integration.integration_type.name,
                'revocation_success': revocation_success,
            })
        
        # Delete all integrations (cascade will delete related records)
        with transaction.atomic():
            integrations.delete()
        
        # Log deletion event
        logger.info(
            f"Complete data deletion for user_id={user_id}: "
            f"deleted_integrations={integration_count}, "
            f"deleted_conversations={conversation_count}, "
            f"deleted_messages={message_count}, "
            f"deleted_webhooks={webhook_count}"
        )
        
        return self.success_response(
            data={
                'message': 'All integration data has been deleted',
                'deleted_integrations': integration_count,
                'deleted_conversations': conversation_count,
                'deleted_messages': message_count,
                'deleted_webhook_events': webhook_count,
                'revocation_results': revocation_results,
            }
        )
    
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
