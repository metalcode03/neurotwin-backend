"""
App Marketplace Service.

Handles app discovery, filtering, search, and installation status checks.

Requirements: 3.3-3.5, 3.6, 3.8, 10.1-10.3, 13.1-13.6, 17.3, 17.5
"""

from typing import Optional, Dict, List
from django.core.cache import cache
from django.db.models import QuerySet, Q, Count
from django.contrib.auth import get_user_model

from ..models import IntegrationTypeModel, Integration, AutomationTemplate
from ..cache import MarketplaceCache

User = get_user_model()


class AppMarketplaceService:
    """Service for app marketplace operations."""
    
    @staticmethod
    def list_integration_types(
        user: User,
        category: Optional[str] = None,
        search: Optional[str] = None,
        page: int = 1,
        page_size: int = 20
    ) -> QuerySet[IntegrationTypeModel]:
        """
        List active integration types with filtering.
        
        Requirements: 3.3-3.5, 10.1-10.2, 17.3
        
        Args:
            user: The requesting user
            category: Optional category filter
            search: Optional search term (name/description)
            page: Page number (1-indexed)
            page_size: Number of items per page (default 20)
            
        Returns:
            QuerySet of IntegrationTypeModel instances
        """
        # Build queryset
        queryset = IntegrationTypeModel.objects.filter(
            is_active=True
        ).select_related('created_by')
        
        # Apply category filter
        if category:
            queryset = queryset.filter(category=category)
        
        # Apply search filter (case-insensitive)
        if search:
            queryset = queryset.filter(
                Q(name__icontains=search) | Q(description__icontains=search)
            )
        
        # Order by name
        queryset = queryset.order_by('name')
        
        # Apply pagination
        start = (page - 1) * page_size
        end = start + page_size
        paginated_queryset = queryset[start:end]
        
        return paginated_queryset

    
    @staticmethod
    def get_integration_type_detail(
        integration_type_id: str,
        user: User
    ) -> Dict:
        """
        Get detailed integration type info with installation status.
        
        Requirements: 3.6, 10.3
        
        Args:
            integration_type_id: UUID of the integration type
            user: The requesting user
            
        Returns:
            Dictionary with integration type details, templates, and installation status
            
        Raises:
            IntegrationTypeModel.DoesNotExist: If integration type not found
        """
        # Fetch integration type with related data
        integration_type = IntegrationTypeModel.objects.select_related(
            'created_by'
        ).prefetch_related(
            'automation_templates'
        ).get(id=integration_type_id)
        
        # Check installation status
        is_installed = AppMarketplaceService.is_installed(user, integration_type_id)
        
        # Get active automation templates
        templates = integration_type.automation_templates.filter(
            is_active=True
        ).values(
            'id',
            'name',
            'description',
            'trigger_type',
            'is_enabled_by_default'
        )
        
        # Build response
        return {
            'id': str(integration_type.id),
            'type': integration_type.type,
            'name': integration_type.name,
            'icon': integration_type.icon.url if integration_type.icon else None,
            'description': integration_type.description,
            'brief_description': integration_type.brief_description,
            'category': integration_type.category,
            'is_active': integration_type.is_active,
            'is_installed': is_installed,
            'automation_templates': list(templates),
            'default_permissions': integration_type.default_permissions,
            'oauth_scopes': integration_type.oauth_scopes,
            'created_at': integration_type.created_at.isoformat(),
            'updated_at': integration_type.updated_at.isoformat(),
        }

    
    @staticmethod
    def is_installed(
        user: User,
        integration_type_id: str
    ) -> bool:
        """
        Check if user has installed this integration type.
        
        Requirements: 3.8, 5.1, 17.2
        
        Args:
            user: The user to check
            integration_type_id: UUID of the integration type
            
        Returns:
            True if user has an active Integration record for this type
        """
        # Try to get from cache
        installed_ids = MarketplaceCache.get_user_installed(user.id)
        
        if installed_ids is None:
            # Fetch from database
            installed_ids = set(
                str(id) for id in Integration.objects.filter(
                    user=user
                ).values_list('integration_type_id', flat=True)
            )
            
            # Cache the result
            MarketplaceCache.cache_user_installed(user.id, installed_ids)
        
        # Check if integration_type_id is in the set
        return str(integration_type_id) in installed_ids

    
    @staticmethod
    def get_categories_with_counts() -> Dict[str, int]:
        """
        Get all categories with active integration counts.
        
        Requirements: 13.1-13.6, 17.1
        
        Returns:
            Dictionary mapping category names to integration counts
        """
        # Try to get from cache
        cached_result = cache.get(MarketplaceCache.KEY_CATEGORIES)
        
        if cached_result is not None:
            return cached_result
        
        # Query database for counts
        category_counts = IntegrationTypeModel.objects.filter(
            is_active=True
        ).values('category').annotate(
            count=Count('id')
        ).order_by('category')
        
        # Build result dictionary
        result = {
            item['category']: item['count']
            for item in category_counts
        }
        
        # Cache the result
        cache.set(
            MarketplaceCache.KEY_CATEGORIES,
            result,
            MarketplaceCache.TTL_CATEGORIES
        )
        
        return result
    
    @staticmethod
    def invalidate_marketplace_cache():
        """
        Invalidate all marketplace-related caches.
        
        Should be called when IntegrationType records are created/updated/deleted.
        Deprecated: Use MarketplaceCache.invalidate_active_types() instead.
        """
        MarketplaceCache.invalidate_active_types()
    
    @staticmethod
    def invalidate_user_installed_cache(user_id: int):
        """
        Invalidate user's installed integrations cache.
        
        Should be called when Integration records are created/deleted.
        Deprecated: Use MarketplaceCache.invalidate_user_installed() instead.
        
        Args:
            user_id: ID of the user whose cache should be invalidated
        """
        MarketplaceCache.invalidate_user_installed(user_id)
