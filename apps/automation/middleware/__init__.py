"""
Middleware for Twin safety controls and authentication rate limiting.

Provides permission validation for Twin-initiated requests and rate limiting
for authentication endpoints.
Requirements: 8.1, 12.7, 16.5
"""

import logging
from django.http import JsonResponse
from django.utils.deprecation import MiddlewareMixin
from django.core.cache import cache
from django.utils import timezone
from datetime import timedelta


logger = logging.getLogger(__name__)


class TwinPermissionMiddleware(MiddlewareMixin):
    """
    Middleware to validate permission_flag for Twin-initiated requests.
    Requirements: 8.1, 12.7
    """

    TWIN_PROTECTED_ENDPOINTS = [
        '/api/v1/automations/',
        '/api/v1/workflows/',
        '/api/v1/integrations/',
    ]

    MODIFYING_METHODS = ['POST', 'PUT', 'PATCH', 'DELETE']

    def process_request(self, request):
        is_twin_initiated = request.headers.get('X-Twin-Initiated', 'false').lower() == 'true'
        if not is_twin_initiated:
            return None

        path = request.path
        requires_permission = any(
            path.startswith(endpoint) for endpoint in self.TWIN_PROTECTED_ENDPOINTS
        )

        if not requires_permission or request.method not in self.MODIFYING_METHODS:
            return None

        permission_flag = self._get_permission_flag(request)
        if not permission_flag:
            return self._deny_permission(request)

        logger.info(
            f'Twin permission granted for {request.method} {path} '
            f'by user {request.user.id if request.user.is_authenticated else "anonymous"}'
        )
        return None

    def _get_permission_flag(self, request) -> bool:
        if request.headers.get('X-Permission-Flag', 'false').lower() == 'true':
            return True
        if hasattr(request, 'data') and isinstance(request.data, dict):
            if request.data.get('permission_flag') is True:
                return True
        if request.GET.get('permission_flag', 'false').lower() == 'true':
            return True
        return False

    def _deny_permission(self, request) -> JsonResponse:
        from apps.twin.services.audit import AuditLogService
        user = request.user if request.user.is_authenticated else None
        path = request.path
        method = request.method

        logger.warning(
            f'Twin permission denied for {method} {path} '
            f'by user {user.id if user else "anonymous"}'
        )

        if user:
            AuditLogService.log_permission_denied(
                user=user,
                resource_type='API Endpoint',
                resource_id=path,
                action=method.lower(),
                details={
                    'path': path,
                    'method': method,
                    'reason': 'Missing permission_flag for Twin-initiated request',
                },
                ip_address=self._get_client_ip(request),
                user_agent=request.META.get('HTTP_USER_AGENT', '')
            )

        return JsonResponse(
            {
                'error': 'Permission denied',
                'message': 'Twin-initiated requests require explicit permission_flag',
                'code': 'TWIN_PERMISSION_REQUIRED',
            },
            status=403
        )

    def _get_client_ip(self, request) -> str:
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            return x_forwarded_for.split(',')[0]
        return request.META.get('REMOTE_ADDR') or ''


class KillSwitchMiddleware(MiddlewareMixin):
    """
    Middleware to enforce kill-switch for all Twin automations.
    Requirements: Safety principles
    """

    def process_request(self, request):
        is_twin_initiated = request.headers.get('X-Twin-Initiated', 'false').lower() == 'true'
        if not is_twin_initiated:
            return None
        if not request.user.is_authenticated:
            return None

        try:
            twin = request.user.twin
            if twin.kill_switch_active:
                return self._block_request(request, twin)
        except Exception as e:
            logger.error(f'Error checking kill-switch for user {request.user.id}: {e}')

        return None

    def _block_request(self, request, twin) -> JsonResponse:
        from apps.twin.services.audit import AuditLogService

        logger.warning(
            f'Kill-switch blocked Twin request for user {request.user.id} at {request.path}'
        )

        AuditLogService.log_twin_action(
            user=request.user,
            resource_type='API Endpoint',
            resource_id=request.path,
            action='blocked',
            result='denied',
            details={
                'path': request.path,
                'method': request.method,
                'reason': 'Kill-switch active',
            },
            cognitive_blend_value=twin.cognitive_blend,
            permission_flag=False,
            ip_address=self._get_client_ip(request),
            user_agent=request.META.get('HTTP_USER_AGENT', '')
        )

        return JsonResponse(
            {
                'error': 'Kill-switch active',
                'message': 'All Twin automations are currently disabled. '
                           'Please deactivate the kill-switch to resume Twin actions.',
                'code': 'KILL_SWITCH_ACTIVE',
            },
            status=403
        )

    def _get_client_ip(self, request) -> str:
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            return x_forwarded_for.split(',')[0]
        return request.META.get('REMOTE_ADDR') or ''


class AuthRateLimitMiddleware(MiddlewareMixin):
    """
    Middleware to enforce rate limiting on authentication endpoints.
    Requirements: 16.5
    """

    AUTH_ENDPOINTS = [
        '/api/v1/integrations/install/',
        '/api/v1/integrations/oauth/callback/',
        '/api/v1/integrations/meta/callback/',
        '/api/v1/integrations/api-key/complete/',
    ]

    MAX_ATTEMPTS = 10
    WINDOW_HOURS = 1

    def process_request(self, request):
        path = request.path
        is_auth_endpoint = any(path.startswith(ep) for ep in self.AUTH_ENDPOINTS)
        if not is_auth_endpoint:
            return None

        user_key = self._get_user_key(request)
        if self._is_rate_limited(user_key):
            return self._rate_limit_response(request, user_key)

        self._increment_attempts(user_key)
        return None

    def _get_user_key(self, request) -> str:
        if request.user.is_authenticated:
            return f'auth_rate_limit:user:{request.user.id}'
        return f'auth_rate_limit:ip:{self._get_client_ip(request)}'

    def _is_rate_limited(self, user_key: str) -> bool:
        return cache.get(user_key, 0) >= self.MAX_ATTEMPTS

    def _increment_attempts(self, user_key: str) -> None:
        attempts = cache.get(user_key, 0)
        cache.set(user_key, attempts + 1, timeout=self.WINDOW_HOURS * 3600)

    def _rate_limit_response(self, request, user_key: str) -> JsonResponse:
        ttl = cache.ttl(user_key)
        retry_after = ttl if ttl else self.WINDOW_HOURS * 3600

        logger.warning(f'Rate limit exceeded for {user_key} at {request.path}')

        return JsonResponse(
            {
                'error': 'Rate limit exceeded',
                'message': f'Too many authentication attempts. '
                           f'Please try again in {retry_after // 60} minutes.',
                'code': 'RATE_LIMIT_EXCEEDED',
                'retry_after': retry_after,
            },
            status=429
        )

    def _get_client_ip(self, request) -> str:
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            return x_forwarded_for.split(',')[0]
        return request.META.get('REMOTE_ADDR') or ''
