"""
IntegrationTypeSerializer for Dynamic App Marketplace.

Handles serialization and validation for IntegrationType model.
Requirements: 1.2-1.3, 2.3
"""

import re
from rest_framework import serializers
from apps.automation.models import IntegrationTypeModel, IntegrationCategory


class IntegrationTypeSerializer(serializers.ModelSerializer):
    """
    Serializer for IntegrationType model.
    
    Includes all fields except encrypted secrets.
    Validates type identifier format, icon file, and OAuth URLs.
    
    Requirements: 1.2-1.3, 2.3
    """
    
    # Read-only computed fields
    automation_template_count = serializers.SerializerMethodField()
    required_fields = serializers.SerializerMethodField()
    
    class Meta:
        model = IntegrationTypeModel
        fields = [
            'id',
            'type',
            'name',
            'icon',
            'description',
            'brief_description',
            'category',
            'auth_type',
            'auth_config',
            'oauth_config',  # Backward compatibility
            'default_permissions',
            'is_active',
            'created_at',
            'updated_at',
            'automation_template_count',
            'required_fields',
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']
    
    def get_automation_template_count(self, obj) -> int:
        """Get count of active automation templates for this integration type."""
        return obj.automation_templates.filter(is_active=True).count()
    
    def get_required_fields(self, obj) -> list:
        """
        Get list of required auth_config fields based on auth_type.
        
        Requirements: 12.7
        """
        return obj.get_required_auth_fields()
    
    def validate_type(self, value: str) -> str:
        """
        Validate type identifier is in kebab-case format.
        
        Requirements: 1.2
        - Must be lowercase
        - Must use hyphens for word separation
        - Must not start or end with hyphen
        - Must contain only alphanumeric characters and hyphens
        """
        if not value:
            raise serializers.ValidationError("Type identifier is required")
        
        # Check kebab-case format
        if not re.match(r'^[a-z0-9]+(-[a-z0-9]+)*$', value):
            raise serializers.ValidationError(
                "Type must be in kebab-case format (lowercase letters, numbers, "
                "and hyphens only, e.g., 'gmail', 'google-calendar')"
            )
        
        # Check uniqueness (only on create or if value changed)
        if self.instance is None or self.instance.type != value:
            if IntegrationTypeModel.objects.filter(type=value).exists():
                raise serializers.ValidationError(
                    f"Integration type '{value}' already exists"
                )
        
        return value
    
    def validate_icon(self, value):
        """
        Validate icon file size and format.
        
        Requirements: 1.3
        - Maximum file size: 500KB
        - Allowed formats: SVG, PNG
        """
        if not value:
            return value
        
        # Check file size (500KB = 512000 bytes)
        max_size = 512000
        if value.size > max_size:
            raise serializers.ValidationError(
                f"Icon file size must not exceed 500KB. "
                f"Current size: {value.size / 1024:.1f}KB"
            )
        
        # Check file format
        allowed_extensions = ['.svg', '.png']
        file_extension = value.name.lower().split('.')[-1] if '.' in value.name else ''
        
        if f'.{file_extension}' not in allowed_extensions:
            raise serializers.ValidationError(
                f"Icon must be SVG or PNG format. "
                f"Received: {file_extension or 'unknown'}"
            )
        
        # Additional MIME type validation
        allowed_mime_types = ['image/svg+xml', 'image/png']
        if hasattr(value, 'content_type') and value.content_type:
            if value.content_type not in allowed_mime_types:
                raise serializers.ValidationError(
                    f"Invalid icon MIME type. Expected SVG or PNG, "
                    f"got: {value.content_type}"
                )
        
        return value
    
    def validate_auth_config(self, value: dict) -> dict:
        """
        Validate authentication configuration based on auth_type.
        
        Requirements: 2.3, 4.7, 11.7
        - OAuth: authorization_url and token_url must be HTTPS
        - Meta: business_verification_url must be HTTPS
        - Validate URL format
        """
        if not value:
            return value
        
        # Validate HTTPS URLs for OAuth
        if 'authorization_url' in value:
            auth_url = value['authorization_url']
            if not auth_url.startswith('https://'):
                raise serializers.ValidationError(
                    "authorization_url must use HTTPS protocol for security"
                )
            
            if not self._is_valid_url(auth_url):
                raise serializers.ValidationError(
                    f"Invalid authorization_url format: {auth_url}"
                )
        
        if 'token_url' in value:
            token_url = value['token_url']
            if not token_url.startswith('https://'):
                raise serializers.ValidationError(
                    "token_url must use HTTPS protocol for security"
                )
            
            if not self._is_valid_url(token_url):
                raise serializers.ValidationError(
                    f"Invalid token_url format: {token_url}"
                )
        
        # Validate HTTPS URLs for Meta
        if 'business_verification_url' in value:
            meta_url = value['business_verification_url']
            if not meta_url.startswith('https://'):
                raise serializers.ValidationError(
                    "business_verification_url must use HTTPS protocol for security"
                )
            
            if not self._is_valid_url(meta_url):
                raise serializers.ValidationError(
                    f"Invalid business_verification_url format: {meta_url}"
                )
        
        # Validate API endpoint URL
        if 'api_endpoint' in value:
            api_url = value['api_endpoint']
            if not api_url.startswith('https://'):
                raise serializers.ValidationError(
                    "api_endpoint must use HTTPS protocol for security"
                )
            
            if not self._is_valid_url(api_url):
                raise serializers.ValidationError(
                    f"Invalid api_endpoint format: {api_url}"
                )
        
        return value
    
    def validate_oauth_config(self, value: dict) -> dict:
        """
        Backward compatibility: validate oauth_config (alias for auth_config).
        
        Requirements: 2.3, 15.5
        """
        return self.validate_auth_config(value)
        
        return value
    
    def _is_valid_url(self, url: str) -> bool:
        """
        Basic URL format validation.
        
        Checks for valid URL structure without making network requests.
        """
        # Simple regex for URL validation
        url_pattern = re.compile(
            r'^https://'  # Must start with https://
            r'(?:(?:[A-Z0-9](?:[A-Z0-9-]{0,61}[A-Z0-9])?\.)+[A-Z]{2,6}\.?|'  # domain
            r'localhost|'  # localhost
            r'\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})'  # IP
            r'(?::\d+)?'  # optional port
            r'(?:/?|[/?]\S+)$', re.IGNORECASE
        )
        return bool(url_pattern.match(url))
    
    def validate(self, attrs):
        """
        Object-level validation.
        
        Ensures all required auth_config fields are present based on auth_type.
        Requirements: 1.4, 2.6
        """
        auth_type = attrs.get('auth_type', self.instance.auth_type if self.instance else 'oauth')
        auth_config = attrs.get('auth_config') or attrs.get('oauth_config', {})
        
        if auth_config:
            # Get required fields for this auth_type
            if auth_type == 'oauth':
                required_fields = ['client_id', 'authorization_url', 'token_url', 'scopes']
            elif auth_type == 'meta':
                required_fields = ['app_id', 'config_id', 'business_verification_url']
            elif auth_type == 'api_key':
                required_fields = ['api_endpoint', 'authentication_header_name']
            else:
                required_fields = []
            
            missing_fields = [
                field for field in required_fields 
                if field not in auth_config
            ]
            
            if missing_fields:
                raise serializers.ValidationError({
                    'auth_config': f"Missing required fields for {auth_type}: {', '.join(missing_fields)}"
                })
        
        return attrs
    
    def to_representation(self, instance):
        """
        Customize output representation.
        
        Excludes encrypted secrets from response.
        Includes both auth_config and oauth_config for backward compatibility.
        
        Requirements: 12.7, 15.5
        """
        data = super().to_representation(instance)
        
        # Remove encrypted secrets from auth_config in response
        if 'auth_config' in data and isinstance(data['auth_config'], dict):
            auth_config = data['auth_config'].copy()
            auth_config.pop('client_secret_encrypted', None)
            auth_config.pop('app_secret_encrypted', None)
            auth_config.pop('api_key_encrypted', None)
            data['auth_config'] = auth_config
        
        # Backward compatibility: also provide oauth_config
        if 'oauth_config' in data and isinstance(data['oauth_config'], dict):
            oauth_config = data['oauth_config'].copy()
            oauth_config.pop('client_secret_encrypted', None)
            oauth_config.pop('app_secret_encrypted', None)
            oauth_config.pop('api_key_encrypted', None)
            data['oauth_config'] = oauth_config
        
        return data
