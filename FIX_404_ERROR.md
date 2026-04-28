# Fix for 404 Error - Payment Endpoint Not Found

## The Problem

The browser is trying to call `/api/v1/subscription/payment/initiate/` but the correct endpoint is `/api/v1/credits/payment/initiate/`.

This is happening because:
1. The browser has cached the old JavaScript bundle
2. Next.js dev server hasn't rebuilt the updated files

## The Solution

### Step 1: Clear Browser Cache & Rebuild

```bash
# Stop the Next.js dev server (Ctrl+C)

# Clear Next.js cache
cd neuro-frontend
rm -rf .next

# Reinstall dependencies (optional but recommended)
npm install

# Restart dev server
npm run dev
```

### Step 2: Hard Refresh Browser

After restarting the dev server:
1. Open the page in your browser
2. Press `Ctrl + Shift + R` (Windows/Linux) or `Cmd + Shift + R` (Mac)
3. Or open DevTools (F12) → Right-click refresh button → "Empty Cache and Hard Reload"

### Step 3: Verify the Fix

1. Open browser DevTools (F12)
2. Go to Network tab
3. Click "Proceed to Payment" button
4. Check the request URL - it should now be:
   ```
   POST http://localhost:8000/api/v1/credits/payment/initiate/
   ```

## Alternative: Force Rebuild

If the above doesn't work:

```bash
# Kill all Node processes
taskkill /F /IM node.exe  # Windows
# or
pkill -9 node  # Linux/Mac

# Delete node_modules and reinstall
cd neuro-frontend
rm -rf node_modules .next
npm install
npm run dev
```

## Verify Backend is Running

Make sure your Django server is running:

```bash
# In the project root
uv run python manage.py runserver
```

You should see:
```
Starting development server at http://127.0.0.1:8000/
```

## Test the Endpoint Directly

You can test if the backend endpoint works:

```bash
# Get a JWT token first (from browser DevTools → Application → Local Storage)
# Then test the endpoint:

curl -X POST http://localhost:8000/api/v1/credits/payment/initiate/ \
  -H "Authorization: Bearer YOUR_JWT_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"tier": "pro"}'
```

Expected response:
```json
{
  "tx_ref": "tx-upg-...",
  "amount": 20,
  "currency": "USD",
  "public_key": "FLWPUBK_TEST-...",
  "customer_email": "user@example.com",
  "customer_name": "User Name"
}
```

## If Still Getting 404

Check Django URL routing:

```bash
# Run this to see all available URLs
uv run python manage.py show_urls | grep payment
```

You should see:
```
/api/v1/credits/payment/initiate/
/api/v1/credits/payment/verify-upgrade/
/api/v1/credits/payment/initiate-topup/
/api/v1/credits/payment/verify-topup/
```

If these URLs are missing, the issue is in the backend routing.
