"""
Token encryption utilities for all authentication types.

Uses Fernet symmetric encryption for secure token storage with separate
encryption keys for OAuth, Meta, and API Key credentials.

Requirements: 17.1-17.4
"""

import os
import base64
from typing import Optional, Literal

from django.conf import settings
from cryptography.fernet import Fernet, InvalidToken


AuthType = Literal['oauth', 'meta', 'api_key']


class TokenEncryption:
    """
    Utility class for encrypting and decrypting authentication credentials.
    
    Uses Fernet symmetric encryption for secure credential storage.
    Supports separate encryption keys for different auth types (OAuth, Meta, API Key).
    
    Requirements: 17.1-17.4
    - Encrypt credentials using Fernet symmetric encryption (17.1)
    - Use separate encryption keys for oauth, meta, api_key from environment (17.3, 17.4)
    - Store keys in environment variables (17.3)
    - Support encrypt() and decrypt() methods with auth_type parameter (17.1)
    """
    
    _fernet_cache: dict[str, Optional[Fernet]] = {}
    
    @classmethod
    def _get_encryption_key(cls, auth_type: AuthType = 'oauth') -> bytes:
        """
        Retrieve encryption key from environment variables for specific auth type.
        
        Args:
            auth_type: Authentication type ('oauth', 'meta', 'api_key')
        
        Returns:
            bytes: Encryption key in correct format for Fernet
            
        Raises:
            ValueError: If encryption key is not configured
            
        Requirements: 17.3, 17.4
        """
        # Map auth type to environment variable name
        env_var_map = {
            'oauth': 'OAUTH_ENCRYPTION_KEY',
            'meta': 'META_ENCRYPTION_KEY',
            'api_key': 'API_KEY_ENCRYPTION_KEY'
        }
        
        env_var_name = env_var_map.get(auth_type, 'ENCRYPTION_KEY')
        
        # Get encryption key from environment variable
        key = os.environ.get(env_var_name)
        
        # Fallback to generic ENCRYPTION_KEY if specific key not found
        if key is None:
            key = os.environ.get('ENCRYPTION_KEY')
        
        # Fallback to settings if not in environment
        if key is None:
            key = getattr(settings, env_var_name, None)
            if key is None:
                key = getattr(settings, 'ENCRYPTION_KEY', None)
        
        if key is None:
            raise ValueError(
                f'{env_var_name} environment variable is not set. '
                f'Please configure it in your .env file. '
                f'Alternatively, set ENCRYPTION_KEY as a fallback.'
            )
        
        # Ensure key is in correct format (bytes)
        if isinstance(key, str):
            # If key is 44 characters (base64 encoded), use as-is
            if len(key) == 44:
                return key.encode()
            else:
                # Otherwise, pad and encode
                return base64.urlsafe_b64encode(key.ljust(32)[:32].encode())
        
        return key
    
    @classmethod
    def _get_fernet(cls, auth_type: AuthType = 'oauth') -> Fernet:
        """
        Get or create Fernet instance with encryption key for specific auth type.
        
        Args:
            auth_type: Authentication type ('oauth', 'meta', 'api_key')
        
        Returns:
            Fernet: Configured Fernet instance for encryption/decryption
            
        Raises:
            ValueError: If encryption key is not configured
            
        Requirements: 16.2, 16.3, 17.1-17.4
        """
        if auth_type not in cls._fernet_cache:
            try:
                key = cls._get_encryption_key(auth_type)
                cls._fernet_cache[auth_type] = Fernet(key)
            except Exception as e:
                raise ValueError(
                    f'Invalid encryption key for {auth_type}: {str(e)}. '
                    'Key must be a valid Fernet key (32 url-safe base64-encoded bytes).'
                )
        
        return cls._fernet_cache[auth_type]
    
    @classmethod
    def encrypt(cls, plaintext: str, auth_type: AuthType = 'oauth') -> bytes:
        """
        Encrypt a plaintext string using auth-type-specific key.
        
        Args:
            plaintext: The string to encrypt
            auth_type: Authentication type ('oauth', 'meta', 'api_key')
            
        Returns:
            bytes: Encrypted ciphertext
            
        Raises:
            ValueError: If encryption key is not configured
            
        Requirements: 17.1
        """
        if not plaintext:
            return b''
        
        try:
            fernet = cls._get_fernet(auth_type)
            return fernet.encrypt(plaintext.encode())
        except Exception as e:
            raise ValueError(f'Encryption failed: {str(e)}')
    
    @classmethod
    def decrypt(cls, ciphertext: bytes, auth_type: AuthType = 'oauth') -> str:
        """
        Decrypt ciphertext to plaintext string using auth-type-specific key.
        
        Args:
            ciphertext: The encrypted bytes to decrypt
            auth_type: Authentication type ('oauth', 'meta', 'api_key')
            
        Returns:
            str: Decrypted plaintext string
            
        Raises:
            ValueError: If encryption key is not configured or decryption fails
            
        Requirements: 17.1
        """
        if not ciphertext:
            return ''
        
        try:
            fernet = cls._get_fernet(auth_type)
            return fernet.decrypt(ciphertext).decode()
        except InvalidToken:
            raise ValueError(
                'Decryption failed: Invalid token or wrong encryption key'
            )
        except Exception as e:
            raise ValueError(f'Decryption failed: {str(e)}')
    
    @classmethod
    def reset(cls, auth_type: Optional[AuthType] = None):
        """
        Reset the cached Fernet instance(s).
        
        Args:
            auth_type: Specific auth type to reset, or None to reset all
        
        Useful for testing or when the encryption key changes.
        """
        if auth_type:
            cls._fernet_cache.pop(auth_type, None)
        else:
            cls._fernet_cache.clear()
