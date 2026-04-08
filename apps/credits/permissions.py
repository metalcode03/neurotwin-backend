"""
Custom DRF permission classes for credit system.

Requirements: 22.8
"""

from rest_framework.permissions import BasePermission


class IsAdminUser(BasePermission):
    """
    Allows access only to users with is_staff=True.

    Applied to admin endpoints like AdminAIRequestViewSet
    and AdminBrainConfigViewSet.

    Requirements: 22.8
    """

    def has_permission(self, request, view):
        return bool(
            request.user
            and request.user.is_authenticated
            and request.user.is_staff
        )
