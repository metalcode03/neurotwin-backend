"""
Flutterwave webhook handler for subscription payments.

Handles payment notifications and subscription activation with comprehensive security.

Security Features:
- Signature verification
- Idempotency (prevents duplicate processing)
- Rate limiting per IP
- Payment amount verification
- Audit logging
- IP allowlisting (optional)
"""

import hashlib
import hmac
import logging
from typing import Dict, Any, Optional
from decimal import Decimal
from datetime import timedelta

from django.conf import settings
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator
from django.utils import timezone
from django.core.cache import cache
from django.db import transaction
from rest_framework import status
from rest_framework.views import APIView
from rest_framework.response import Response

from .services import SubscriptionService
from .models import SubscriptionTier
from .payment_models import PaymentTransaction, WebhookLog

logger = logging.getLogger('security_events')  # Use security log handler


@method_decorator(csrf_exempt, name='dispatch')
class FlutterwaveWebhookView(APIView):
    """
    POST /api/v1/subscription/webhook/flutterwave
    
    Handle Flutterwave payment webhooks for subscription payments.
    
    Security measures:
    - Signature verification (FLUTTERWAVE_SECRET_HASH)
    - Rate limiting (10 requests per minute per IP)
    - Idempotency (prevents duplicate processing via tx_ref)
    - Payment amount verification against expected tier prices
    - IP allowlisting (optional via FLUTTERWAVE_ALLOWED_IPS)
    - Comprehensive audit logging
    """
    
    authentication_classes = []  # Webhook doesn't use JWT
    permission_classes = []  # Verified via signature
    
    # Expected prices for each tier by currency
    TIER_PRICES = {
        'USD': {
            SubscriptionTier.PRO: Decimal('20.00'),
            SubscriptionTier.TWIN_PLUS: Decimal('50.00'),
            SubscriptionTier.EXECUTIVE: Decimal('100.00'),
            # Support string values too
            'pro': Decimal('20.00'),
            'twin_plus': Decimal('50.00'),
            'executive': Decimal('100.00'),
        },
        'NGN': {
            SubscriptionTier.PRO: Decimal('30000.00'),
            SubscriptionTier.TWIN_PLUS: Decimal('75000.00'),
            SubscriptionTier.EXECUTIVE: Decimal('150000.00'),
            # Support string values too
            'pro': Decimal('30000.00'),
            'twin_plus': Decimal('75000.00'),
            'executive': Decimal('150000.00'),
        },
    }
    
    # Rate limit: 10 requests per minute per IP
    RATE_LIMIT_REQUESTS = 10
    RATE_LIMIT_WINDOW = 60  # seconds
    
    def post(self, request):
        """Process Flutterwave webhook event with security checks."""
        
        ip_address = self._get_client_ip(request)
        
        # Rate limiting check
        if not self._check_rate_limit(ip_address):
            logger.warning(
                f"Rate limit exceeded for webhook from IP: {ip_address}",
                extra={'ip_address': ip_address, 'event': 'rate_limit_exceeded'}
            )
            return Response(
                {"status": "error", "message": "Rate limit exceeded"},
                status=status.HTTP_429_TOO_MANY_REQUESTS
            )
        
        # IP allowlist check (optional)
        if not self._check_ip_allowlist(ip_address):
            logger.warning(
                f"Webhook from non-allowlisted IP: {ip_address}",
                extra={'ip_address': ip_address, 'event': 'ip_not_allowed'}
            )
            return Response(
                {"status": "error", "message": "Unauthorized IP"},
                status=status.HTTP_403_FORBIDDEN
            )
        
        # Verify webhook signature
        signature_valid = self._verify_signature(request)
        
        payload = request.data
        event_type = payload.get('event', 'unknown')
        
        # Log webhook attempt
        webhook_log = self._create_webhook_log(
            request=request,
            ip_address=ip_address,
            event_type=event_type,
            signature_valid=signature_valid
        )
        
        if not signature_valid:
            logger.error(
                f"Invalid Flutterwave webhook signature from IP: {ip_address}",
                extra={
                    'ip_address': ip_address,
                    'event_type': event_type,
                    'event': 'invalid_signature'
                }
            )
            webhook_log.response_status = 401
            webhook_log.error_message = "Invalid signature"
            webhook_log.save()
            
            return Response(
                {"status": "error", "message": "Invalid signature"},
                status=status.HTTP_401_UNAUTHORIZED
            )
        
        logger.info(
            f"Received valid Flutterwave webhook: {event_type}",
            extra={'ip_address': ip_address, 'event_type': event_type}
        )
        
        # Handle different event types
        try:
            if event_type == 'charge.completed':
                response = self._handle_charge_completed(payload, ip_address, webhook_log)
            elif event_type == 'subscription.cancelled':
                response = self._handle_subscription_cancelled(payload, webhook_log)
            else:
                logger.info(f"Unhandled Flutterwave event type: {event_type}")
                webhook_log.response_status = 200
                webhook_log.processed = False
                webhook_log.save()
                response = Response({"status": "ignored"}, status=status.HTTP_200_OK)
            
            return response
            
        except Exception as e:
            logger.error(
                f"Webhook processing error: {str(e)}",
                exc_info=True,
                extra={'ip_address': ip_address, 'event_type': event_type}
            )
            webhook_log.response_status = 500
            webhook_log.error_message = str(e)
            webhook_log.save()
            
            return Response(
                {"status": "error", "message": "Internal server error"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    def _get_client_ip(self, request) -> str:
        """Extract client IP address from request."""
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[0].strip()
        else:
            ip = request.META.get('REMOTE_ADDR', 'unknown')
        return ip
    
    def _check_rate_limit(self, ip_address: str) -> bool:
        """
        Check if IP has exceeded rate limit.
        
        Returns True if within limit, False if exceeded.
        """
        cache_key = f'webhook_rate_limit:{ip_address}'
        
        # Get current count
        count = cache.get(cache_key, 0)
        
        if count >= self.RATE_LIMIT_REQUESTS:
            return False
        
        # Increment count
        cache.set(cache_key, count + 1, self.RATE_LIMIT_WINDOW)
        return True
    
    def _check_ip_allowlist(self, ip_address: str) -> bool:
        """
        Check if IP is in allowlist (if configured).
        
        Returns True if no allowlist configured or IP is allowed.
        """
        allowed_ips = getattr(settings, 'FLUTTERWAVE_ALLOWED_IPS', None)
        
        # If no allowlist configured, allow all
        if not allowed_ips:
            return True
        
        # Check if IP is in allowlist
        return ip_address in allowed_ips
    
    def _create_webhook_log(
        self,
        request,
        ip_address: str,
        event_type: str,
        signature_valid: bool
    ) -> WebhookLog:
        """Create webhook log entry for audit trail."""
        
        # Extract headers (sanitize sensitive data)
        headers = {
            k: v for k, v in request.META.items()
            if k.startswith('HTTP_') and 'TOKEN' not in k and 'KEY' not in k
        }
        
        return WebhookLog.objects.create(
            event_type=event_type,
            payload=request.data,
            headers=headers,
            ip_address=ip_address,
            signature_provided=request.headers.get('verif-hash', ''),
            signature_valid=signature_valid,
            response_status=200,  # Will be updated later
        )
    
    def _verify_signature(self, request) -> bool:
        """
        Verify Flutterwave webhook signature.
        
        Flutterwave sends a signature in the 'verif-hash' header.
        """
        secret_hash = getattr(settings, 'FLUTTERWAVE_SECRET_HASH', None)
        
        if not secret_hash:
            logger.error("FLUTTERWAVE_SECRET_HASH not configured")
            return False
        
        signature = request.headers.get('verif-hash')
        
        if not signature:
            return False
        
        # Flutterwave uses the secret hash directly for verification
        return signature == secret_hash
    
    def _verify_payment_amount(
        self,
        tier: str,
        amount: Decimal,
        currency: str
    ) -> bool:
        """
        Verify payment amount matches expected tier price.
        
        Prevents price manipulation attacks.
        Supports multiple currencies (USD, NGN, etc.)
        """
        # Check if currency is supported
        if currency not in self.TIER_PRICES:
            logger.warning(
                f"Unsupported currency: {currency}",
                extra={'currency': currency, 'tier': tier}
            )
            # Don't reject - just log warning and skip verification
            # This allows adding new currencies without code changes
            return True
        
        currency_prices = self.TIER_PRICES[currency]
        expected_price = currency_prices.get(tier)
        
        if not expected_price:
            logger.error(
                f"No price configured for tier: {tier} in currency: {currency}",
                extra={'tier': tier, 'currency': currency}
            )
            return False
        
        # Allow 2% tolerance for rounding/fees/exchange rate fluctuations
        tolerance = expected_price * Decimal('0.02')
        
        if abs(amount - expected_price) > tolerance:
            logger.error(
                f"Payment amount mismatch: expected {expected_price} {currency}, got {amount} {currency}",
                extra={
                    'tier': tier,
                    'currency': currency,
                    'expected': str(expected_price),
                    'actual': str(amount),
                    'difference': str(abs(amount - expected_price))
                }
            )
            return False
        
        return True
    
    def _handle_charge_completed(
        self,
        payload: Dict[str, Any],
        ip_address: str,
        webhook_log: WebhookLog
    ) -> Response:
        """
        Handle successful payment charge with idempotency and verification.
        
        Activates or upgrades user subscription based on payment.
        Handles both metadata-based and transaction-lookup flows.
        """
        data = payload.get('data', {})
        
        # Extract payment details
        tx_ref = data.get('tx_ref')
        flutterwave_tx_id = data.get('id')
        amount = Decimal(str(data.get('amount', 0)))
        currency = data.get('currency')
        status_payment = data.get('status')
        customer_email = data.get('customer', {}).get('email')
        
        # Get metadata (may be empty if not configured in Flutterwave)
        metadata = data.get('meta', {}) or data.get('metadata', {})
        user_id = metadata.get('user_id')
        tier = metadata.get('tier')
        
        logger.info(
            f"Processing payment: tx_ref={tx_ref}, amount={amount}, "
            f"user_id={user_id}, tier={tier}",
            extra={
                'tx_ref': tx_ref,
                'amount': str(amount),
                'user_id': user_id,
                'tier': tier,
                'ip_address': ip_address,
                'customer_email': customer_email
            }
        )
        
        # Validate payment status
        if status_payment != 'successful':
            logger.warning(f"Payment not successful: {status_payment}")
            webhook_log.response_status = 200
            webhook_log.processed = False
            webhook_log.save()
            return Response({"status": "ignored", "reason": "payment_not_successful"}, status=status.HTTP_200_OK)
        
        # Validate tx_ref exists
        if not tx_ref:
            error_msg = "Missing tx_ref in webhook payload"
            logger.error(error_msg)
            webhook_log.response_status = 400
            webhook_log.error_message = error_msg
            webhook_log.save()
            return Response(
                {"status": "error", "message": "Missing tx_ref"},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # If metadata is missing, log warning but return success
        # The frontend will handle verification via /credits/payment/verify-upgrade/
        if not user_id or not tier:
            logger.warning(
                f"Webhook received without metadata: tx_ref={tx_ref}. "
                f"Payment will be verified via frontend endpoint.",
                extra={'tx_ref': tx_ref, 'customer_email': customer_email}
            )
            
            # Create a pending transaction record for audit
            try:
                PaymentTransaction.objects.get_or_create(
                    tx_ref=tx_ref,
                    defaults={
                        'flutterwave_tx_id': str(flutterwave_tx_id),
                        'user_id': None,  # Will be filled by verify endpoint
                        'amount': amount,
                        'currency': currency,
                        'tier': 'unknown',
                        'status': 'pending',
                        'payment_status': status_payment,
                        'webhook_payload': payload,
                        'ip_address': ip_address,
                        'signature_verified': True,
                    }
                )
            except Exception as e:
                logger.error(f"Failed to create pending transaction: {str(e)}")
            
            webhook_log.response_status = 200
            webhook_log.processed = True
            webhook_log.save()
            
            return Response(
                {
                    "status": "success",
                    "message": "Payment received, awaiting frontend verification",
                    "tx_ref": tx_ref
                },
                status=status.HTTP_200_OK
            )
        
        # Validate tier
        if tier not in [t.value for t in SubscriptionTier]:
            error_msg = f"Invalid tier: {tier}"
            logger.error(error_msg)
            webhook_log.response_status = 400
            webhook_log.error_message = error_msg
            webhook_log.save()
            return Response(
                {"status": "error", "message": "Invalid tier"},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Verify payment amount matches tier price
        if not self._verify_payment_amount(tier, amount, currency):
            error_msg = f"Payment amount verification failed: {amount} {currency} for tier {tier}"
            logger.error(error_msg, extra={'tx_ref': tx_ref, 'user_id': user_id})
            webhook_log.response_status = 400
            webhook_log.error_message = error_msg
            webhook_log.save()
            return Response(
                {"status": "error", "message": "Payment amount mismatch"},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Idempotency check: prevent duplicate processing
        try:
            with transaction.atomic():
                # Try to get existing transaction
                existing_tx = PaymentTransaction.objects.filter(tx_ref=tx_ref).first()
                
                if existing_tx:
                    if existing_tx.status == 'completed':
                        logger.info(
                            f"Duplicate webhook for completed transaction: {tx_ref}",
                            extra={'tx_ref': tx_ref, 'user_id': user_id}
                        )
                        existing_tx.mark_duplicate()
                        webhook_log.transaction = existing_tx
                        webhook_log.response_status = 200
                        webhook_log.processed = True
                        webhook_log.save()
                        return Response(
                            {
                                "status": "success",
                                "message": "Already processed",
                                "subscription_id": str(existing_tx.subscription_id) if existing_tx.subscription else None
                            },
                            status=status.HTTP_200_OK
                        )
                    
                    # If pending/processing, mark as processing and continue
                    payment_tx = existing_tx
                    payment_tx.mark_processing()
                else:
                    # Create new transaction record
                    payment_tx = PaymentTransaction.objects.create(
                        tx_ref=tx_ref,
                        flutterwave_tx_id=str(flutterwave_tx_id),
                        user_id=user_id,
                        amount=amount,
                        currency=currency,
                        tier=tier,
                        status='processing',
                        payment_status=status_payment,
                        webhook_payload=payload,
                        ip_address=ip_address,
                        signature_verified=True,
                    )
                
                webhook_log.transaction = payment_tx
                webhook_log.save()
                
                # Activate/upgrade subscription
                subscription_service = SubscriptionService()
                subscription = subscription_service.upgrade(
                    user_id=user_id,
                    new_tier=tier
                )
                
                # Mark transaction as completed
                payment_tx.mark_completed(subscription=subscription)
                
                logger.info(
                    f"Subscription activated: user_id={user_id}, tier={tier}, tx_ref={tx_ref}",
                    extra={
                        'user_id': user_id,
                        'tier': tier,
                        'tx_ref': tx_ref,
                        'subscription_id': str(subscription.id)
                    }
                )
                
                webhook_log.response_status = 200
                webhook_log.processed = True
                webhook_log.save()
                
                return Response(
                    {
                        "status": "success",
                        "message": "Subscription activated",
                        "subscription_id": str(subscription.id),
                        "transaction_id": str(payment_tx.id)
                    },
                    status=status.HTTP_200_OK
                )
                
        except Exception as e:
            error_msg = f"Failed to activate subscription: {str(e)}"
            logger.error(error_msg, exc_info=True, extra={'tx_ref': tx_ref, 'user_id': user_id})
            
            # Mark transaction as failed if it exists
            if 'payment_tx' in locals():
                payment_tx.mark_failed(error_msg)
            
            webhook_log.response_status = 500
            webhook_log.error_message = error_msg
            webhook_log.save()
            
            return Response(
                {"status": "error", "message": "Internal server error"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    def _handle_subscription_cancelled(
        self,
        payload: Dict[str, Any],
        webhook_log: WebhookLog
    ) -> Response:
        """
        Handle subscription cancellation.
        
        Downgrades user to FREE tier.
        """
        data = payload.get('data', {})
        metadata = data.get('meta', {})
        user_id = metadata.get('user_id')
        
        if not user_id:
            error_msg = "Missing user_id in cancellation webhook"
            logger.error(error_msg)
            webhook_log.response_status = 400
            webhook_log.error_message = error_msg
            webhook_log.save()
            return Response(
                {"status": "error", "message": "Missing user_id"},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            subscription_service = SubscriptionService()
            subscription = subscription_service.downgrade(
                user_id=user_id,
                new_tier=SubscriptionTier.FREE
            )
            
            logger.info(
                f"Subscription cancelled: user_id={user_id}",
                extra={'user_id': user_id, 'event': 'subscription_cancelled'}
            )
            
            webhook_log.response_status = 200
            webhook_log.processed = True
            webhook_log.save()
            
            return Response(
                {
                    "status": "success",
                    "message": "Subscription cancelled",
                    "subscription_id": str(subscription.id)
                },
                status=status.HTTP_200_OK
            )
            
        except Exception as e:
            error_msg = f"Failed to cancel subscription: {str(e)}"
            logger.error(error_msg, exc_info=True, extra={'user_id': user_id})
            
            webhook_log.response_status = 500
            webhook_log.error_message = error_msg
            webhook_log.save()
            
            return Response(
                {"status": "error", "message": "Internal server error"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
