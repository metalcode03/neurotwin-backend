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
            'oauth_config',
            'default_permissions',
            'is_active',
            'created_at',
            'updated_at',
            'automation_template_count',
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']
    
    def get_automation_template_count(self, obj) -> int:
        """Get count of active automation templates for this integration type."""
        return obj.automation_templates.filter(is_active=True).count()
    
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
    
    def validate_oauth_config(self, value: dict) -> dict:
        """
        Validate OAuth configuration.
        
        Requirements: 2.3
        - authorization_url must be HTTPS
        - token_url must be HTTPS
        - Validate URL format
        """
        if not value:
            return value
        
        # Validate authorization_url
        if 'authorization_url' in value:
            auth_url = value['authorization_url']
            if not auth_url.startswith('https://'):
                raise serializers.ValidationError(
                    "authorization_url must use HTTPS protocol for security"
                )
            
            # Basic URL format validation
            if not self._is_valid_url(auth_url):
                raise serializers.ValidationError(
                    f"Invalid authorization_url format: {auth_url}"
                )
        
        # Validate token_url
        if 'token_url' in value:
            token_url = value['token_url']
            if not token_url.startswith('https://'):
                raise serializers.ValidationError(
                    "token_url must use HTTPS protocol for security"
                )
            
            # Basic URL format validation
            if not self._is_valid_url(token_url):
                raise serializers.ValidationError(
                    f"Invalid token_url format: {token_url}"
                )
        
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
        
        Ensures all required OAuth fields are present if oauth_config is provided.
        """
        oauth_config = attrs.get('oauth_config', {})
        
        if oauth_config:
            required_oauth_fields = ['client_id', 'authorization_url', 'token_url', 'scopes']
            missing_fields = [
                field for field in required_oauth_fields 
                if field not in oauth_config
            ]
            
            if missing_fields:
                raise serializers.ValidationError({
                    'oauth_config': f"Missing required OAuth fields: {', '.join(missing_fields)}"
                })
        
        return attrs
    
    def to_representation(self, instance):
        """
        Customize output representation.
        
        Excludes encrypted client_secret from response.
        """
        data = super().to_representation(instance)
        
        # Remove encrypted client_secret from oauth_config in response
        if 'oauth_config' in data and isinstance(data['oauth_config'], dict):
            oauth_config = data['oauth_config'].copy()
            oauth_config.pop('client_secret_encrypted', None)
            data['oauth_config'] = oauth_config
        
        return data
