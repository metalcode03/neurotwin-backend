"""
Authentication configuration parser with validation.

Provides dataclasses and parsing functions for OAuth, Meta, and API Key configurations.
Validates configuration structure and field formats.

Requirements: 21.1-21.5, 21.8
"""

import re
from dataclasses import dataclass, field
from typing import List, Optional, Dict, Any
from urllib.parse import urlparse

from django.core.exceptions import ValidationError


@dataclass
class OAuthConfig:
    """
    OAuth 2.0 configuration dataclass.
    
    Requirements: 21.1
    """
    client_id: str
    client_secret_encrypted: str
    authorization_url: str
    token_url: str
    scopes: List[str]
    revoke_url: Optional[str] = None
    
    def __post_init__(self):
        """Validate OAuth configuration after initialization."""
        if not self.client_id:
            raise ValidationError("client_id is required")
        if not self.client_secret_encrypted:
            raise ValidationError("client_secret_encrypted is required")
        if not self.authorization_url:
            raise ValidationError("authorization_url is required")
        if not self.token_url:
            raise ValidationError("token_url is required")
        if not self.scopes:
            raise ValidationError("scopes list cannot be empty")


@dataclass
class MetaConfig:
    """
    Meta Business authentication configuration dataclass.
    
    Requirements: 21.1
    """
    app_id: str
    app_secret_encrypted: str
    config_id: str
    business_verification_url: str
    
    def __post_init__(self):
        """Validate Meta configuration after initialization."""
        if not self.app_id:
            raise ValidationError("app_id is required")
        if not self.app_secret_encrypted:
            raise ValidationError("app_secret_encrypted is required")
        if not self.config_id:
            raise ValidationError("config_id is required")
        if not self.business_verification_url:
            raise ValidationError("business_verification_url is required")


@dataclass
class APIKeyConfig:
    """
    API Key authentication configuration dataclass.
    
    Requirements: 21.1
    """
    api_endpoint: str
    authentication_header_name: str = 'Authorization'
    api_key_format_hint: Optional[str] = None
    header_format: str = 'Bearer {key}'
    
    def __post_init__(self):
        """Validate API Key configuration after initialization."""
        if not self.api_endpoint:
            raise ValidationError("api_endpoint is required")
        if not self.authentication_header_name:
            raise ValidationError("authentication_header_name is required")


class AuthConfigParser:
    """
    Parser for authentication configurations.
    
    Parses and validates auth_config JSON into typed dataclass objects.
    Provides descriptive error messages for invalid configurations.
    
    Requirements: 21.1-21.5, 21.8
    """
    
    @staticmethod
    def _validate_url(url: str, field_name: str) -> None:
        """
        Validate URL format.
        
        Args:
            url: URL to validate
            field_name: Field name for error messages
            
        Raises:
            ValidationError: If URL format is invalid
            
        Requirements: 21.5
        """
        if not url:
            raise ValidationError(f"{field_name} cannot be empty")
        
        try:
            parsed = urlparse(url)
            
            # Must have scheme and netloc
            if not parsed.scheme:
                raise ValidationError(
                    f"{field_name} must include protocol (http:// or https://)"
                )
            
            if not parsed.netloc:
                raise ValidationError(
                    f"{field_name} must include domain name"
                )
            
            # Validate scheme
            if parsed.scheme not in ('http', 'https'):
                raise ValidationError(
                    f"{field_name} must use http or https protocol"
                )
            
        except Exception as e:
            if isinstance(e, ValidationError):
                raise
            raise ValidationError(
                f"{field_name} has invalid URL format: {str(e)}"
            )
    
    @staticmethod
    def _validate_https_url(url: str, field_name: str, allow_http_localhost: bool = True) -> None:
        """
        Validate that URL uses HTTPS (or HTTP for localhost in dev).
        
        Args:
            url: URL to validate
            field_name: Field name for error messages
            allow_http_localhost: Allow HTTP for localhost/127.0.0.1
            
        Raises:
            ValidationError: If URL doesn't use HTTPS
            
        Requirements: 21.5
        """
        AuthConfigParser._validate_url(url, field_name)
        
        parsed = urlparse(url)
        
        # Allow HTTP for localhost in development
        if allow_http_localhost and parsed.scheme == 'http':
            if parsed.netloc.startswith('localhost') or parsed.netloc.startswith('127.0.0.1'):
                return
        
        # Otherwise require HTTPS
        if parsed.scheme != 'https':
            raise ValidationError(
                f"{field_name} must use HTTPS protocol for security. "
                f"HTTP is only allowed for localhost in development."
            )
    
    @classmethod
    def parse_oauth_config(cls, config_dict: Dict[str, Any]) -> OAuthConfig:
        """
        Parse OAuth configuration from dictionary.
        
        Args:
            config_dict: Configuration dictionary from auth_config field
            
        Returns:
            OAuthConfig: Validated OAuth configuration
            
        Raises:
            ValidationError: If configuration is invalid
            
        Requirements: 21.2, 21.5, 21.8
        """
        try:
            # Extract required fields
            client_id = config_dict.get('client_id', '')
            client_secret_encrypted = config_dict.get('client_secret_encrypted', '')
            authorization_url = config_dict.get('authorization_url', '')
            token_url = config_dict.get('token_url', '')
            scopes = config_dict.get('scopes', [])
            revoke_url = config_dict.get('revoke_url')
            
            # Validate URLs
            if authorization_url:
                cls._validate_https_url(authorization_url, 'authorization_url')
            
            if token_url:
                cls._validate_https_url(token_url, 'token_url')
            
            if revoke_url:
                cls._validate_https_url(revoke_url, 'revoke_url')
            
            # Handle scopes as string or list
            if isinstance(scopes, str):
                scopes = [s.strip() for s in scopes.split(',') if s.strip()]
            elif not isinstance(scopes, list):
                raise ValidationError(
                    "scopes must be a list of strings or comma-separated string"
                )
            
            # Create and validate config
            return OAuthConfig(
                client_id=client_id,
                client_secret_encrypted=client_secret_encrypted,
                authorization_url=authorization_url,
                token_url=token_url,
                scopes=scopes,
                revoke_url=revoke_url
            )
            
        except ValidationError:
            raise
        except Exception as e:
            raise ValidationError(
                f"Failed to parse OAuth configuration: {str(e)}"
            )
    
    @classmethod
    def parse_meta_config(cls, config_dict: Dict[str, Any]) -> MetaConfig:
        """
        Parse Meta configuration from dictionary.
        
        Args:
            config_dict: Configuration dictionary from auth_config field
            
        Returns:
            MetaConfig: Validated Meta configuration
            
        Raises:
            ValidationError: If configuration is invalid
            
        Requirements: 21.3, 21.5, 21.8
        """
        try:
            # Extract required fields
            app_id = config_dict.get('app_id', '')
            app_secret_encrypted = config_dict.get('app_secret_encrypted', '')
            config_id = config_dict.get('config_id', '')
            business_verification_url = config_dict.get('business_verification_url', '')
            
            # Validate URL
            if business_verification_url:
                cls._validate_https_url(business_verification_url, 'business_verification_url')
            
            # Create and validate config
            return MetaConfig(
                app_id=app_id,
                app_secret_encrypted=app_secret_encrypted,
                config_id=config_id,
                business_verification_url=business_verification_url
            )
            
        except ValidationError:
            raise
        except Exception as e:
            raise ValidationError(
                f"Failed to parse Meta configuration: {str(e)}"
            )
    
    @classmethod
    def parse_api_key_config(cls, config_dict: Dict[str, Any]) -> APIKeyConfig:
        """
        Parse API Key configuration from dictionary.
        
        Args:
            config_dict: Configuration dictionary from auth_config field
            
        Returns:
            APIKeyConfig: Validated API Key configuration
            
        Raises:
            ValidationError: If configuration is invalid
            
        Requirements: 21.4, 21.5, 21.8
        """
        try:
            # Extract required fields
            api_endpoint = config_dict.get('api_endpoint', '')
            authentication_header_name = config_dict.get(
                'authentication_header_name',
                'Authorization'
            )
            api_key_format_hint = config_dict.get('api_key_format_hint')
            header_format = config_dict.get('header_format', 'Bearer {key}')
            
            # Validate URL
            if api_endpoint:
                cls._validate_https_url(api_endpoint, 'api_endpoint')
            
            # Validate header format contains {key} placeholder
            if '{key}' not in header_format:
                raise ValidationError(
                    "header_format must contain {key} placeholder"
                )
            
            # Create and validate config
            return APIKeyConfig(
                api_endpoint=api_endpoint,
                authentication_header_name=authentication_header_name,
                api_key_format_hint=api_key_format_hint,
                header_format=header_format
            )
            
        except ValidationError:
            raise
        except Exception as e:
            raise ValidationError(
                f"Failed to parse API Key configuration: {str(e)}"
            )
    
    @classmethod
    def parse_config(
        cls,
        config_dict: Dict[str, Any],
        auth_type: str
    ) -> OAuthConfig | MetaConfig | APIKeyConfig:
        """
        Parse configuration based on auth type.
        
        Args:
            config_dict: Configuration dictionary
            auth_type: Authentication type ('oauth', 'meta', 'api_key')
            
        Returns:
            Parsed configuration object
            
        Raises:
            ValidationError: If auth_type is invalid or configuration is invalid
        """
        if auth_type == 'oauth':
            return cls.parse_oauth_config(config_dict)
        elif auth_type == 'meta':
            return cls.parse_meta_config(config_dict)
        elif auth_type == 'api_key':
            return cls.parse_api_key_config(config_dict)
        else:
            raise ValidationError(
                f"Unsupported auth_type: {auth_type}. "
                f"Supported types: oauth, meta, api_key"
            )
    
    @staticmethod
    def serialize_oauth_config(config: OAuthConfig) -> Dict[str, Any]:
        """
        Serialize OAuth configuration to dictionary.
        
        Args:
            config: OAuthConfig instance
            
        Returns:
            Dictionary representation of the configuration
            
        Requirements: 25.6
        """
        result = {
            'client_id': config.client_id,
            'client_secret_encrypted': config.client_secret_encrypted,
            'authorization_url': config.authorization_url,
            'token_url': config.token_url,
            'scopes': config.scopes
        }
        
        if config.revoke_url:
            result['revoke_url'] = config.revoke_url
        
        return result
    
    @staticmethod
    def serialize_meta_config(config: MetaConfig) -> Dict[str, Any]:
        """
        Serialize Meta configuration to dictionary.
        
        Args:
            config: MetaConfig instance
            
        Returns:
            Dictionary representation of the configuration
            
        Requirements: 25.6
        """
        return {
            'app_id': config.app_id,
            'app_secret_encrypted': config.app_secret_encrypted,
            'config_id': config.config_id,
            'business_verification_url': config.business_verification_url
        }
    
    @staticmethod
    def serialize_api_key_config(config: APIKeyConfig) -> Dict[str, Any]:
        """
        Serialize API Key configuration to dictionary.
        
        Args:
            config: APIKeyConfig instance
            
        Returns:
            Dictionary representation of the configuration
            
        Requirements: 25.6
        """
        result = {
            'api_endpoint': config.api_endpoint,
            'authentication_header_name': config.authentication_header_name,
            'header_format': config.header_format
        }
        
        if config.api_key_format_hint:
            result['api_key_format_hint'] = config.api_key_format_hint
        
        return result
    
    @classmethod
    def serialize_config(
        cls,
        config: OAuthConfig | MetaConfig | APIKeyConfig
    ) -> Dict[str, Any]:
        """
        Serialize configuration object to dictionary.
        
        Args:
            config: Configuration object (OAuthConfig, MetaConfig, or APIKeyConfig)
            
        Returns:
            Dictionary representation of the configuration
            
        Raises:
            ValidationError: If config type is not recognized
            
        Requirements: 25.6
        """
        if isinstance(config, OAuthConfig):
            return cls.serialize_oauth_config(config)
        elif isinstance(config, MetaConfig):
            return cls.serialize_meta_config(config)
        elif isinstance(config, APIKeyConfig):
            return cls.serialize_api_key_config(config)
        else:
            raise ValidationError(
                f"Unsupported config type: {type(config).__name__}"
            )
