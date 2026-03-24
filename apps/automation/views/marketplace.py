"""
IntegrationTypeViewSet for App Marketplace.

Handles listing, retrieving, and managing integration types.
Requirements: 10.1-10.3
"""

from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, IsAdminUser
from rest_framework.pagination import PageNumberPagination

from apps.automation.models import IntegrationTypeModel
from apps.automation.serializers import IntegrationTypeSerializer
from apps.automation.services import AppMarketplaceService


class IntegrationTypePagination(PageNumberPagination):
    """
    Pagination for integration type listings.
    
    Requirements: 10.1
    """
    page_size = 20
    page_size_query_param = 'page_size'
    max_page_size = 100


class IntegrationTypeViewSet(viewsets.ModelViewSet):
    """
    ViewSet for IntegrationType management.
    
    Provides:
    - list: GET /api/v1/integrations/types/ - List active integration types with filtering
    - retrieve: GET /api/v1/integrations/types/{id}/ - Get detailed integration type info
    - create: POST /api/v1/integrations/types/ - Create new integration type (admin only)
    - update: PUT/PATCH /api/v1/integrations/types/{id}/ - Update integration type (admin only)
    - destroy: DELETE /api/v1/integrations/types/{id}/ - Delete integration type (admin only)
    
    Requirements: 10.1-10.3
    """
    
    serializer_class = IntegrationTypeSerializer
    pagination_class = IntegrationTypePagination
    
    def get_permissions(self):
        """
        Set permissions based on action.
        
        - list, retrieve: Authenticated users
        - create, update, partial_update, destroy: Admin only
        
        Requirements: 10.1-10.3
        """
        if self.action in ['list', 'retrieve']:
            permission_classes = [IsAuthenticated]
        else:
            permission_classes = [IsAuthenticated, IsAdminUser]
        
        return [permission() for permission in permission_classes]
    
    def get_queryset(self):
        """
        Get queryset with filtering.
        
        Supports query parameters:
        - category: Filter by category
        - search: Search in name and description
        - is_active: Filter by active status (admin only)
        
        Requirements: 10.1-10.2
        """
        queryset = IntegrationTypeModel.objects.select_related('created_by')
        
        # Non-admin users only see active integration types
        if not self.request.user.is_staff:
            queryset = queryset.filter(is_active=True)
        
        # Apply filters from query parameters
        category = self.request.query_params.get('category')
        if category:
            queryset = queryset.filter(category=category)
        
        search = self.request.query_params.get('search')
        if search:
            from django.db.models import Q
            queryset = queryset.filter(
                Q(name__icontains=search) | Q(description__icontains=search)
            )
        
        # Admin-only filter
        if self.request.user.is_staff:
            is_active = self.request.query_params.get('is_active')
            if is_active is not None:
                queryset = queryset.filter(is_active=is_active.lower() == 'true')
        
        return queryset.order_by('name')
    
    def list(self, request, *args, **kwargs):
        """
        List integration types with filtering and pagination.
        
        Query parameters:
        - category: Filter by category
        - search: Search term for name/description
        - page: Page number
        - page_size: Items per page (max 100)
        
        Requirements: 10.1-10.2
        """
        # Use service layer for caching and business logic
        category = request.query_params.get('category')
        search = request.query_params.get('search')
        page = int(request.query_params.get('page', 1))
        page_size = int(request.query_params.get('page_size', 20))
        
        # Get integration types from service (with caching)
        integration_types = AppMarketplaceService.list_integration_types(
            user=request.user,
            category=category,
            search=search,
            page=page,
            page_size=page_size
        )
        
        # Serialize and paginate
        paginator = self.pagination_class()
        paginated_queryset = paginator.paginate_queryset(
            integration_types,
            request,
            view=self
        )
        
        serializer = self.get_serializer(paginated_queryset, many=True)
        
        return paginator.get_paginated_response(serializer.data)
    
    def retrieve(self, request, *args, **kwargs):
        """
        Get detailed integration type information.
        
        Includes:
        - Full integration type details
        - Automation templates
        - Installation status for current user
        
        Requirements: 10.3
        """
        instance = self.get_object()
        
        # Use service layer to get detailed info with installation status
        detail_data = AppMarketplaceService.get_integration_type_detail(
            integration_type_id=str(instance.id),
            user=request.user
        )
        
        return Response(detail_data)
    
    def perform_create(self, serializer):
        """
        Create integration type with current user as creator.
        
        Requirements: 10.1
        """
        serializer.save(created_by=self.request.user)
        
        # Invalidate marketplace cache
        AppMarketplaceService.invalidate_marketplace_cache()
    
    def perform_update(self, serializer):
        """
        Update integration type and invalidate cache.
        
        Requirements: 10.1
        """
        serializer.save()
        
        # Invalidate marketplace cache
        AppMarketplaceService.invalidate_marketplace_cache()
    
    def perform_destroy(self, instance):
        """
        Delete integration type with validation.
        
        Prevents deletion if any user has installed this integration type.
        
        Requirements: 1.7
        """
        from apps.automation.models import Integration
        
        # Check if any installations exist
        installation_count = Integration.objects.filter(
            integration_type=instance
        ).count()
        
        if installation_count > 0:
            from rest_framework.exceptions import ValidationError
            raise ValidationError(
                f'Cannot delete integration type: {installation_count} '
                f'user(s) have installed this integration'
            )
        
        instance.delete()
        
        # Invalidate marketplace cache
        AppMarketplaceService.invalidate_marketplace_cache()
    
    @action(detail=False, methods=['get'], permission_classes=[IsAuthenticated])
    def categories(self, request):
        """
        Get all categories with integration counts.
        
        GET /api/v1/integrations/types/categories/
        
        Returns:
            {
                "categories": {
                    "communication": 5,
                    "productivity": 3,
                    ...
                }
            }
        
        Requirements: 13.1-13.6
        """
        categories = AppMarketplaceService.get_categories_with_counts()
        
        return Response({
            'categories': categories
        })
