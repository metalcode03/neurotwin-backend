# Flutterwave Webhook Security Guide

## Overview

The Flutterwave webhook implementation includes comprehensive security measures to prevent fraud, duplicate processing, and unauthorized access.

## Security Features

### 1. Signature Verification

Every webhook request must include a valid signature in the `verif-hash` header.

**Configuration:**
```bash
# .env
FLUTTERWAVE_SECRET_HASH=your_webhook_secret_from_dashboard
```

**How it works:**
- Flutterwave sends a secret hash with each webhook
- We verify it matches the configured `FLUTTERWAVE_SECRET_HASH`
- Invalid signatures are rejected with 401 Unauthorized

### 2. Idempotency Protection

Prevents duplicate processing of the same transaction.

**How it works:**
- Each transaction has a unique `tx_ref` (transaction reference)
- First webhook creates a `PaymentTransaction` record
- Subsequent webhooks for same `tx_ref` return success without reprocessing
- Status tracked: `pending` → `processing` → `completed`

**Benefits:**
- Network retries don't cause duplicate subscriptions
- Safe to replay webhooks for debugging
- Audit trail of all webhook attempts

### 3. Payment Amount Verification

Validates payment amount matches expected tier price.

**Configuration:**
```python
# apps/subscription/webhooks.py
TIER_PRICES = {
    SubscriptionTier.PRO: Decimal('5000.00'),        # NGN
    SubscriptionTier.TWIN_PLUS: Decimal('15000.00'), # NGN
    SubscriptionTier.EXECUTIVE: Decimal('50000.00'), # NGN
}
```

**How it works:**
- Compares received amount against expected tier price
- Allows 1% tolerance for rounding/fees
- Rejects mismatched amounts with 400 Bad Request

**Prevents:**
- Price manipulation attacks
- Users paying for PRO but getting EXECUTIVE
- Fraudulent tier upgrades

### 4. Rate Limiting

Limits webhook requests per IP address.

**Configuration:**
- 10 requests per minute per IP (default)
- Configurable via `RATE_LIMIT_REQUESTS` and `RATE_LIMIT_WINDOW`

**How it works:**
- Uses Redis cache to track request counts per IP
- Rejects excess requests with 429 Too Many Requests
- Automatically resets after time window

**Prevents:**
- DDoS attacks on webhook endpoint
- Brute force signature guessing
- Resource exhaustion

### 5. IP Allowlisting (Optional)

Restricts webhooks to known Flutterwave IPs.

**Configuration:**
```python
# neurotwin/settings.py
FLUTTERWAVE_ALLOWED_IPS = [
    '52.49.173.169',
    '52.214.14.220',
    '52.31.139.75',
    # Add Flutterwave's webhook IPs
]
```

**How it works:**
- If `FLUTTERWAVE_ALLOWED_IPS` is configured, only those IPs are accepted
- If not configured, all IPs are allowed (signature still required)
- Rejected IPs get 403 Forbidden

**Note:** Get current Flutterwave webhook IPs from their documentation.

### 6. Comprehensive Audit Logging

All webhook attempts are logged for security monitoring.

**What's logged:**

**PaymentTransaction:**
- Transaction reference and Flutterwave ID
- User, amount, currency, tier
- Payment status and processing status
- IP address and signature verification
- Full webhook payload
- Processing timestamps and errors

**WebhookLog:**
- Event type and timestamp
- IP address and headers
- Signature validity
- Processing status and response code
- Error messages

**Benefits:**
- Full audit trail for compliance
- Fraud detection and investigation
- Debugging payment issues
- Security incident response

### 7. Database Transaction Safety

Uses atomic transactions to prevent partial updates.

**How it works:**
```python
with transaction.atomic():
    # Create/update payment transaction
    # Upgrade subscription
    # Mark transaction complete
    # All or nothing
```

**Prevents:**
- Subscription upgraded but payment not recorded
- Payment recorded but subscription not upgraded
- Inconsistent state from errors

## Security Best Practices

### Environment Configuration

```bash
# Required
FLUTTERWAVE_SECRET_HASH=your_webhook_secret_hash

# Optional but recommended
FLUTTERWAVE_ALLOWED_IPS=52.49.173.169,52.214.14.220,52.31.139.75

# Payment gateway keys (for frontend)
FLUTTERWAVE_PUBLIC_KEY=your_public_key
FLUTTERWAVE_SECRET_KEY=your_secret_key
```

### Monitoring & Alerts

Monitor these metrics:

1. **Failed signature verifications**
   - Query: `WebhookLog.objects.filter(signature_valid=False)`
   - Alert if > 5 per hour

2. **Failed transactions**
   - Query: `PaymentTransaction.objects.filter(status='failed')`
   - Alert on any failures

3. **Rate limit hits**
   - Check logs for "rate_limit_exceeded" events
   - Alert if frequent from same IP

4. **Amount mismatches**
   - Check logs for "Payment amount verification failed"
   - Alert immediately (potential fraud)

### Regular Security Audits

1. **Review webhook logs weekly**
   ```python
   # Check for suspicious patterns
   WebhookLog.objects.filter(
       signature_valid=False,
       created_at__gte=timezone.now() - timedelta(days=7)
   )
   ```

2. **Verify transaction integrity**
   ```python
   # Ensure all completed transactions have subscriptions
   PaymentTransaction.objects.filter(
       status='completed',
       subscription__isnull=True
   )
   ```

3. **Check for duplicate processing**
   ```python
   # Should be rare
   PaymentTransaction.objects.filter(status='duplicate')
   ```

## Testing Webhooks

### Local Testing

1. **Use ngrok for local webhook URL:**
   ```bash
   ngrok http 8000
   ```

2. **Configure in Flutterwave Dashboard:**
   - Webhook URL: `https://your-ngrok-url.ngrok.io/api/v1/subscription/webhook/flutterwave`
   - Copy the Secret Hash to `.env`

3. **Test with Flutterwave test mode:**
   - Use test API keys
   - Make test payment
   - Verify webhook received and processed

### Production Testing

1. **Test with small amount first**
2. **Verify in admin panel:**
   - Check `PaymentTransaction` created
   - Verify `WebhookLog` shows success
   - Confirm subscription upgraded
3. **Test idempotency:**
   - Replay webhook (use admin or curl)
   - Verify returns success without duplicate upgrade

## Incident Response

### Suspicious Activity Detected

1. **Immediately check WebhookLog:**
   ```python
   WebhookLog.objects.filter(
       signature_valid=False,
       created_at__gte=suspicious_time
   ).order_by('-created_at')
   ```

2. **Block suspicious IPs (if needed):**
   ```python
   # Add to settings.py temporarily
   FLUTTERWAVE_BLOCKED_IPS = ['suspicious.ip.address']
   ```

3. **Review affected transactions:**
   ```python
   PaymentTransaction.objects.filter(
       ip_address='suspicious.ip.address'
   )
   ```

### Fraudulent Payment Detected

1. **Mark transaction as failed:**
   ```python
   tx = PaymentTransaction.objects.get(tx_ref='suspicious_ref')
   tx.mark_failed('Fraudulent payment detected')
   ```

2. **Downgrade subscription:**
   ```python
   from apps.subscription.services import SubscriptionService
   service = SubscriptionService()
   service.downgrade(user_id, SubscriptionTier.FREE, reason='fraud')
   ```

3. **Contact Flutterwave support**
4. **Document in security log**

## Compliance

### Data Retention

- `PaymentTransaction`: Retain indefinitely (financial records)
- `WebhookLog`: Retain 90 days (security logs)
- Configure cleanup job:
  ```python
  # Delete old webhook logs
  WebhookLog.objects.filter(
      created_at__lt=timezone.now() - timedelta(days=90)
  ).delete()
  ```

### PCI Compliance

- Never log full card numbers
- Never store CVV
- Flutterwave handles card data (PCI compliant)
- We only store transaction references

## Summary

The webhook implementation provides defense-in-depth security:

1. ✅ Signature verification (authentication)
2. ✅ Idempotency (prevents duplicates)
3. ✅ Amount verification (prevents fraud)
4. ✅ Rate limiting (prevents abuse)
5. ✅ IP allowlisting (optional hardening)
6. ✅ Comprehensive logging (audit trail)
7. ✅ Atomic transactions (data integrity)

**You're protected against:**
- Unauthorized webhooks
- Duplicate processing
- Price manipulation
- DDoS attacks
- Data inconsistency
- Fraud attempts

**Next steps:**
1. Configure `FLUTTERWAVE_SECRET_HASH` in production
2. Set up monitoring alerts
3. Review logs weekly
4. Test thoroughly before launch
