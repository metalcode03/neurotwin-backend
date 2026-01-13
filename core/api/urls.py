"""
Main API URL configuration for NeuroTwin platform.

Routes all API endpoints through versioned URL paths.
Requirements: 13.1, 13.6 - REST conventions and API versioning
"""

from django.urls import path, include

app_name = 'api'

# API v1 URL patterns
v1_patterns = [
    path('auth/', include('apps.authentication.urls', namespace='auth')),
    path('twin/', include('apps.twin.urls', namespace='twin')),
    path('csm/', include('apps.csm.urls', namespace='csm')),
    path('subscription/', include('apps.subscription.urls', namespace='subscription')),
    path('integrations/', include('apps.automation.urls_integrations', namespace='integrations')),
    path('workflows/', include('apps.automation.urls_workflows', namespace='workflows')),
    path('voice/', include('apps.voice.urls', namespace='voice')),
    path('permissions/', include('apps.safety.urls_permissions', namespace='permissions')),
    path('audit/', include('apps.safety.urls_audit', namespace='audit')),
    path('kill-switch/', include('apps.safety.urls_killswitch', namespace='killswitch')),
    path('actions/', include('apps.safety.urls_actions', namespace='actions')),
]

urlpatterns = [
    path('v1/', include((v1_patterns, 'v1'))),
]
