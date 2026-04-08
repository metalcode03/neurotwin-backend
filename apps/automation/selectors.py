"""
Database selectors for optimized queries.

Provides query methods with proper select_related and prefetch_related
to avoid N+1 query problems in authentication flows.

Requirements: 22.4
"""

import logging
from typing import List, Optional
from django.db.models import QuerySet

from apps.automation.models import (
    Integration,
    IntegrationTypeModel,
    InstallationSession,
    AuthenticationAuditLog,
)


logger = logging.getLogger(__name__)


class IntegrationSelector:
    """
    Optimized queries for Integration model.
    
    Uses select_related to fetch related IntegrationTypeModel in a single query,
    avoiding N+1 query problems.
    
    Requirements: 22.4
    """
    
    @staticmethod
    def get_user_integrations(user, is_active: Optional[bool] = None) -> QuerySet:
        """
        Get user's integrations with optimized query.
        
        Uses select_related('integration_type') to fetch integration type
        in a single query instead of N+1 queries.
        
        Args:
            user: User instance
            is_active: Optional filter for active/inactive integrations
            
        Returns:
            QuerySet of Integration instances with integration_type prefetched
            
        Requirements: 22.4
        """
        queryset = Integration.objects.select_related(
            'integration_type'
        ).filter(user=user)
        
        if is_active is not None:
            queryset = queryset.filter(is_active=is_active)
        
        return queryset.order_by('-created_at')
    
    @staticmethod
    def get_integration_by_id(
        integration_id: str,
        user=None
    ) -> Optional[Integration]:
        """
        Get integration by ID with optimized query.
        
        Args:
            integration_id: UUID of integration
            user: Optional user filter
            
        Returns:
            Integration instance or None
            
        Requirements: 22.4
        """
        queryset = Integration.objects.select_related('integration_type')
        
        if user:
            queryset = queryset.filter(user=user)
        
        try:
            return queryset.get(id=integration_id)
        except Integration.DoesNotExist:
            return None
    
    @staticmethod
    def get_integrations_by_type(
        user,
        integration_type_id: str,
        is_active: Optional[bool] = None
    ) -> QuerySet:
        """
        Get user's integrations for a specific type.
        
        Args:
            user: User instance
            integration_type_id: UUID of integration type
            is_active: Optional filter for active/inactive
            
        Returns:
            QuerySet of Integration instances
            
        Requirements: 22.4
        """
        queryset = Integration.objects.select_related(
            'integration_type'
        ).filter(
            user=user,
            integration_type_id=integration_type_id
        )
        
        if is_active is not None:
            queryset = queryset.filter(is_active=is_active)
        
        return queryset
    
    @staticmethod
    def get_integrations_by_auth_type(
        user,
        auth_type: str,
        is_active: Optional[bool] = True
    ) -> QuerySet:
        """
        Get user's integrations filtered by authentication type.
        
        Uses composite index on (is_active, auth_type) for optimal performance.
        
        Args:
            user: User instance
            auth_type: Authentication type (oauth, meta, api_key)
            is_active: Optional filter for active/inactive (default: True)
            
        Returns:
            QuerySet of Integration instances
            
        Requirements: 22.4
        """
        queryset = Integration.objects.select_related(
            'integration_type'
        ).filter(
            user=user,
            integration_type__auth_type=auth_type
        )
        
        if is_active is not None:
            queryset = queryset.filter(is_active=is_active)
        
        return queryset.order_by('-created_at')
    
    @staticmethod
    def get_expiring_tokens(days: int = 7) -> QuerySet:
        """
        Get integrations with tokens expiring soon.
        
        Used for token refresh background tasks.
        
        Args:
            days: Number of days to look ahead
            
        Returns:
            QuerySet of Integration instances with expiring tokens
            
        Requirements: 22.4
        """
        from datetime import timedelta
        from django.utils import timezone
        
        cutoff = timezone.now() + timedelta(days=days)
        
        return Integration.objects.select_related(
            'integration_type'
        ).filter(
            is_active=True,
            token_expires_at__lte=cutoff,
            token_expires_at__isnull=False
        ).order_by('token_expires_at')


class IntegrationTypeSelector:
    """
    Optimized queries for IntegrationTypeModel.
    
    Uses indexes on auth_type and is_active for optimal performance.
    
    Requirements: 22.4
    """
    
    @staticmethod
    def get_active_types(auth_type: Optional[str] = None) -> QuerySet:
        """
        Get active integration types.
        
        Uses index on (is_active, auth_type) for optimal performance.
        
        Args:
            auth_type: Optional filter by authentication type
            
        Returns:
            QuerySet of IntegrationTypeModel instances
            
        Requirements: 22.4
        """
        queryset = IntegrationTypeModel.objects.filter(is_active=True)
        
        if auth_type:
            queryset = queryset.filter(auth_type=auth_type)
        
        return queryset.order_by('name')
    
    @staticmethod
    def get_type_by_id(integration_type_id: str) -> Optional[IntegrationTypeModel]:
        """
        Get integration type by ID.
        
        Args:
            integration_type_id: UUID of integration type
            
        Returns:
            IntegrationTypeModel instance or None
            
        Requirements: 22.4
        """
        try:
            return IntegrationTypeModel.objects.get(
                id=integration_type_id,
                is_active=True
            )
        except IntegrationTypeModel.DoesNotExist:
            return None
    
    @staticmethod
    def get_types_by_category(
        category: str,
        is_active: bool = True
    ) -> QuerySet:
        """
        Get integration types by category.
        
        Args:
            category: Category identifier
            is_active: Filter by active status
            
        Returns:
            QuerySet of IntegrationTypeModel instances
            
        Requirements: 22.4
        """
        return IntegrationTypeModel.objects.filter(
            category=category,
            is_active=is_active
        ).order_by('name')


class InstallationSessionSelector:
    """
    Optimized queries for InstallationSession model.
    
    Uses select_related to fetch related models efficiently.
    
    Requirements: 22.4
    """
    
    @staticmethod
    def get_session_by_id(session_id: str) -> Optional[InstallationSession]:
        """
        Get installation session by ID with related data.
        
        Args:
            session_id: UUID of installation session
            
        Returns:
            InstallationSession instance or None
            
        Requirements: 22.4
        """
        try:
            return InstallationSession.objects.select_related(
                'integration_type',
                'user'
            ).get(id=session_id)
        except InstallationSession.DoesNotExist:
            return None
    
    @staticmethod
    def get_user_sessions(
        user,
        status: Optional[str] = None
    ) -> QuerySet:
        """
        Get user's installation sessions.
        
        Args:
            user: User instance
            status: Optional status filter
            
        Returns:
            QuerySet of InstallationSession instances
            
        Requirements: 22.4
        """
        queryset = InstallationSession.objects.select_related(
            'integration_type'
        ).filter(user=user)
        
        if status:
            queryset = queryset.filter(status=status)
        
        return queryset.order_by('-created_at')
    
    @staticmethod
    def get_session_by_state(oauth_state: str) -> Optional[InstallationSession]:
        """
        Get installation session by OAuth state.
        
        Used for OAuth callback validation.
        
        Args:
            oauth_state: OAuth state parameter
            
        Returns:
            InstallationSession instance or None
            
        Requirements: 22.4
        """
        try:
            return InstallationSession.objects.select_related(
                'integration_type',
                'user'
            ).get(oauth_state=oauth_state)
        except InstallationSession.DoesNotExist:
            return None


class AuthenticationAuditLogSelector:
    """
    Optimized queries for AuthenticationAuditLog model.
    
    Uses select_related and proper indexing for audit log queries.
    
    Requirements: 22.4
    """
    
    @staticmethod
    def get_user_logs(
        user,
        days: int = 30,
        auth_type: Optional[str] = None
    ) -> QuerySet:
        """
        Get user's authentication audit logs.
        
        Args:
            user: User instance
            days: Number of days to look back
            auth_type: Optional filter by authentication type
            
        Returns:
            QuerySet of AuthenticationAuditLog instances
            
        Requirements: 22.4
        """
        from datetime import timedelta
        from django.utils import timezone
        
        cutoff = timezone.now() - timedelta(days=days)
        
        queryset = AuthenticationAuditLog.objects.select_related(
            'integration_type'
        ).filter(
            user=user,
            created_at__gte=cutoff
        )
        
        if auth_type:
            queryset = queryset.filter(auth_type=auth_type)
        
        return queryset.order_by('-created_at')
    
    @staticmethod
    def get_failed_attempts(
        user=None,
        hours: int = 24,
        auth_type: Optional[str] = None
    ) -> QuerySet:
        """
        Get failed authentication attempts.
        
        Args:
            user: Optional user filter
            hours: Number of hours to look back
            auth_type: Optional filter by authentication type
            
        Returns:
            QuerySet of failed AuthenticationAuditLog instances
            
        Requirements: 22.4
        """
        from datetime import timedelta
        from django.utils import timezone
        
        cutoff = timezone.now() - timedelta(hours=hours)
        
        queryset = AuthenticationAuditLog.objects.select_related(
            'integration_type'
        ).filter(
            success=False,
            created_at__gte=cutoff
        )
        
        if user:
            queryset = queryset.filter(user=user)
        
        if auth_type:
            queryset = queryset.filter(auth_type=auth_type)
        
        return queryset.order_by('-created_at')
