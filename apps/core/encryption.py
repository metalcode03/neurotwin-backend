"""
Encryption utility for secure storage of API keys and secrets.

Uses Fernet symmetric encryption.
The encryption key must be stored in the ENCRYPTION_KEY environment variable.

Requirements: 22.1, 22.2
"""

import os
import logging
from cryptography.fernet import Fernet, InvalidToken

logger = logging.getLogger(__name__)


def _get_fernet() -> Fernet:
    """
    Build a Fernet cipher from the ENCRYPTION_KEY env-var.

    Raises EnvironmentError if the key is missing or malformed.
    """
    key = os.environ.get('ENCRYPTION_KEY')
    if not key:
        raise EnvironmentError(
            "ENCRYPTION_KEY environment variable is not set. "
            "Generate one with: python -c \"from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())\""
        )
    try:
        return Fernet(key.encode() if isinstance(key, str) else key)
    except Exception as exc:
        raise EnvironmentError(f"Invalid ENCRYPTION_KEY: {exc}") from exc


def encrypt(plaintext: str) -> str:
    """
    Encrypt a plaintext string and return the ciphertext as a UTF-8 string.

    Usage:
        encrypted = encrypt(cerebras_api_key)
        # Store `encrypted` in the database
    """
    if not plaintext:
        raise ValueError("Cannot encrypt an empty string")
    fernet = _get_fernet()
    return fernet.encrypt(plaintext.encode()).decode()


def decrypt(ciphertext: str) -> str:
    """
    Decrypt a ciphertext string and return the original plaintext.

    Usage:
        api_key = decrypt(row.encrypted_api_key)
    """
    if not ciphertext:
        raise ValueError("Cannot decrypt an empty string")
    fernet = _get_fernet()
    try:
        return fernet.decrypt(ciphertext.encode()).decode()
    except InvalidToken:
        logger.error("Failed to decrypt value – invalid token or corrupted ciphertext")
        raise ValueError("Decryption failed: invalid token or wrong encryption key")
