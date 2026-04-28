"""
Test script for Flutterwave payment endpoints
Run this after starting the Django server to verify endpoints are working
"""

import requests
import json

BASE_URL = "http://localhost:8000/api/v1"

# You'll need to replace this with a valid JWT token from your auth flow
# Get it by logging in through the frontend or using the auth API
AUTH_TOKEN = "YOUR_JWT_TOKEN_HERE"

headers = {
    "Authorization": f"Bearer {AUTH_TOKEN}",
    "Content-Type": "application/json"
}

def test_payment_initiation():
    """Test payment initiation endpoint"""
    print("\n" + "="*60)
    print("Testing Payment Initiation")
    print("="*60)
    
    url = f"{BASE_URL}/credits/payment/initiate/"
    data = {"tier": "pro"}
    
    print(f"\nPOST {url}")
    print(f"Data: {json.dumps(data, indent=2)}")
    
    try:
        response = requests.post(url, json=data, headers=headers)
        print(f"\nStatus Code: {response.status_code}")
        print(f"Response: {json.dumps(response.json(), indent=2)}")
        
        if response.status_code == 200:
            print("\n✅ Payment initiation successful!")
            response_data = response.json()
            
            # Verify required fields
            required_fields = ['tx_ref', 'amount', 'currency', 'public_key', 'customer_email', 'customer_name']
            missing_fields = [field for field in required_fields if field not in response_data]
            
            if missing_fields:
                print(f"\n⚠️  Warning: Missing fields: {missing_fields}")
            else:
                print("\n✅ All required fields present")
                return response_data['tx_ref']
        else:
            print(f"\n❌ Payment initiation failed: {response.json()}")
            
    except requests.exceptions.RequestException as e:
        print(f"\n❌ Request failed: {str(e)}")
    except json.JSONDecodeError:
        print(f"\n❌ Invalid JSON response: {response.text}")
    
    return None

def test_payment_verification(transaction_id="test_transaction_id"):
    """Test payment verification endpoint"""
    print("\n" + "="*60)
    print("Testing Payment Verification")
    print("="*60)
    
    url = f"{BASE_URL}/credits/payment/verify-upgrade/"
    data = {
        "transaction_id": transaction_id,
        "tier": "pro"
    }
    
    print(f"\nPOST {url}")
    print(f"Data: {json.dumps(data, indent=2)}")
    print("\nNote: This will fail without a real Flutterwave transaction")
    
    try:
        response = requests.post(url, json=data, headers=headers)
        print(f"\nStatus Code: {response.status_code}")
        print(f"Response: {json.dumps(response.json(), indent=2)}")
        
        if response.status_code == 200:
            print("\n✅ Payment verification successful!")
        else:
            print(f"\n⚠️  Expected failure (no real transaction): {response.json()}")
            
    except requests.exceptions.RequestException as e:
        print(f"\n❌ Request failed: {str(e)}")
    except json.JSONDecodeError:
        print(f"\n❌ Invalid JSON response: {response.text}")

def test_topup_initiation():
    """Test credit top-up initiation endpoint"""
    print("\n" + "="*60)
    print("Testing Top-up Initiation")
    print("="*60)
    
    url = f"{BASE_URL}/credits/payment/initiate-topup/"
    data = {"topup_package": "small"}
    
    print(f"\nPOST {url}")
    print(f"Data: {json.dumps(data, indent=2)}")
    
    try:
        response = requests.post(url, json=data, headers=headers)
        print(f"\nStatus Code: {response.status_code}")
        print(f"Response: {json.dumps(response.json(), indent=2)}")
        
        if response.status_code == 200:
            print("\n✅ Top-up initiation successful!")
        else:
            print(f"\n❌ Top-up initiation failed: {response.json()}")
            
    except requests.exceptions.RequestException as e:
        print(f"\n❌ Request failed: {str(e)}")
    except json.JSONDecodeError:
        print(f"\n❌ Invalid JSON response: {response.text}")

if __name__ == "__main__":
    print("\n" + "="*60)
    print("Flutterwave Payment Endpoints Test")
    print("="*60)
    
    if AUTH_TOKEN == "YOUR_JWT_TOKEN_HERE":
        print("\n❌ Error: Please set a valid AUTH_TOKEN in the script")
        print("\nTo get a token:")
        print("1. Log in through the frontend")
        print("2. Open browser DevTools > Application > Local Storage")
        print("3. Copy the 'access_token' value")
        print("4. Replace AUTH_TOKEN in this script")
        exit(1)
    
    # Test payment initiation
    tx_ref = test_payment_initiation()
    
    # Test payment verification (will fail without real transaction)
    if tx_ref:
        test_payment_verification(tx_ref)
    
    # Test top-up initiation
    test_topup_initiation()
    
    print("\n" + "="*60)
    print("Tests Complete")
    print("="*60)
    print("\nNext steps:")
    print("1. If initiation works, test the full flow in the frontend")
    print("2. Click 'Upgrade' button in Settings page")
    print("3. Complete payment with Flutterwave test card")
    print("4. Verify subscription and credits are updated")
    print("\nFlutterwave Test Card:")
    print("  Card: 5531886652142950")
    print("  CVV: 564")
    print("  Expiry: 09/32")
    print("  PIN: 3310")
    print("  OTP: 12345")
    print("="*60 + "\n")
