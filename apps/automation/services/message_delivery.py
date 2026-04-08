"""
Message delivery service for sending messages via integrations.

Handles message delivery through Meta WhatsApp API, OAuth-based platforms,
and API key-based platforms with proper error handling and logging.

Requirements: 16.6, 21.5
"""

import logging
from typing import Dict, Any
import httpx

from django.utils import timezone

from apps.automation.models import Integration, Conversation, Message, AuthType


logger = logging.getLogger(__name__)


class MessageDeliveryService:
    """
    Service for delivering messages through various integration types.
    
    Handles Meta WhatsApp API, OAuth-based platforms, and API key-based platforms.
    Requirements: 16.6, 21.5
    """
    
    # Timeout for external API calls
    REQUEST_TIMEOUT = 30.0
    
    def send_message(
        self,
        integration: Integration,
        conversation: Conversation,
        message: Message
    ) -> Dict[str, Any]:
        """
        Send a message via the integration.
        
        Args:
            integration: Integration to send through
            conversation: Conversation context
            message: Message to send
            
        Returns:
            Dictionary with external_message_id and status
            
        Raises:
            httpx.HTTPStatusError: If API request fails
            Exception: If sending fails for other reasons
            
        Requirements: 16.6, 21.5
        """
        auth_type = integration.integration_type.auth_type
        
        try:
            if auth_type == AuthType.META:
                return self._send_meta_message(integration, conversation, message)
            elif auth_type == AuthType.OAUTH:
                return self._send_oauth_message(integration, conversation, message)
            elif auth_type == AuthType.API_KEY:
                return self._send_api_key_message(integration, conversation, message)
            else:
                raise ValueError(f"Unsupported auth_type: {auth_type}")
                
        except Exception as e:
            logger.error(
                f"Failed to send message {message.id} via {auth_type}",
                extra={
                    'integration_id': str(integration.id),
                    'conversation_id': str(conversation.id),
                    'message_id': str(message.id),
                    'error': str(e)
                }
            )
            raise
    
    def _send_meta_message(
        self,
        integration: Integration,
        conversation: Conversation,
        message: Message
    ) -> Dict[str, Any]:
        """
        Send message via Meta WhatsApp Business API.
        
        Args:
            integration: Meta integration
            conversation: Conversation context
            message: Message to send
            
        Returns:
            Dictionary with message_id and status
            
        Requirements: 16.6
        """
        # Get Meta credentials
        access_token = integration.oauth_token
        phone_number_id = integration.phone_number_id
        
        if not access_token or not phone_number_id:
            raise ValueError("Missing Meta credentials")
        
        # Build WhatsApp API request
        url = f"https://graph.facebook.com/v18.0/{phone_number_id}/messages"
        
        headers = {
            'Authorization': f'Bearer {access_token}',
            'Content-Type': 'application/json'
        }
        
        payload = {
            'messaging_product': 'whatsapp',
            'recipient_type': 'individual',
            'to': conversation.external_contact_id,
            'type': 'text',
            'text': {
                'body': message.content
            }
        }
        
        # Send request
        response = httpx.post(
            url,
            headers=headers,
            json=payload,
            timeout=self.REQUEST_TIMEOUT
        )
        response.raise_for_status()
        
        # Parse response
        result = response.json()
        external_message_id = result.get('messages', [{}])[0].get('id', '')
        
        logger.info(
            f"Sent Meta message {message.id}",
            extra={
                'integration_id': str(integration.id),
                'external_message_id': external_message_id
            }
        )
        
        return {
            'message_id': external_message_id,
            'status': 'sent',
            'platform': 'meta'
        }
    
    def _send_oauth_message(
        self,
        integration: Integration,
        conversation: Conversation,
        message: Message
    ) -> Dict[str, Any]:
        """
        Send message via OAuth-based platform.
        
        This is a generic implementation that should be customized
        per integration type (Slack, Gmail, etc.).
        
        Args:
            integration: OAuth integration
            conversation: Conversation context
            message: Message to send
            
        Returns:
            Dictionary with message_id and status
            
        Requirements: 16.6
        """
        access_token = integration.oauth_token
        
        if not access_token:
            raise ValueError("Missing OAuth access token")
        
        # Get platform-specific endpoint from integration type config
        auth_config = integration.integration_type.auth_config
        api_endpoint = auth_config.get('api_endpoint', '')
        
        if not api_endpoint:
            raise ValueError("Missing api_endpoint in integration type config")
        
        # Build request
        headers = {
            'Authorization': f'Bearer {access_token}',
            'Content-Type': 'application/json'
        }
        
        # Generic payload structure - should be customized per platform
        payload = {
            'channel': conversation.external_contact_id,
            'text': message.content,
            'metadata': message.metadata
        }
        
        # Send request
        response = httpx.post(
            api_endpoint,
            headers=headers,
            json=payload,
            timeout=self.REQUEST_TIMEOUT
        )
        response.raise_for_status()
        
        # Parse response
        result = response.json()
        external_message_id = result.get('id', result.get('message_id', ''))
        
        logger.info(
            f"Sent OAuth message {message.id}",
            extra={
                'integration_id': str(integration.id),
                'external_message_id': external_message_id
            }
        )
        
        return {
            'message_id': external_message_id,
            'status': 'sent',
            'platform': 'oauth'
        }
    
    def _send_api_key_message(
        self,
        integration: Integration,
        conversation: Conversation,
        message: Message
    ) -> Dict[str, Any]:
        """
        Send message via API key-based platform.
        
        Args:
            integration: API key integration
            conversation: Conversation context
            message: Message to send
            
        Returns:
            Dictionary with message_id and status
            
        Requirements: 16.6
        """
        api_key = integration.api_key
        
        if not api_key:
            raise ValueError("Missing API key")
        
        # Get platform configuration
        auth_config = integration.integration_type.auth_config
        api_endpoint = auth_config.get('api_endpoint', '')
        header_name = auth_config.get('authentication_header_name', 'Authorization')
        header_format = auth_config.get('header_format', 'Bearer {key}')
        
        if not api_endpoint:
            raise ValueError("Missing api_endpoint in integration type config")
        
        # Build request
        headers = {
            header_name: header_format.format(key=api_key),
            'Content-Type': 'application/json'
        }
        
        # Generic payload structure
        payload = {
            'recipient': conversation.external_contact_id,
            'message': message.content,
            'metadata': message.metadata
        }
        
        # Send request
        response = httpx.post(
            api_endpoint,
            headers=headers,
            json=payload,
            timeout=self.REQUEST_TIMEOUT
        )
        response.raise_for_status()
        
        # Parse response
        result = response.json()
        external_message_id = result.get('id', result.get('message_id', ''))
        
        logger.info(
            f"Sent API key message {message.id}",
            extra={
                'integration_id': str(integration.id),
                'external_message_id': external_message_id
            }
        )
        
        return {
            'message_id': external_message_id,
            'status': 'sent',
            'platform': 'api_key'
        }
