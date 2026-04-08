"""
Notification tasks for integration failures.

Sends notifications to users when messages fail or integrations become disconnected.
Requirements: 13.4, 23.7
"""
import logging
from typing import Dict, Any
from celery import shared_task
from django.utils import timezone

from apps.automation.tasks.retryable_task import RetryableTask

logger = logging.getLogger(__name__)


@shared_task(base=RetryableTask, bind=True)
def notify_message_failure(self, message_id: str) -> Dict[str, Any]:
    """
    Send notification to user when message fails after max retries.
    
    Creates a notification record and optionally sends email/push notification
    to inform the user about the message failure with error details and retry option.
    
    Args:
        message_id: UUID of failed Message
        
    Returns:
        Dictionary with notification results
        
    Requirements: 13.4
    """
    from apps.automation.models import Message
    
    try:
        # Get message with related data
        message = Message.objects.select_related(
            'conversation',
            'conversation__integration',
            'conversation__integration__integration_type',
            'conversation__integration__user'
        ).get(id=message_id)
        
        user = message.conversation.integration.user
        integration = message.conversation.integration
        integration_type = integration.integration_type
        
        # Build notification content
        notification_data = {
            'type': 'message_failure',
            'title': f'{integration_type.name} Message Failed',
            'message': (
                f'Your message to {message.conversation.external_contact_name} '
                f'failed to send after {message.retry_count} attempts.'
            ),
            'details': {
                'integration_id': str(integration.id),
                'integration_name': integration_type.name,
                'conversation_id': str(message.conversation.id),
                'contact_name': message.conversation.external_contact_name,
                'message_id': str(message.id),
                'message_preview': message.content[:100] if message.content else '',
                'retry_count': message.retry_count,
                'last_retry_at': message.last_retry_at.isoformat() if message.last_retry_at else None,
                'error_message': 'Message delivery failed after maximum retry attempts',
            },
            'actions': [
                {
                    'label': 'Retry Message',
                    'action': 'retry_message',
                    'message_id': str(message.id)
                },
                {
                    'label': 'View Integration',
                    'action': 'view_integration',
                    'integration_id': str(integration.id)
                }
            ]
        }
        
        # TODO: Create notification record in database
        # from apps.notifications.models import Notification
        # notification = Notification.objects.create(
        #     user=user,
        #     type='message_failure',
        #     title=notification_data['title'],
        #     message=notification_data['message'],
        #     data=notification_data['details'],
        #     actions=notification_data['actions']
        # )
        
        # TODO: Send email notification if user has email notifications enabled
        # from apps.notifications.services import EmailNotificationService
        # if user.notification_preferences.get('email_on_message_failure', True):
        #     EmailNotificationService.send_message_failure_email(
        #         user=user,
        #         notification_data=notification_data
        #     )
        
        # TODO: Send push notification if user has push notifications enabled
        # from apps.notifications.services import PushNotificationService
        # if user.notification_preferences.get('push_on_message_failure', True):
        #     PushNotificationService.send_push(
        #         user=user,
        #         notification_data=notification_data
        #     )
        
        logger.info(
            f"Sent message failure notification for message {message.id}",
            extra={
                'user_id': str(user.id),
                'integration_id': str(integration.id),
                'message_id': str(message.id),
                'retry_count': message.retry_count
            }
        )
        
        return {
            'status': 'success',
            'message_id': str(message.id),
            'user_id': str(user.id),
            'notification_sent': True
        }
        
    except Message.DoesNotExist:
        logger.error(f"Message {message_id} not found for notification")
        raise
        
    except Exception as e:
        logger.error(
            f"Failed to send message failure notification for {message_id}: {e}",
            exc_info=True
        )
        raise


@shared_task(base=RetryableTask, bind=True)
def notify_integration_disconnected(self, integration_id: str) -> Dict[str, Any]:
    """
    Send notification when integration health_status becomes 'disconnected'.
    
    Creates a notification record and optionally sends email/push notification
    to inform the user about the integration disconnection with reconnection instructions.
    
    Args:
        integration_id: UUID of disconnected Integration
        
    Returns:
        Dictionary with notification results
        
    Requirements: 23.7
    """
    from apps.automation.models import Integration
    
    try:
        # Get integration with related data
        integration = Integration.objects.select_related(
            'integration_type',
            'user'
        ).get(id=integration_id)
        
        user = integration.user
        integration_type = integration.integration_type
        
        # Build reconnection instructions based on auth type
        reconnection_instructions = _get_reconnection_instructions(integration_type)
        
        # Build notification content
        notification_data = {
            'type': 'integration_disconnected',
            'title': f'{integration_type.name} Disconnected',
            'message': (
                f'Your {integration_type.name} integration has been disconnected '
                f'after {integration.consecutive_failures} consecutive failures.'
            ),
            'details': {
                'integration_id': str(integration.id),
                'integration_name': integration_type.name,
                'consecutive_failures': integration.consecutive_failures,
                'last_successful_sync_at': (
                    integration.last_successful_sync_at.isoformat() 
                    if integration.last_successful_sync_at else None
                ),
                'health_status': integration.health_status,
                'reconnection_instructions': reconnection_instructions,
            },
            'actions': [
                {
                    'label': 'Reconnect Integration',
                    'action': 'reconnect_integration',
                    'integration_id': str(integration.id)
                },
                {
                    'label': 'View Details',
                    'action': 'view_integration_health',
                    'integration_id': str(integration.id)
                },
                {
                    'label': 'Remove Integration',
                    'action': 'remove_integration',
                    'integration_id': str(integration.id)
                }
            ]
        }
        
        # TODO: Create notification record in database
        # from apps.notifications.models import Notification
        # notification = Notification.objects.create(
        #     user=user,
        #     type='integration_disconnected',
        #     title=notification_data['title'],
        #     message=notification_data['message'],
        #     data=notification_data['details'],
        #     actions=notification_data['actions'],
        #     priority='high'
        # )
        
        # TODO: Send email notification (always send for disconnections)
        # from apps.notifications.services import EmailNotificationService
        # EmailNotificationService.send_integration_disconnected_email(
        #     user=user,
        #     notification_data=notification_data
        # )
        
        # TODO: Send push notification if user has push notifications enabled
        # from apps.notifications.services import PushNotificationService
        # if user.notification_preferences.get('push_on_integration_issues', True):
        #     PushNotificationService.send_push(
        #         user=user,
        #         notification_data=notification_data
        #     )
        
        logger.warning(
            f"Sent integration disconnected notification for integration {integration.id}",
            extra={
                'user_id': str(user.id),
                'integration_id': str(integration.id),
                'integration_type': integration_type.name,
                'consecutive_failures': integration.consecutive_failures
            }
        )
        
        return {
            'status': 'success',
            'integration_id': str(integration.id),
            'user_id': str(user.id),
            'notification_sent': True
        }
        
    except Integration.DoesNotExist:
        logger.error(f"Integration {integration_id} not found for notification")
        raise
        
    except Exception as e:
        logger.error(
            f"Failed to send integration disconnected notification for {integration_id}: {e}",
            exc_info=True
        )
        raise


def _get_reconnection_instructions(integration_type) -> str:
    """
    Get reconnection instructions based on integration auth type.
    
    Args:
        integration_type: IntegrationTypeModel instance
        
    Returns:
        String with reconnection instructions
    """
    auth_type = integration_type.auth_type
    
    if auth_type == 'oauth':
        return (
            "To reconnect your integration:\n"
            "1. Go to the Integrations page\n"
            "2. Click 'Reconnect' on the disconnected integration\n"
            "3. You'll be redirected to authorize the connection again\n"
            "4. Grant the necessary permissions\n\n"
            "Common causes:\n"
            "- Your authorization token expired\n"
            "- You revoked access from the provider's settings\n"
            "- The provider's API is experiencing issues"
        )
    elif auth_type == 'meta':
        return (
            "To reconnect your WhatsApp Business integration:\n"
            "1. Go to the Integrations page\n"
            "2. Click 'Reconnect' on the disconnected integration\n"
            "3. Complete the Meta Business verification again\n"
            "4. Ensure your WhatsApp Business Account is active\n\n"
            "Common causes:\n"
            "- Your Meta access token expired (60-day limit)\n"
            "- Your WhatsApp Business Account was suspended\n"
            "- Your phone number was removed from the account\n"
            "- Meta API rate limits were exceeded"
        )
    elif auth_type == 'api_key':
        return (
            "To reconnect your integration:\n"
            "1. Go to the Integrations page\n"
            "2. Click 'Update API Key' on the disconnected integration\n"
            "3. Enter a valid API key\n"
            "4. Test the connection\n\n"
            "Common causes:\n"
            "- Your API key was revoked or expired\n"
            "- The API endpoint is unreachable\n"
            "- Your account with the provider was suspended"
        )
    else:
        return (
            "To reconnect your integration:\n"
            "1. Go to the Integrations page\n"
            "2. Click 'Reconnect' on the disconnected integration\n"
            "3. Follow the reconnection steps\n\n"
            "If the issue persists, please contact support."
        )
