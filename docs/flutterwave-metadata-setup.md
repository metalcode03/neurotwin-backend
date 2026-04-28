# Flutterwave Metadata Configuration Guide

## Problem

The webhook is receiving payments without `user_id` and `tier` metadata, causing 400 errors. However, your frontend verification endpoint works fine.

## Current Flow (Working)

```
1. User pays → Flutterwave processes
2. Webhook receives payment (no metadata) → Returns 200 but doesn't process
3. Frontend calls /credits/payment/verify-upgrade/ → Processes successfully ✓
```

## Solution Options

### Option 1: Add Metadata in Frontend (Recommended)

Update your frontend payment initialization to include metadata:

```javascript
// When user clicks "Upgrade to PRO"
const paymentData = {
  tx_ref: `tx-upg-${generateUniqueId()}`,
  amount: 20,
  currency: "USD",
  customer: {
    email: user.email,
    name: user.name
  },
  // IMPORTANT: Add metadata here
  meta: {
    user_id: user.id,           // User's UUID
    tier: "pro"                 // Target tier: "pro", "twin_plus", or "executive"
  },
  customizations: {
    title: "NeuroTwin Subscription",
    description: `Upgrade to ${tierName}`,
    logo: "https://your-domain.com/logo.png"
  }
};

// Initialize Flutterwave payment
FlutterwaveCheckout({
  public_key: process.env.NEXT_PUBLIC_FLUTTERWAVE_PUBLIC_KEY,
  ...paymentData,
  callback: function(response) {
    // Payment successful
    console.log("Payment response:", response);
    
    // Verify payment via your backend
    verifyPayment(response.transaction_id, tier);
  },
  onclose: function() {
    // Payment modal closed
  }
});
```

### Option 2: Configure in Flutterwave Dashboard

If you're using Flutterwave Payment Links:

1. **Go to Flutterwave Dashboard**
2. **Navigate to:** Settings > Payment Links
3. **Edit your payment link**
4. **Add Custom Fields:**
   - Field 1: `user_id` (required)
   - Field 2: `tier` (required)
5. **Save changes**

**Note:** This requires users to manually enter these values, which is not ideal.

### Option 3: Keep Current Hybrid Approach (Easiest)

Your current setup actually works! The webhook now:
- ✅ Accepts payments without metadata (returns 200)
- ✅ Creates pending transaction record
- ✅ Frontend verifies and completes the upgrade

**No changes needed** - the webhook fix I just made handles this gracefully.

## Recommended Implementation

### Frontend Payment Component

```typescript
// neuro-frontend/src/components/subscription/UpgradeButton.tsx
import { useAuth } from '@/hooks/useAuth';
import { useState } from 'react';

interface UpgradeButtonProps {
  tier: 'pro' | 'twin_plus' | 'executive';
  price: number;
}

export function UpgradeButton({ tier, price }: UpgradeButtonProps) {
  const { user } = useAuth();
  const [loading, setLoading] = useState(false);

  const handleUpgrade = () => {
    setLoading(true);

    const paymentData = {
      tx_ref: `tx-upg-${Date.now()}-${Math.random().toString(36).substr(2, 9)}`,
      amount: price,
      currency: "USD",
      customer: {
        email: user.email,
        name: `${user.first_name} ${user.last_name}`,
      },
      // CRITICAL: Include metadata for webhook
      meta: {
        user_id: user.id,
        tier: tier,
      },
      customizations: {
        title: "NeuroTwin Subscription",
        description: `Upgrade to ${tier.replace('_', ' ').toUpperCase()}`,
        logo: "https://your-domain.com/logo.png",
      },
    };

    // @ts-ignore - FlutterwaveCheckout is loaded via script
    FlutterwaveCheckout({
      public_key: process.env.NEXT_PUBLIC_FLUTTERWAVE_PUBLIC_KEY,
      ...paymentData,
      callback: async (response: any) => {
        console.log("Payment successful:", response);
        
        try {
          // Verify payment via backend
          const result = await fetch('/api/v1/credits/payment/verify-upgrade/', {
            method: 'POST',
            headers: {
              'Content-Type': 'application/json',
              'Authorization': `Bearer ${getAccessToken()}`,
            },
            body: JSON.stringify({
              transaction_id: response.transaction_id,
              tier: tier,
            }),
          });

          if (result.ok) {
            // Success! Redirect to dashboard
            window.location.href = '/dashboard';
          } else {
            alert('Payment verification failed. Please contact support.');
          }
        } catch (error) {
          console.error('Verification error:', error);
          alert('Payment verification failed. Please contact support.');
        } finally {
          setLoading(false);
        }
      },
      onclose: () => {
        setLoading(false);
      },
    });
  };

  return (
    <button
      onClick={handleUpgrade}
      disabled={loading}
      className="btn-primary"
    >
      {loading ? 'Processing...' : `Upgrade to ${tier.toUpperCase()} - $${price}`}
    </button>
  );
}
```

### Load Flutterwave Script

Add to your `_app.tsx` or layout:

```typescript
// neuro-frontend/src/app/layout.tsx
export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <head>
        {/* Flutterwave Inline Script */}
        <script src="https://checkout.flutterwave.com/v3.js"></script>
      </head>
      <body>{children}</body>
    </html>
  );
}
```

## Testing

### 1. Test with Metadata

```javascript
const testPayment = {
  tx_ref: "test-tx-123",
  amount: 20,
  currency: "USD",
  customer: {
    email: "test@example.com"
  },
  meta: {
    user_id: "e48cdce0-e173-405a-ad07-13d4d5363a3d",
    tier: "pro"
  }
};
```

**Expected Result:**
- Webhook receives metadata ✓
- Subscription upgraded automatically ✓
- Credits allocated ✓

### 2. Test without Metadata (Current Behavior)

```javascript
const testPayment = {
  tx_ref: "test-tx-456",
  amount: 20,
  currency: "USD",
  customer: {
    email: "test@example.com"
  }
  // No meta field
};
```

**Expected Result:**
- Webhook returns 200 (no error) ✓
- Frontend verifies payment ✓
- Subscription upgraded ✓
- Credits allocated ✓

## Webhook Behavior After Fix

### With Metadata (Ideal)
```
POST /api/v1/subscription/webhook/flutterwave
{
  "data": {
    "tx_ref": "tx-123",
    "amount": 20,
    "currency": "USD",
    "status": "successful",
    "meta": {
      "user_id": "uuid-here",
      "tier": "pro"
    }
  }
}

Response: 200 OK
{
  "status": "success",
  "message": "Subscription activated",
  "subscription_id": "uuid"
}
```

### Without Metadata (Fallback)
```
POST /api/v1/subscription/webhook/flutterwave
{
  "data": {
    "tx_ref": "tx-123",
    "amount": 20,
    "currency": "USD",
    "status": "successful"
    // No meta field
  }
}

Response: 200 OK
{
  "status": "success",
  "message": "Payment received, awaiting frontend verification",
  "tx_ref": "tx-123"
}
```

## Summary

✅ **Webhook fixed** - Now handles both cases gracefully
✅ **No more 400 errors** - Returns 200 even without metadata
✅ **Dual verification** - Webhook OR frontend can process payment
✅ **Backward compatible** - Works with your current frontend

**Recommended Action:**
Add metadata to frontend payment initialization for automatic processing, but keep the frontend verification as a fallback.
