"""
Celery tasks for message processing with automatic retry.

Provides tasks for processing incoming webhooks, sending outgoing messages,
and triggering AI responses with exponential backoff retry logic.

Requirements: 11.2, 11.3, 13.1-13.7, 16.1-16.7
"""

import logging
from typing import Dict, Any
from celery import shared_task
from django.utils import timezone
from apps.automation.tasks.retryable_task import RetryableTask, TransientError


logger = logging.getLogger(__name__)


@shared_task(base=RetryableTask, bind=True)
def process_incoming_message(self, webhook_event_id: str) -> Dict[str, Any]:
    """
    Process incoming webhook message asynchronously.
    
    Parses webhook payload, creates Message and Conversation records,
    and triggers AI response if needed. Uses RetryableTask for automatic
    retry on transient failures.
    
    Args:
        webhook_event_id: UUID of WebhookEvent to process
        
    Returns:
        Dictionary with processing results
        
    Requirements: 11.2, 16.1-16.3
    """
    from apps.automation.models import WebhookEvent, Message, Conversation
    
    try:
        # Get webhook event
        event = WebhookEvent.objects.select_related(
            'integration',
            'integration__integration_type',
            'integration__user'
        ).get(id=webhook_event_id)
        
        event.status = 'processing'
        event.save(update_fields=['status', 'updated_at'])
        
        # Parse webhook payload
        payload = event.payload
        integration = event.integration
        
        # Extract message data (Meta WhatsApp format)
        messages = payload.get('entry', [{}])[0].get('changes', [{}])[0].get('value', {}).get('messages', [])
        
        if not messages:
            logger.warning(f"No messages found in webhook event {webhook_event_id}")
            event.status = 'processed'
            event.processed_at = timezone.now()
            event.save(update_fields=['status', 'processed_at', 'updated_at'])
            return {'status': 'no_messages'}
        
        message_data = messages[0]
        external_contact_id = message_data.get('from')
        message_content = message_data.get('text', {}).get('body', '')
        external_message_id = message_data.get('id')
        
        # Get contact name from profile
        contacts = payload.get('entry', [{}])[0].get('changes', [{}])[0].get('value', {}).get('contacts', [])
        contact_name = contacts[0].get('profile', {}).get('name', 'Unknown') if contacts else 'Unknown'
        
        # Get or create conversation
        conversation, created = Conversation.objects.get_or_create(
            integration=integration,
            external_contact_id=external_contact_id,
            defaults={
                'external_contact_name': contact_name,
                'status': 'active'
            }
        )
        
        # Check for duplicate message (idempotency)
        if Message.objects.filter(external_message_id=external_message_id).exists():
            logger.info(f"Duplicate message {external_message_id}, skipping")
            event.status = 'processed'
            event.processed_at = timezone.now()
            event.save(update_fields=['status', 'processed_at', 'updated_at'])
            return {'status': 'duplicate', 'message_id': external_message_id}
        
        # Create message record
        message = Message.objects.create(
            conversation=conversation,
            direction='inbound',
            content=message_content,
            status='received',
            external_message_id=external_message_id,
            metadata=payload
        )
        
        # Update conversation timestamp
        conversation.last_message_at = timezone.now()
        conversation.save(update_fields=['last_message_at', 'updated_at'])
        
        # Mark webhook as processed
        event.status = 'processed'
        event.processed_at = timezone.now()
        event.save(update_fields=['status', 'processed_at', 'updated_at'])
        
        logger.info(
            f"Processed incoming message {message.id}",
            extra={
                'integration_id': str(integration.id),
                'conversation_id': str(conversation.id),
                'message_id': str(message.id),
                'external_message_id': external_message_id
            }
        )
        
        # Trigger AI response if needed (async)
        # TODO: Implement should_trigger_ai_response logic
        # if should_trigger_ai_response(conversation, message):
        #     trigger_ai_response.delay(str(message.id))
        
        return {
            'status': 'success',
            'message_id': str(message.id),
            'conversation_id': str(conversation.id),
            'created_conversation': created
        }
        
    except WebhookEvent.DoesNotExist:
        logger.error(f"WebhookEvent {webhook_event_id} not found")
        raise
        
    except Exception as e:
        logger.error(
            f"Failed to process webhook event {webhook_event_id}: {e}",
            exc_info=True
        )
        
        # Update event status
        try:
            event = WebhookEvent.objects.get(id=webhook_event_id)
            event.status = 'failed'
            event.error_message = str(e)
            event.save(update_fields=['status', 'error_message', 'updated_at'])
        except:
            pass
        
        # Retry if transient error
        if self.should_retry(e):
            raise
        else:
            # Permanent error - don't retry
            raise


@shared_task(base=RetryableTask, bind=True)
def send_outgoing_message(self, message_id: str) -> Dict[str, Any]:
    """
    Send outgoing message with rate limiting and retry.
    
    Checks rate limits, sends message via appropriate delivery service,
    and updates message status. Uses RetryableTask for automatic retry
    on transient failures with exponential backoff.
    
    Args:
        message_id: UUID of Message to send
        
    Returns:
        Dictionary with send results
        
    Requirements: 11.3, 12.1-12.7, 13.1-13.7, 16.6, 21.5
    """
    from apps.automation.models import Message
    # from apps.automation.services import MessageDeliveryService
    # from apps.core.redis_utils import get_redis_connection
    # from apps.automation.utils.rate_limiter import RateLimiter
    
    try:
        # Get message with related data
        message = Message.objects.select_related(
            'conversation',
            'conversation__integration',
            'conversation__integration__integration_type',
            'conversation__integration__user'
        ).get(id=message_id)
        
        conversation = message.conversation
        integration = conversation.integration
        
        # Check rate limit
        # TODO: Implement rate limiting
        # rate_limiter = RateLimiter(get_redis_connection('default'))
        # rate_limit_config = integration.integration_type.rate_limit_config or {}
        # limit_per_minute = rate_limit_config.get('messages_per_minute', 20)
        # 
        # allowed, wait_seconds = rate_limiter.check_rate_limit(
        #     str(integration.id),
        #     limit_per_minute=limit_per_minute
        # )
        # 
        # if not allowed:
        #     # Retry after wait period
        #     logger.info(
        #         f"Rate limit exceeded for integration {integration.id}, "
        #         f"retrying in {wait_seconds}s"
        #     )
        #     raise self.retry(countdown=wait_seconds)
        
        # Send message via delivery service
        # TODO: Implement MessageDeliveryService
        # delivery_service = MessageDeliveryService()
        # result = delivery_service.send_message(
        #     integration=integration,
        #     conversation=conversation,
        #     message=message
        # )
        
        # Placeholder for now
        result = {
            'message_id': f"msg_{message_id[:8]}",
            'status': 'sent'
        }
        
        # Update message status
        message.status = 'sent'
        message.external_message_id = result.get('message_id')
        message.save(update_fields=['status', 'external_message_id', 'updated_at'])
        
        # Reset integration health on success
        if integration.consecutive_failures > 0:
            integration.consecutive_failures = 0
            integration.health_status = 'healthy'
            integration.last_successful_sync_at = timezone.now()
            integration.save(update_fields=[
                'consecutive_failures',
                'health_status',
                'last_successful_sync_at',
                'updated_at'
            ])
        
        logger.info(
            f"Sent outgoing message {message.id}",
            extra={
                'integration_id': str(integration.id),
                'conversation_id': str(conversation.id),
                'message_id': str(message.id),
                'external_message_id': result.get('message_id')
            }
        )
        
        return {
            'status': 'success',
            'message_id': str(message.id),
            'external_message_id': result.get('message_id')
        }
        
    except Message.DoesNotExist:
        logger.error(f"Message {message_id} not found")
        raise
        
    except Exception as e:
        logger.error(
            f"Failed to send message {message_id}: {e}",
            exc_info=True
        )
        
        # Update retry count
        try:
            message = Message.objects.get(id=message_id)
            message.retry_count += 1
            message.last_retry_at = timezone.now()
            
            # Update integration health
            integration = message.conversation.integration
            integration.consecutive_failures += 1
            
            # Mark as degraded after 3 failures
            if integration.consecutive_failures >= 3:
                integration.health_status = 'degraded'
            
            # Mark as disconnected after 10 failures
            if integration.consecutive_failures >= 10:
                integration.health_status = 'disconnected'
                
                # Notify user of disconnection
                from apps.automation.tasks.notification_tasks import notify_integration_disconnected
                notify_integration_disconnected.delay(str(integration.id))
            
            integration.save(update_fields=[
                'consecutive_failures',
                'health_status',
                'updated_at'
            ])
            
            # Check if max retries exceeded
            if message.retry_count >= 5:
                # Max retries exceeded - mark as failed
                message.status = 'failed'
                message.save(update_fields=[
                    'status',
                    'retry_count',
                    'last_retry_at',
                    'updated_at'
                ])
                
                logger.error(
                    f"Message {message.id} failed after {message.retry_count} retries",
                    extra={'error': str(e)}
                )
                
                # Notify user of failure
                from apps.automation.tasks.notification_tasks import notify_message_failure
                notify_message_failure.delay(str(message.id))
                
                # Don't retry further
                raise
            else:
                message.save(update_fields=[
                    'retry_count',
                    'last_retry_at',
                    'updated_at'
                ])
                
                # Retry if transient error
                if self.should_retry(e):
                    raise
                else:
                    # Permanent error - mark as failed
                    message.status = 'failed'
                    message.save(update_fields=['status', 'updated_at'])
                    logger.error(f"Permanent error sending message: {e}")
                    raise
                    
        except Message.DoesNotExist:
            pass
        
        raise


@shared_task(base=RetryableTask, bind=True)
def trigger_ai_response(self, message_id: str) -> Dict[str, Any]:
    """
    Trigger AI to generate response to incoming message.
    
    Fetches conversation history, generates AI response using TwinResponseService,
    creates outgoing message, and enqueues for sending.
    
    Args:
        message_id: UUID of incoming Message to respond to
        
    Returns:
        Dictionary with AI response results
        
    Requirements: 16.4
    """
    from apps.automation.models import Message
    # from apps.twin.services import TwinResponseService
    
    try:
        # Get message with related data
        message = Message.objects.select_related(
            'conversation',
            'conversation__integration',
            'conversation__integration__integration_type',
            'conversation__integration__user'
        ).get(id=message_id)
        
        conversation = message.conversation
        integration = conversation.integration
        user = integration.user
        
        # Get conversation history
        recent_messages = Message.objects.filter(
            conversation=conversation
        ).order_by('-created_at')[:10]
        
        conversation_history = [
            {
                'direction': msg.direction,
                'content': msg.content,
                'created_at': msg.created_at.isoformat()
            }
            for msg in reversed(recent_messages)
        ]
        
        # Generate AI response
        # TODO: Implement TwinResponseService
        # twin_service = TwinResponseService()
        # response_content = twin_service.generate_response(
        #     user=user,
        #     conversation_history=conversation_history,
        #     incoming_message=message.content,
        #     integration_type=integration.integration_type.type
        # )
        
        # Placeholder for now
        response_content = f"AI response to: {message.content}"
        
        # Create outgoing message
        outgoing_message = Message.objects.create(
            conversation=conversation,
            direction='outbound',
            content=response_content,
            status='pending',
            metadata={'generated_by': 'twin', 'in_reply_to': str(message.id)}
        )
        
        logger.info(
            f"Generated AI response for message {message.id}",
            extra={
                'integration_id': str(integration.id),
                'conversation_id': str(conversation.id),
                'incoming_message_id': str(message.id),
                'outgoing_message_id': str(outgoing_message.id)
            }
        )
        
        # Enqueue for sending
        send_outgoing_message.delay(str(outgoing_message.id))
        
        return {
            'status': 'success',
            'incoming_message_id': str(message.id),
            'outgoing_message_id': str(outgoing_message.id)
        }
        
    except Message.DoesNotExist:
        logger.error(f"Message {message_id} not found")
        raise
        
    except Exception as e:
        logger.error(
            f"Failed to generate AI response for message {message_id}: {e}",
            exc_info=True
        )
        
        # Retry if transient error
        if self.should_retry(e):
            raise
        else:
            raise
