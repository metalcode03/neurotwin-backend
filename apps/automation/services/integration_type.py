"""
Integration Type Service.

Manages CRUD operations for integration types (admin-only).
Requirements: 1.1-1.7, 2.1-2.6
"""

import re
import base64
from typing import Optional
from uuid import UUID

from django.core.files import File
from django.core.exceptions import ValidationError
from django.core.cache import cache
from django.db import transaction

from ..models import IntegrationTypeModel
from ..utils.encryption import TokenEncryption


class IntegrationTypeService:
    """Service for managing integration types."""
    
    # Cache key for marketplace active types
    MARKETPLACE_CACHE_KEY = 'marketplace:active_types'
    
    @staticmethod
    def create_integration_type(
        type_identifier: str,
        name: str,
        icon: File,
        description: str,
        category: str,
        oauth_config: dict,
        brief_description: str = '',
        default_permissions: Optional[dict] = None,
        created_by=None
    ) -> IntegrationTypeModel:
        """
        Create a new integration type with validation.
        
        Args:
            type_identifier: Unique kebab-case identifier
            name: Human-readable name
            icon: Icon file (SVG/PNG, max 500KB)
            description: Full description
            category: Category for organization
            oauth_config: OAuth 2.0 configuration
            brief_description: Short description for card display
            default_permissions: Default permission settings
            created_by: User creating the integration type
            
        Returns:
            IntegrationType: Created integration type
            
        Raises:
            ValidationError: If validation fails
        """
        # Validate type identifier format and uniqueness
        if not IntegrationTypeService.validate_type_identifier(type_identifier):
            raise ValidationError(
                f'Invalid type identifier: {type_identifier}. '
                'Must be kebab-case format (lowercase letters, numbers, hyphens only).'
            )
        
        # Check uniqueness
        if IntegrationTypeModel.objects.filter(type=type_identifier).exists():
            raise ValidationError(
                f'Integration type with identifier "{type_identifier}" already exists.'
            )
        
        # Validate icon file size and format
        if icon:
            # Check file size (max 500KB)
            max_size = 500 * 1024  # 500KB in bytes
            if icon.size > max_size:
                raise ValidationError(
                    f'Icon file size ({icon.size} bytes) exceeds maximum allowed size (500KB).'
                )
            
            # Check file format (SVG or PNG)
            allowed_extensions = ['.svg', '.png']
            file_extension = icon.name.lower().split('.')[-1] if '.' in icon.name else ''
            if f'.{file_extension}' not in allowed_extensions:
                raise ValidationError(
                    f'Icon file format must be SVG or PNG. Got: {file_extension}'
                )
        
        # Prepare OAuth config with encrypted client secret
        processed_oauth_config = oauth_config.copy()
        if 'client_secret' in processed_oauth_config:
            client_secret = processed_oauth_config.pop('client_secret')
            if client_secret:
                # Encrypt the client secret
                encrypted = TokenEncryption.encrypt(client_secret)
                processed_oauth_config['client_secret_encrypted'] = \
                    base64.b64encode(encrypted).decode()
        
        # Create the integration type
        with transaction.atomic():
            integration_type = IntegrationTypeModel.objects.create(
                type=type_identifier,
                name=name,
                icon=icon,
                description=description,
                brief_description=brief_description or description[:200],
                category=category,
                oauth_config=processed_oauth_config,
                default_permissions=default_permissions or {},
                created_by=created_by
            )
            
            # Invalidate marketplace cache
            cache.delete(IntegrationTypeService.MARKETPLACE_CACHE_KEY)
        
        return integration_type
    
    @staticmethod
    def update_integration_type(
        integration_type_id: UUID,
        **updates
    ) -> IntegrationTypeModel:
        """
        Update an existing integration type.
        
        Args:
            integration_type_id: ID of integration type to update
            **updates: Fields to update
            
        Returns:
            IntegrationType: Updated integration type
            
        Raises:
            IntegrationTypeModel.DoesNotExist: If integration type not found
            ValidationError: If validation fails
        """
        integration_type = IntegrationTypeModel.objects.get(id=integration_type_id)
        
        # Validate icon if provided
        if 'icon' in updates and updates['icon']:
            icon = updates['icon']
            max_size = 500 * 1024  # 500KB
            if icon.size > max_size:
                raise ValidationError(
                    f'Icon file size ({icon.size} bytes) exceeds maximum allowed size (500KB).'
                )
            
            allowed_extensions = ['.svg', '.png']
            file_extension = icon.name.lower().split('.')[-1] if '.' in icon.name else ''
            if f'.{file_extension}' not in allowed_extensions:
                raise ValidationError(
                    f'Icon file format must be SVG or PNG. Got: {file_extension}'
                )
        
        # Handle OAuth config updates with client secret encryption
        if 'oauth_config' in updates:
            oauth_config = updates['oauth_config'].copy()
            
            # If client_secret is being updated, encrypt it
            if 'client_secret' in oauth_config:
                client_secret = oauth_config.pop('client_secret')
                if client_secret:
                    encrypted = TokenEncryption.encrypt(client_secret)
                    oauth_config['client_secret_encrypted'] = \
                        base64.b64encode(encrypted).decode()
                else:
                    # Remove encrypted secret if empty
                    oauth_config.pop('client_secret_encrypted', None)
            
            updates['oauth_config'] = oauth_config
        
        # Update fields
        with transaction.atomic():
            for field, value in updates.items():
                if hasattr(integration_type, field):
                    setattr(integration_type, field, value)
            
            integration_type.save()
            
            # Invalidate relevant caches
            cache.delete(IntegrationTypeService.MARKETPLACE_CACHE_KEY)
            cache.delete(f'oauth_config:{integration_type_id}')
        
        return integration_type
    
    @staticmethod
    def deactivate_integration_type(
        integration_type_id: UUID
    ) -> IntegrationTypeModel:
        """
        Set integration type to inactive.
        
        Preserves existing user installations but hides from marketplace.
        
        Args:
            integration_type_id: ID of integration type to deactivate
            
        Returns:
            IntegrationType: Deactivated integration type
            
        Raises:
            IntegrationTypeModel.DoesNotExist: If integration type not found
        """
        integration_type = IntegrationTypeModel.objects.get(id=integration_type_id)
        
        with transaction.atomic():
            integration_type.is_active = False
            integration_type.save(update_fields=['is_active', 'updated_at'])
            
            # Invalidate marketplace cache
            cache.delete(IntegrationTypeService.MARKETPLACE_CACHE_KEY)
        
        return integration_type
    
    @staticmethod
    def validate_type_identifier(identifier: str) -> bool:
        """
        Validate kebab-case format and uniqueness.
        
        Checks that identifier:
        - Contains only lowercase letters, numbers, and hyphens
        - Starts and ends with alphanumeric characters
        - Does not have consecutive hyphens
        
        Args:
            identifier: Type identifier to validate
            
        Returns:
            bool: True if valid format, False otherwise
        """
        if not identifier:
            return False
        
        # Kebab-case regex: lowercase letters, numbers, hyphens
        # Must start and end with alphanumeric, no consecutive hyphens
        kebab_case_pattern = r'^[a-z0-9]+(-[a-z0-9]+)*$'
        
        return bool(re.match(kebab_case_pattern, identifier))
