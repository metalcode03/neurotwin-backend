"""
Token encryption utilities for OAuth tokens.

Uses Fernet symmetric encryption for secure token storage.
Requirements: 2.2, 4.7, 18.1
"""

import os
import base64
from typing import Optional

from django.conf import settings
from cryptography.fernet import Fernet, InvalidToken


class TokenEncryption:
    """
    Utility class for encrypting and decrypting OAuth tokens.
    
    Uses Fernet symmetric encryption for secure token storage.
    The encryption key is loaded from the ENCRYPTION_KEY environment variable.
    
    Requirements: 2.2, 4.7, 18.1
    - Encrypt OAuth client secrets using Fernet symmetric encryption
    - Load encryption key from environment variable
    - Add error handling for invalid keys
    """
    
    _fernet: Optional[Fernet] = None
    
    @classmethod
    def _get_fernet(cls) -> Fernet:
        """
        Get or create Fernet instance with encryption key.
        
        Returns:
            Fernet: Configured Fernet instance for encryption/decryption
            
        Raises:
            ValueError: If encryption key is not configured
        """
        if cls._fernet is None:
            # Get encryption key from environment variable
            key = os.environ.get('ENCRYPTION_KEY')
            
            # Fallback to settings if not in environment
            if key is None:
                key = getattr(settings, 'ENCRYPTION_KEY', None)
            
            if key is None:
                raise ValueError(
                    'ENCRYPTION_KEY environment variable is not set. '
                    'Please configure it in your .env file.'
                )
            
            # Ensure key is in correct format (bytes)
            if isinstance(key, str):
                # If key is 44 characters (base64 encoded), use as-is
                if len(key) == 44:
                    key = key.encode()
                else:
                    # Otherwise, pad and encode
                    key = base64.urlsafe_b64encode(key.ljust(32)[:32].encode())
            
            try:
                cls._fernet = Fernet(key)
            except Exception as e:
                raise ValueError(
                    f'Invalid ENCRYPTION_KEY format: {str(e)}. '
                    'Key must be a valid Fernet key (32 url-safe base64-encoded bytes).'
                )
        
        return cls._fernet
    
    @classmethod
    def encrypt(cls, plaintext: str) -> bytes:
        """
        Encrypt a plaintext string.
        
        Args:
            plaintext: The string to encrypt
            
        Returns:
            bytes: Encrypted ciphertext
            
        Raises:
            ValueError: If encryption key is not configured
        """
        if not plaintext:
            return b''
        
        try:
            fernet = cls._get_fernet()
            return fernet.encrypt(plaintext.encode())
        except Exception as e:
            raise ValueError(f'Encryption failed: {str(e)}')
    
    @classmethod
    def decrypt(cls, ciphertext: bytes) -> str:
        """
        Decrypt ciphertext to plaintext string.
        
        Args:
            ciphertext: The encrypted bytes to decrypt
            
        Returns:
            str: Decrypted plaintext string
            
        Raises:
            ValueError: If encryption key is not configured or decryption fails
        """
        if not ciphertext:
            return ''
        
        try:
            fernet = cls._get_fernet()
            return fernet.decrypt(ciphertext).decode()
        except InvalidToken:
            raise ValueError(
                'Decryption failed: Invalid token or wrong encryption key'
            )
        except Exception as e:
            raise ValueError(f'Decryption failed: {str(e)}')
    
    @classmethod
    def reset(cls):
        """
        Reset the cached Fernet instance.
        
        Useful for testing or when the encryption key changes.
        """
        cls._fernet = None
