"""
Authentication configuration serializer.

Converts dataclass configuration objects back to dictionary format for storage.
Ensures round-trip property: parse -> serialize -> parse produces equivalent config.

Requirements: 21.6, 21.7
"""

from typing import Dict, Any

from .auth_config_parser import OAuthConfig, MetaConfig, APIKeyConfig


class AuthConfigSerializer:
    """
    Serializer for authentication configurations.
    
    Converts typed configuration dataclasses back to dictionary format
    for storage in the database auth_config JSON field.
    
    Requirements: 21.6, 21.7
    """
    
    @staticmethod
    def serialize_oauth_config(config: OAuthConfig) -> Dict[str, Any]:
        """
        Serialize OAuth configuration to dictionary.
        
        Args:
            config: OAuthConfig dataclass instance
            
        Returns:
            Dictionary representation of OAuth configuration
            
        Requirements: 21.6
        """
        result = {
            'client_id': config.client_id,
            'client_secret_encrypted': config.client_secret_encrypted,
            'authorization_url': config.authorization_url,
            'token_url': config.token_url,
            'scopes': config.scopes
        }
        
        # Include optional fields if present
        if config.revoke_url:
            result['revoke_url'] = config.revoke_url
        
        return result
    
    @staticmethod
    def serialize_meta_config(config: MetaConfig) -> Dict[str, Any]:
        """
        Serialize Meta configuration to dictionary.
        
        Args:
            config: MetaConfig dataclass instance
            
        Returns:
            Dictionary representation of Meta configuration
            
        Requirements: 21.6
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
            config: APIKeyConfig dataclass instance
            
        Returns:
            Dictionary representation of API Key configuration
            
        Requirements: 21.6
        """
        result = {
            'api_endpoint': config.api_endpoint,
            'authentication_header_name': config.authentication_header_name,
            'header_format': config.header_format
        }
        
        # Include optional fields if present
        if config.api_key_format_hint:
            result['api_key_format_hint'] = config.api_key_format_hint
        
        return result
    
    @staticmethod
    def serialize_config(
        config: OAuthConfig | MetaConfig | APIKeyConfig
    ) -> Dict[str, Any]:
        """
        Serialize configuration based on type.
        
        Args:
            config: Configuration dataclass instance
            
        Returns:
            Dictionary representation of configuration
            
        Raises:
            ValueError: If config type is not recognized
            
        Requirements: 21.6, 21.7
        """
        if isinstance(config, OAuthConfig):
            return AuthConfigSerializer.serialize_oauth_config(config)
        elif isinstance(config, MetaConfig):
            return AuthConfigSerializer.serialize_meta_config(config)
        elif isinstance(config, APIKeyConfig):
            return AuthConfigSerializer.serialize_api_key_config(config)
        else:
            raise ValueError(
                f"Unsupported config type: {type(config).__name__}"
            )


def verify_round_trip(config_dict: Dict[str, Any], auth_type: str) -> bool:
    """
    Verify round-trip property: parse -> serialize -> parse produces equivalent config.
    
    This function is useful for testing and validation.
    
    Args:
        config_dict: Original configuration dictionary
        auth_type: Authentication type ('oauth', 'meta', 'api_key')
        
    Returns:
        True if round-trip produces equivalent configuration
        
    Raises:
        AssertionError: If round-trip fails
        
    Requirements: 21.7
    """
    from .auth_config_parser import AuthConfigParser
    
    # Parse original
    parsed1 = AuthConfigParser.parse_config(config_dict, auth_type)
    
    # Serialize
    serialized = AuthConfigSerializer.serialize_config(parsed1)
    
    # Parse again
    parsed2 = AuthConfigParser.parse_config(serialized, auth_type)
    
    # Compare - should be equivalent
    # Note: We compare the serialized forms since dataclass equality
    # checks all fields including optional ones
    serialized2 = AuthConfigSerializer.serialize_config(parsed2)
    
    # Normalize for comparison (handle list ordering, etc.)
    def normalize(d):
        """Normalize dictionary for comparison."""
        result = {}
        for key, value in d.items():
            if isinstance(value, list):
                result[key] = sorted(value) if value else []
            else:
                result[key] = value
        return result
    
    normalized1 = normalize(serialized)
    normalized2 = normalize(serialized2)
    
    if normalized1 != normalized2:
        raise AssertionError(
            f"Round-trip failed: {normalized1} != {normalized2}"
        )
    
    return True
