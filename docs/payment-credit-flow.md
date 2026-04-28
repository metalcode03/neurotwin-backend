# Payment to Credit Allocation Flow

## Overview

When a user pays for a subscription upgrade via Flutterwave, the system automatically allocates credits based on their new tier. This document explains the complete flow.

## Credit Allocation by Tier

| Tier | Monthly Credits | Price (USD) |
|------|----------------|-------------|
| FREE | 50 | $0 |
| PRO | 2,000 | $20 |
| TWIN+ | 5,000 | $50 |
| EXECUTIVE | 10,000 | $100 |

## Complete Payment Flow

### 1. User Initiates Payment (Frontend)

```javascript
// User clicks "Upgrade to PRO"
const payment = {
  amount: 20,
  currency: "USD",
  customer: {
    email: user.email
  },
  meta: {
    user_id: user.id,
    tier: "pro"
  }
}
// Flutterwave payment modal opens
```

### 2. Payment Processed (Flutterwave)

- User completes payment
- Flutterwave processes transaction
- Flutterwave sends webhook to your server

### 3. Webhook Received (Backend)

**Endpoint:** `POST /api/v1/subscription/webhook/flutterwave`

**Security checks:**
1. ✅ Signature verification
2. ✅ Rate limiting
3. ✅ IP allowlist (optional)
4. ✅ Payment amount verification ($20 for PRO)
5. ✅ Idempotency check (prevents duplicates)

### 4. Subscription Upgraded

**File:** `apps/subscription/webhooks.py`

```python
# Webhook calls SubscriptionService
subscription_service = SubscriptionService()
subscription = subscription_service.upgrade(
    user_id=user_id,
    new_tier='pro'  # From webhook metadata
)
```

**What happens:**
- Updates `Subscription` model
- Changes `tier` from 'free' to 'pro'
- Sets `started_at` to now
- Records change in `SubscriptionHistory`

### 5. Credits Automatically Allocated

**File:** `apps/credits/signals.py`

```python
@receiver(post_save, sender=Subscription)
def handle_subscription_tier_change(...):
    # Triggered automatically when Subscription is saved
    
    # Get new tier allocation
    new_monthly_credits = TIER_CREDIT_ALLOCATIONS['PRO']  # 2000
    old_monthly_credits = user_credits.monthly_credits     # 50
    
    # Calculate difference
    credit_difference = 2000 - 50 = 1950
    
    # Update credits
    user_credits.monthly_credits = 2000
    user_credits.remaining_credits += 1950  # Add difference immediately
    user_credits.save()
```

**Result:**
- User's `monthly_credits` updated to 2,000
- User's `remaining_credits` increased by 1,950
- Credits available immediately for use

### 6. Cache Invalidated

**File:** `apps/credits/services.py`

The credit balance cache is automatically invalidated when credits are updated, ensuring the user sees their new balance immediately.

### 7. User Can Use Credits

User can now:
- Make AI requests using Brain modes
- Use up to 2,000 credits per month
- Access PRO-tier features (Brain Pro mode, Gemini Pro models)

## Credit Upgrade Logic

### On Upgrade (FREE → PRO)

```python
# Before upgrade
monthly_credits = 50
remaining_credits = 30  # User used 20 credits

# After upgrade
monthly_credits = 2000
remaining_credits = 30 + (2000 - 50) = 1980  # Preserves unused + adds difference
```

**Key points:**
- Unused credits are preserved
- Difference is added immediately
- User gets full benefit right away

### On Downgrade (PRO → FREE)

```python
# Before downgrade
monthly_credits = 2000
remaining_credits = 1500  # User used 500 credits

# After downgrade
monthly_credits = 50
remaining_credits = 1500  # Preserved! User keeps what they have
```

**Key points:**
- Remaining credits are NOT reduced
- User can use existing credits until next monthly reset
- Monthly allocation reduced for next cycle

## Monthly Reset

On the 1st of each month:

```python
# Automatic reset
remaining_credits = monthly_credits  # Reset to tier allocation
used_credits = 0                     # Reset usage counter
last_reset_date = today              # Update reset date
```

**Example:**
- User on PRO tier
- On March 1st: `remaining_credits` reset to 2,000
- User can use 2,000 credits in March

## Testing the Flow

### 1. Test Payment (Staging)

```bash
# Use Flutterwave test mode
# Test card: 5531886652142950
# CVV: 564
# Expiry: 09/32
# PIN: 3310
# OTP: 12345
```

### 2. Verify Subscription Updated

```python
from apps.subscription.models import Subscription

subscription = Subscription.objects.get(user_id=user_id)
print(subscription.tier)  # Should be 'pro'
```

### 3. Verify Credits Allocated

```python
from apps.credits.models import UserCredits

credits = UserCredits.objects.get(user_id=user_id)
print(f"Monthly: {credits.monthly_credits}")    # Should be 2000
print(f"Remaining: {credits.remaining_credits}") # Should be ~2000
```

### 4. Verify Payment Recorded

```python
from apps.subscription.payment_models import PaymentTransaction

tx = PaymentTransaction.objects.filter(user_id=user_id).latest('created_at')
print(f"Status: {tx.status}")           # Should be 'completed'
print(f"Amount: {tx.amount} {tx.currency}")  # Should be '20.00 USD'
print(f"Tier: {tx.tier}")               # Should be 'pro'
```

## API Endpoints

### Check Credit Balance

```bash
GET /api/v1/credits/balance
Authorization: Bearer <jwt_token>

Response:
{
  "monthly_credits": 2000,
  "remaining_credits": 1850,
  "used_credits": 150,
  "purchased_credits": 0,
  "next_reset_date": "2026-05-01",
  "days_until_reset": 15,
  "usage_percentage": 7.5
}
```

### Check Subscription

```bash
GET /api/v1/subscription
Authorization: Bearer <jwt_token>

Response:
{
  "tier": "pro",
  "tier_display": "Pro",
  "is_active": true,
  "started_at": "2026-04-16T10:30:00Z",
  "features": {
    "tier_name": "Pro",
    "available_models": ["gemini-3-flash", "gemini-3-pro", "cerebras", "mistral"],
    "has_cognitive_learning": true,
    "has_voice_twin": false,
    "has_autonomous_workflows": false
  }
}
```

## Troubleshooting

### Credits Not Allocated After Payment

**Check:**
1. Subscription tier updated?
   ```python
   Subscription.objects.get(user_id=user_id).tier
   ```

2. Signal handler executed?
   ```python
   # Check logs for "handle_subscription_tier_change"
   ```

3. UserCredits exists?
   ```python
   UserCredits.objects.filter(user_id=user_id).exists()
   ```

**Fix:**
```python
# Manually trigger credit allocation
from apps.credits.signals import handle_subscription_tier_change
subscription = Subscription.objects.get(user_id=user_id)
handle_subscription_tier_change(Subscription, subscription, created=False)
```

### Payment Successful But Subscription Not Upgraded

**Check:**
1. PaymentTransaction status
   ```python
   PaymentTransaction.objects.filter(tx_ref=tx_ref).first().status
   ```

2. Webhook logs
   ```python
   WebhookLog.objects.filter(transaction__tx_ref=tx_ref)
   ```

3. Error messages
   ```python
   tx = PaymentTransaction.objects.get(tx_ref=tx_ref)
   print(tx.error_message)
   ```

### User Has Wrong Credit Amount

**Check:**
1. Current tier vs credits
   ```python
   subscription = Subscription.objects.get(user_id=user_id)
   credits = UserCredits.objects.get(user_id=user_id)
   print(f"Tier: {subscription.tier}")
   print(f"Monthly: {credits.monthly_credits}")
   print(f"Expected: {TIER_CREDIT_ALLOCATIONS[subscription.tier.upper()]}")
   ```

**Fix:**
```python
from apps.credits.constants import TIER_CREDIT_ALLOCATIONS

subscription = Subscription.objects.get(user_id=user_id)
credits = UserCredits.objects.get(user_id=user_id)

expected = TIER_CREDIT_ALLOCATIONS[subscription.tier.upper()]
difference = expected - credits.monthly_credits

credits.monthly_credits = expected
credits.remaining_credits += difference
credits.save()
```

## Security Considerations

1. **Webhook signature verified** - Prevents fake payment notifications
2. **Amount verified** - Ensures user paid correct amount for tier
3. **Idempotency enforced** - Prevents duplicate credit allocation
4. **Atomic transactions** - Subscription + credits updated together
5. **Audit trail** - All changes logged in PaymentTransaction and SubscriptionHistory

## Summary

✅ **Automatic:** Credits allocated automatically when payment succeeds
✅ **Immediate:** Credits available right after payment
✅ **Secure:** Multiple security checks prevent fraud
✅ **Auditable:** Full trail of payment → subscription → credits
✅ **Reliable:** Atomic transactions prevent inconsistencies

The flow is fully automated - no manual intervention needed!
