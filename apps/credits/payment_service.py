import logging
import requests
from django.conf import settings
from .exceptions import PaymentVerificationError

logger = logging.getLogger(__name__)

class FlutterwaveService:
    """
    Service to interact with Flutterwave API for payment verification.
    """
    BASE_URL = "https://api.flutterwave.com/v3"

    @classmethod
    def verify_transaction(cls, transaction_id: str) -> dict:
        """
        Verifies a transaction with Flutterwave using the given transaction ID.
        
        Args:
            transaction_id: The Flutterwave transaction ID to verify.
            
        Returns:
            dict: The verified transaction data (amount, currency, status, customer).
            
        Raises:
            PaymentVerificationError: If verification fails or the gateway is unconfigured.
        """
        secret_key = settings.FLUTTERWAVE_SECRET_KEY
        if not secret_key:
            logger.error("FLUTTERWAVE_SECRET_KEY is not configured.")
            raise PaymentVerificationError("Payment gateway not configured")

        url = f"{cls.BASE_URL}/transactions/{transaction_id}/verify"
        headers = {
            "Authorization": f"Bearer {secret_key}",
            "Content-Type": "application/json"
        }

        try:
            response = requests.get(url, headers=headers)
            response.raise_for_status()
            data = response.json()
            
            if data.get("status") == "success":
                return data.get("data")
            else:
                logger.error(f"Flutterwave verification failed: {data}")
                raise PaymentVerificationError("Payment verification failed", provider_error=data.get('message'))
                
        except requests.exceptions.RequestException as e:
            logger.error(f"Error communicating with Flutterwave: {str(e)}")
            raise PaymentVerificationError("Error communicating with payment provider", provider_error=str(e))
