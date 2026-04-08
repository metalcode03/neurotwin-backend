"""
Meta Webhook Views

Handles incoming webhook events from Meta platforms (WhatsApp, Instagram).
Provides verification endpoint for webhook setup and event processing endpoint.

Requirements: 10.1-10.7
"""

import json
import logging
from datetime import datetime
from typing import Dict, Any, Optional

from django.conf import settings
from django.http import HttpResponse, JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from django.utils.decorators import method_decorator
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.request import Request
from rest_framework.response import Response

from apps.automation.utils.webhook_verifier import WebhookVerifier
from apps.automation.models import Integration, IntegrationTypeModel, WebhookEvent
from apps.automation.tasks.message_tasks import process_incoming_message

logger = logging.getLogger(__name__)


@api_view(['GET', 'POST'])
@permission_classes([AllowAny])  # Meta webhooks don't use JWT auth
def meta_webhook(request: Request) -> Response:
    """
    Meta webhook endpoint for verification and event processing.
    
    GET: Handles Meta webhook verification challenge
    POST: Processes incoming webhook events
    
    Requirements: 14.1-14.8
    """
    if request.method == 'GET':
        return _handle_verification(request)
    elif request.method == 'POST':
        return _handle_webhook_event(request)


def _handle_verification(request: Request) -> Response:
    """
    Handle Meta webhook verification challenge.
    
    During webhook setup, Meta sends a GET request with:
    - hub.mode: 'subscribe'
    - hub.verify_token: Token to verify
    - hub.challenge: Random string to echo back
    
    Requirements: 10.6-10.7
    """
    mode = request.query_params.get('hub.mode')
    token = request.query_params.get('hub.verify_token')
    challenge = request.query_params.get('hub.challenge')
    
    logger.info(f"Meta webhook verification request: mode={mode}")
    
    # Validate verification token
    expected_token = getattr(settings, 'META_WEBHOOK_VERIFY_TOKEN', None)
    
    if not expected_token:
        logger.error("META_WEBHOOK_VERIFY_TOKEN not configured")
        return Response(
            {'error': 'Webhook verification token not configured'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )
    
    if mode == 'subscribe' and WebhookVerifier.verify_token(token, expected_token):
        logger.info("Meta webhook verification successful")
        # Return challenge as plain text (Meta requirement)
        return HttpResponse(challenge, content_type='text/plain')
    else:
        logger.warning(f"Meta webhook verification failed: mode={mode}, token_valid={token == expected_token}")
        return Response(
            {'error': 'Verification failed'},
            status=status.HTTP_403_FORBIDDEN
        )


def _handle_webhook_event(request: Request) -> Response:
    """
    Process incoming Meta webhook events.
    
    Verifies signature, creates WebhookEvent record, and enqueues processing task.
    Must return HTTP 200 within 5 seconds to prevent Meta retries.
    
    Requirements: 10.1-10.5
    """
    # Get signature header
    signature_header = request.headers.get('X-Hub-Signature-256')
    
    if not signature_header:
        logger.warning("Missing X-Hub-Signature-256 header in Meta webhook")
        return Response(
            {'error': 'Missing signature'},
            status=status.HTTP_401_UNAUTHORIZED
        )
    
    # Get app secret for signature verification
    app_secret = getattr(settings, 'META_APP_SECRET', None)
    
    if not app_secret:
        logger.error("META_APP_SECRET not configured")
        return Response(
            {'error': 'Webhook signature verification not configured'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )
    
    # Verify signature (Requirement 10.2)
    if not WebhookVerifier.verify_meta_signature(
        payload=request.body,
        signature=signature_header,
        app_secret=app_secret
    ):
        logger.warning("Meta webhook signature verification failed")
        return Response(
            {'error': 'Invalid signature'},
            status=status.HTTP_401_UNAUTHORIZED
        )
    
    # Parse webhook payload
    try:
        payload = json.loads(request.body) if isinstance(request.body, bytes) else request.data
    except json.JSONDecodeError as e:
        logger.error(f"Failed to parse Meta webhook payload: {e}")
        return Response(
            {'error': 'Invalid JSON payload'},
            status=status.HTTP_400_BAD_REQUEST
        )
    
    # Extract waba_id from payload to find Integration (Requirement 10.1)
    waba_id = _extract_waba_id(payload)
    integration = None
    integration_type = None
    
    if waba_id:
        try:
            # Find integration by waba_id
            integration = Integration.objects.select_related('integration_type').get(
                waba_id=waba_id,
                status='active'
            )
            integration_type = integration.integration_type
            logger.info(f"Found integration for waba_id={waba_id}: {integration.id}")
        except Integration.DoesNotExist:
            logger.warning(f"No active integration found for waba_id={waba_id}")
        except Integration.MultipleObjectsReturned:
            logger.error(f"Multiple integrations found for waba_id={waba_id}")
            integration = Integration.objects.select_related('integration_type').filter(
                waba_id=waba_id,
                status='active'
            ).first()
            if integration:
                integration_type = integration.integration_type
    
    # Get Meta integration type if not found via integration
    if not integration_type:
        try:
            integration_type = IntegrationTypeModel.objects.get(
                key='whatsapp',
                auth_type='meta'
            )
        except IntegrationTypeModel.DoesNotExist:
            logger.error("Meta integration type not found")
            # Still return 200 to prevent retries
            return Response({'status': 'received'}, status=status.HTTP_200_OK)
    
    # Create WebhookEvent record with status='pending' (Requirement 10.4)
    try:
        webhook_event = WebhookEvent.objects.create(
            integration_type=integration_type,
            integration=integration,
            payload=payload,
            signature=signature_header,
            status='pending'
        )
        logger.info(f"Created WebhookEvent: {webhook_event.id}")
        
        # Enqueue process_incoming_message task (Requirement 10.4)
        process_incoming_message.delay(str(webhook_event.id))
        logger.info(f"Enqueued process_incoming_message task for webhook {webhook_event.id}")
        
    except Exception as e:
        logger.error(f"Error creating WebhookEvent: {e}", exc_info=True)
        # Still return 200 to prevent Meta retries
    
    # Return HTTP 200 within 5 seconds (Requirement 10.5)
    return Response({'status': 'received'}, status=status.HTTP_200_OK)


def _extract_waba_id(payload: Dict[str, Any]) -> Optional[str]:
    """
    Extract waba_id from Meta webhook payload.
    
    The waba_id can be in different locations depending on the event type.
    """
    # Try to extract from entry metadata
    entries = payload.get('entry', [])
    if entries:
        for entry in entries:
            # Check in changes
            changes = entry.get('changes', [])
            for change in changes:
                value = change.get('value', {})
                
                # Check metadata
                metadata = value.get('metadata', {})
                if 'phone_number_id' in metadata:
                    # For WhatsApp, we need to find integration by phone_number_id
                    # But we'll use waba_id if available
                    waba_id = metadata.get('display_phone_number')
                    if waba_id:
                        return waba_id
                
                # Check direct waba_id field
                if 'waba_id' in value:
                    return value['waba_id']
            
            # Check entry id (might be business_id or waba_id)
            entry_id = entry.get('id')
            if entry_id:
                return entry_id
    
    return None

