"""
Task handlers for NeuroTwin platform.

Contains the actual task implementations that are executed by the queue.
Requirements: 14.5 - Memory writes shall be asynchronous
"""

import logging
import asyncio
from typing import Dict, Any, Optional

from django.conf import settings

logger = logging.getLogger(__name__)


def handle_memory_write(
    user_id: str,
    content: str,
    source: str,
    metadata: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """
    Handle async memory write operation.
    
    Requirements: 14.5 - Memory writes shall be asynchronous
    
    Args:
        user_id: The user's ID
        content: The content to store
        source: The source of the memory
        metadata: Optional metadata
        
    Returns:
        Result dictionary with memory_id and status
    """
    try:
        from apps.memory.services import VectorMemoryEngine
        
        engine = VectorMemoryEngine()
        
        # Run the async store_memory in an event loop
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        try:
            memory = loop.run_until_complete(
                engine.store_memory(
                    user_id=user_id,
                    content=content,
                    source=source,
                    metadata=metadata,
                )
            )
            
            logger.info(f"Memory stored successfully: {memory.id}")
            
            return {
                'success': True,
                'memory_id': memory.id,
                'user_id': user_id,
            }
            
        finally:
            loop.close()
            
    except Exception as e:
        logger.error(f"Failed to store memory: {e}")
        return {
            'success': False,
            'error': str(e),
            'user_id': user_id,
        }


def handle_embedding_generation(
    user_id: str,
    content: str,
    memory_id: str,
) -> Dict[str, Any]:
    """
    Handle async embedding generation.
    
    Requirements: 14.5 - Embedding generation shall be asynchronous
    
    Args:
        user_id: The user's ID
        content: The content to generate embeddings for
        memory_id: The memory record ID
        
    Returns:
        Result dictionary with embedding status
    """
    try:
        from core.ai.services import AIService
        from apps.memory.models import MemoryRecord
        
        ai_service = AIService()
        
        # Generate embeddings
        embeddings = ai_service.generate_embeddings_sync(content)
        
        # Update the memory record
        try:
            record = MemoryRecord.objects.get(id=memory_id)
            record.has_embedding = True
            record.save(update_fields=['has_embedding'])
        except MemoryRecord.DoesNotExist:
            logger.warning(f"Memory record {memory_id} not found")
        
        logger.info(f"Embeddings generated for memory {memory_id}")
        
        return {
            'success': True,
            'memory_id': memory_id,
            'embedding_size': len(embeddings),
        }
        
    except Exception as e:
        logger.error(f"Failed to generate embeddings: {e}")
        return {
            'success': False,
            'error': str(e),
            'memory_id': memory_id,
        }


def handle_send_email(
    to_email: str,
    subject: str,
    body: str,
    template: Optional[str] = None,
    context: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """
    Handle async email sending.
    
    Args:
        to_email: Recipient email address
        subject: Email subject
        body: Email body (plain text)
        template: Optional email template name
        context: Optional template context
        
    Returns:
        Result dictionary with send status
    """
    try:
        from django.core.mail import send_mail
        from django.template.loader import render_to_string
        
        # Render template if provided
        if template and context:
            html_body = render_to_string(template, context)
        else:
            html_body = None
        
        # Send the email
        send_mail(
            subject=subject,
            message=body,
            from_email=settings.DEFAULT_FROM_EMAIL if hasattr(settings, 'DEFAULT_FROM_EMAIL') else None,
            recipient_list=[to_email],
            html_message=html_body,
            fail_silently=False,
        )
        
        logger.info(f"Email sent to {to_email}")
        
        return {
            'success': True,
            'to_email': to_email,
            'subject': subject,
        }
        
    except Exception as e:
        logger.error(f"Failed to send email: {e}")
        return {
            'success': False,
            'error': str(e),
            'to_email': to_email,
        }


def handle_learning_update(
    user_id: str,
    features: Dict[str, Any],
) -> Dict[str, Any]:
    """
    Handle async learning profile update.
    
    Requirements: 6.2 - Profile updates shall be asynchronous
    
    Args:
        user_id: The user's ID
        features: Extracted features for profile update
        
    Returns:
        Result dictionary with update status
    """
    try:
        from apps.learning.services import LearningService
        from apps.learning.dataclasses import ExtractedFeatures, ActionCategory
        
        service = LearningService()
        
        # Reconstruct ExtractedFeatures from dict
        extracted = ExtractedFeatures(
            action_type=features.get('action_type', ''),
            category=ActionCategory(features.get('category', 'interaction')),
            context=features.get('context', {}),
            patterns=features.get('patterns', []),
            sentiment=features.get('sentiment', 0.0),
            confidence=features.get('confidence', 0.5),
            personality_signals=features.get('personality_signals', {}),
            tone_signals=features.get('tone_signals', {}),
            vocabulary_additions=features.get('vocabulary_additions', []),
            decision_signals=features.get('decision_signals', {}),
        )
        
        # Run the async update_profile in an event loop
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        try:
            result = loop.run_until_complete(
                service.update_profile(user_id, extracted)
            )
            
            logger.info(f"Profile updated for user {user_id}")
            
            return {
                'success': result.success,
                'user_id': user_id,
                'updated_fields': result.updated_fields,
                'new_version': result.new_version,
                'error': result.error,
            }
            
        finally:
            loop.close()
            
    except Exception as e:
        logger.error(f"Failed to update profile: {e}")
        return {
            'success': False,
            'error': str(e),
            'user_id': user_id,
        }


def handle_token_refresh(
    integration_id: str,
) -> Dict[str, Any]:
    """
    Handle async integration token refresh.
    
    Requirements: 7.5 - Token refresh handling
    
    Args:
        integration_id: The integration ID
        
    Returns:
        Result dictionary with refresh status
    """
    try:
        from apps.automation.services import IntegrationService
        
        service = IntegrationService()
        result = service.refresh_token(integration_id)
        
        if result.success:
            logger.info(f"Token refreshed for integration {integration_id}")
        else:
            logger.warning(f"Token refresh failed for {integration_id}: {result.error}")
        
        return {
            'success': result.success,
            'integration_id': integration_id,
            'error': result.error if not result.success else None,
            'needs_reconnect': result.needs_reconnect if not result.success else False,
        }
        
    except Exception as e:
        logger.error(f"Failed to refresh token: {e}")
        return {
            'success': False,
            'error': str(e),
            'integration_id': integration_id,
        }
