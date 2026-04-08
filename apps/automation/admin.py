"""
Django admin configuration for automation app.
"""

import base64
from django import forms
from django.contrib import admin
from django.db.models import Count
from django.utils.html import format_html
from django.core.exceptions import ValidationError
from django.urls import reverse
from django.utils.safestring import mark_safe

from .models import (
    AutomationTemplate,
    Integration,
    IntegrationTypeModel,
    AuthType,
    WebhookEvent,
    Message,
    Conversation,
)
from .utils.encryption import TokenEncryption
from .utils.auth_config_cache import AuthConfigCache


class IntegrationTypeAdminForm(forms.ModelForm):
    """
    Custom form for IntegrationType with dynamic fields based on auth_type.
    
    Requirements: 18.1-18.8
    """
    
    # OAuth fields
    oauth_client_id = forms.CharField(
        required=False,
        max_length=255,
        help_text='OAuth 2.0 client ID'
    )
    oauth_client_secret = forms.CharField(
        required=False,
        widget=forms.PasswordInput(render_value=False),
        help_text='OAuth 2.0 client secret (will be encrypted on save)'
    )
    oauth_authorization_url = forms.URLField(
        required=False,
        help_text='OAuth 2.0 authorization endpoint URL (must be HTTPS)'
    )
    oauth_token_url = forms.URLField(
        required=False,
        help_text='OAuth 2.0 token endpoint URL (must be HTTPS)'
    )
    oauth_revoke_url = forms.URLField(
        required=False,
        help_text='OAuth 2.0 token revocation endpoint URL (optional)'
    )
    oauth_scopes = forms.CharField(
        required=False,
        widget=forms.Textarea(attrs={'rows': 3}),
        help_text='OAuth scopes (comma-separated or one per line)'
    )
    
    # Meta fields
    meta_app_id = forms.CharField(
        required=False,
        max_length=255,
        help_text='Meta App ID'
    )
    meta_app_secret = forms.CharField(
        required=False,
        widget=forms.PasswordInput(render_value=False),
        help_text='Meta App Secret (will be encrypted on save)'
    )
    meta_config_id = forms.CharField(
        required=False,
        max_length=255,
        help_text='Meta Configuration ID for embedded signup'
    )
    meta_business_verification_url = forms.URLField(
        required=False,
        help_text='Meta Business verification URL'
    )
    
    # API Key fields
    api_key_endpoint = forms.URLField(
        required=False,
        help_text='API endpoint for validation requests'
    )
    api_key_header_name = forms.CharField(
        required=False,
        max_length=100,
        help_text='HTTP header name for API key (e.g., "X-API-Key", "Authorization")'
    )
    api_key_format_hint = forms.CharField(
        required=False,
        max_length=255,
        help_text='Format hint to display to users (e.g., "sk-xxxxx...")'
    )
    
    # Rate limit fields
    rate_limit_messages_per_minute = forms.IntegerField(
        required=False,
        min_value=1,
        max_value=1000,
        help_text='Maximum messages per minute (default: 20)'
    )
    rate_limit_requests_per_minute = forms.IntegerField(
        required=False,
        min_value=1,
        max_value=10000,
        help_text='Maximum requests per minute (default: 100)'
    )
    rate_limit_burst_limit = forms.IntegerField(
        required=False,
        min_value=1,
        max_value=100,
        help_text='Maximum burst requests (default: 5)'
    )
    
    class Meta:
        model = IntegrationTypeModel
        fields = [
            'type',
            'name',
            'icon',
            'brief_description',
            'description',
            'category',
            'auth_type',
            'auth_config',
            'default_permissions',
            'is_active',
            'created_by',
        ]
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        # Pre-populate fields from auth_config JSON
        if self.instance and self.instance.pk:
            auth_config = self.instance.auth_config or {}
            auth_type = self.instance.auth_type
            
            # Populate OAuth fields
            if auth_type == AuthType.OAUTH or auth_type == 'oauth':
                self.fields['oauth_client_id'].initial = auth_config.get('client_id', '')
                self.fields['oauth_authorization_url'].initial = auth_config.get('authorization_url', '')
                self.fields['oauth_token_url'].initial = auth_config.get('token_url', '')
                self.fields['oauth_revoke_url'].initial = auth_config.get('revoke_url', '')
                
                scopes = auth_config.get('scopes', [])
                if isinstance(scopes, list):
                    self.fields['oauth_scopes'].initial = ', '.join(scopes)
                else:
                    self.fields['oauth_scopes'].initial = scopes
            
            # Populate Meta fields
            elif auth_type == AuthType.META or auth_type == 'meta':
                self.fields['meta_app_id'].initial = auth_config.get('app_id', '')
                self.fields['meta_config_id'].initial = auth_config.get('config_id', '')
                self.fields['meta_business_verification_url'].initial = auth_config.get('business_verification_url', '')
            
            # Populate API Key fields
            elif auth_type == AuthType.API_KEY or auth_type == 'api_key':
                self.fields['api_key_endpoint'].initial = auth_config.get('api_endpoint', '')
                self.fields['api_key_header_name'].initial = auth_config.get('authentication_header_name', '')
                self.fields['api_key_format_hint'].initial = auth_config.get('api_key_format_hint', '')
            
            # Populate rate limit fields
            rate_config = obj.get_rate_limit_config()
            self.fields['rate_limit_messages_per_minute'].initial = rate_config.get('messages_per_minute', 20)
            self.fields['rate_limit_requests_per_minute'].initial = rate_config.get('requests_per_minute', 100)
            self.fields['rate_limit_burst_limit'].initial = rate_config.get('burst_limit', 5)
    
    def clean(self):
        """
        Validate required fields based on selected auth_type.
        
        Requirements: 18.6
        """
        cleaned_data = super().clean()
        auth_type = cleaned_data.get('auth_type')
        
        if not auth_type:
            return cleaned_data
        
        # Validate OAuth fields
        if auth_type == AuthType.OAUTH or auth_type == 'oauth':
            required_oauth_fields = {
                'oauth_client_id': 'OAuth Client ID',
                'oauth_authorization_url': 'OAuth Authorization URL',
                'oauth_token_url': 'OAuth Token URL',
                'oauth_scopes': 'OAuth Scopes',
            }
            
            # Only require secret for new instances or if explicitly provided
            if not self.instance.pk or cleaned_data.get('oauth_client_secret'):
                required_oauth_fields['oauth_client_secret'] = 'OAuth Client Secret'
            
            for field, label in required_oauth_fields.items():
                if not cleaned_data.get(field):
                    self.add_error(field, f'{label} is required for OAuth 2.0 authentication')
            
            # Validate HTTPS URLs
            for url_field in ['oauth_authorization_url', 'oauth_token_url', 'oauth_revoke_url']:
                url = cleaned_data.get(url_field)
                if url and not url.startswith('https://'):
                    self.add_error(url_field, 'OAuth URLs must use HTTPS protocol')
        
        # Validate Meta fields
        elif auth_type == AuthType.META or auth_type == 'meta':
            required_meta_fields = {
                'meta_app_id': 'Meta App ID',
                'meta_config_id': 'Meta Config ID',
                'meta_business_verification_url': 'Meta Business Verification URL',
            }
            
            # Only require secret for new instances or if explicitly provided
            if not self.instance.pk or cleaned_data.get('meta_app_secret'):
                required_meta_fields['meta_app_secret'] = 'Meta App Secret'
            
            for field, label in required_meta_fields.items():
                if not cleaned_data.get(field):
                    self.add_error(field, f'{label} is required for Meta Business authentication')
        
        # Validate API Key fields
        elif auth_type == AuthType.API_KEY or auth_type == 'api_key':
            required_api_key_fields = {
                'api_key_endpoint': 'API Endpoint',
                'api_key_header_name': 'API Key Header Name',
            }
            
            for field, label in required_api_key_fields.items():
                if not cleaned_data.get(field):
                    self.add_error(field, f'{label} is required for API Key authentication')
        
        # Validate rate limit fields
        messages_per_min = cleaned_data.get('rate_limit_messages_per_minute')
        requests_per_min = cleaned_data.get('rate_limit_requests_per_minute')
        burst_limit = cleaned_data.get('rate_limit_burst_limit')
        
        if messages_per_min is not None and messages_per_min < 1:
            self.add_error('rate_limit_messages_per_minute', 'Must be at least 1')
        
        if requests_per_min is not None and requests_per_min < 1:
            self.add_error('rate_limit_requests_per_minute', 'Must be at least 1')
        
        if burst_limit is not None and burst_limit < 1:
            self.add_error('rate_limit_burst_limit', 'Must be at least 1')
        
        # Validate that messages_per_minute doesn't exceed requests_per_minute
        if messages_per_min and requests_per_min and messages_per_min > requests_per_min:
            self.add_error(
                'rate_limit_messages_per_minute',
                'Messages per minute cannot exceed requests per minute'
            )
        
        return cleaned_data
    
    def save(self, commit=True):
        """
        Save form and update auth_config based on auth_type.
        
        Requirements: 18.7
        """
        instance = super().save(commit=False)
        auth_type = instance.auth_type
        
        # Initialize auth_config if needed
        if not isinstance(instance.auth_config, dict):
            instance.auth_config = {}
        
        # Save OAuth configuration
        if auth_type == AuthType.OAUTH or auth_type == 'oauth':
            instance.auth_config['client_id'] = self.cleaned_data.get('oauth_client_id', '')
            instance.auth_config['authorization_url'] = self.cleaned_data.get('oauth_authorization_url', '')
            instance.auth_config['token_url'] = self.cleaned_data.get('oauth_token_url', '')
            
            revoke_url = self.cleaned_data.get('oauth_revoke_url', '')
            if revoke_url:
                instance.auth_config['revoke_url'] = revoke_url
            
            # Handle scopes
            scopes_str = self.cleaned_data.get('oauth_scopes', '')
            if scopes_str:
                # Split by comma or newline
                scopes = [s.strip() for s in scopes_str.replace('\n', ',').split(',') if s.strip()]
                instance.auth_config['scopes'] = scopes
            else:
                instance.auth_config['scopes'] = []
            
            # Encrypt and save client secret
            secret = self.cleaned_data.get('oauth_client_secret')
            if secret:
                encrypted = TokenEncryption.encrypt(secret, auth_type='oauth')
                instance.auth_config['client_secret_encrypted'] = base64.b64encode(encrypted).decode()
        
        # Save Meta configuration
        elif auth_type == AuthType.META or auth_type == 'meta':
            instance.auth_config['app_id'] = self.cleaned_data.get('meta_app_id', '')
            instance.auth_config['config_id'] = self.cleaned_data.get('meta_config_id', '')
            instance.auth_config['business_verification_url'] = self.cleaned_data.get('meta_business_verification_url', '')
            
            # Encrypt and save app secret
            secret = self.cleaned_data.get('meta_app_secret')
            if secret:
                encrypted = TokenEncryption.encrypt(secret, auth_type='meta')
                instance.auth_config['app_secret_encrypted'] = base64.b64encode(encrypted).decode()
        
        # Save API Key configuration
        elif auth_type == AuthType.API_KEY or auth_type == 'api_key':
            instance.auth_config['api_endpoint'] = self.cleaned_data.get('api_key_endpoint', '')
            instance.auth_config['authentication_header_name'] = self.cleaned_data.get('api_key_header_name', '')
            
            format_hint = self.cleaned_data.get('api_key_format_hint', '')
            if format_hint:
                instance.auth_config['api_key_format_hint'] = format_hint
        
        # Save rate limit configuration
        if not isinstance(instance.rate_limit_config, dict):
            instance.rate_limit_config = {}
        
        messages_per_min = self.cleaned_data.get('rate_limit_messages_per_minute')
        requests_per_min = self.cleaned_data.get('rate_limit_requests_per_minute')
        burst_limit = self.cleaned_data.get('rate_limit_burst_limit')
        
        if messages_per_min is not None:
            instance.rate_limit_config['messages_per_minute'] = messages_per_min
        
        if requests_per_min is not None:
            instance.rate_limit_config['requests_per_minute'] = requests_per_min
        
        if burst_limit is not None:
            instance.rate_limit_config['burst_limit'] = burst_limit
        
        if commit:
            instance.save()
        
        return instance


@admin.register(IntegrationTypeModel)
class IntegrationTypeAdmin(admin.ModelAdmin):
    """
    Admin configuration for IntegrationType model with multi-auth support.
    
    Requirements: 18.1-18.8
    """
    
    form = IntegrationTypeAdminForm
    
    list_display = [
        'type',
        'name',
        'auth_type_display',
        'category',
        'is_active',
        'installation_count',
        'created_at',
    ]
    
    list_filter = [
        'auth_type',
        'category',
        'is_active',
        'created_at',
    ]
    
    search_fields = [
        'name',
        'type',
        'description',
        'brief_description',
    ]
    
    readonly_fields = [
        'id',
        'created_at',
        'updated_at',
        'installation_count',
        'auth_config_display',
        'rate_limit_config_display',
        'test_authentication_button',
    ]
    
    ordering = ['name']
    
    def get_form(self, request, obj=None, **kwargs):
        """
        Override to ensure custom form fields are properly included.
        """
        form = super().get_form(request, obj, **kwargs)
        return form
    
    def get_queryset(self, request):
        """Annotate queryset with installation count."""
        qs = super().get_queryset(request)
        return qs.annotate(
            _installation_count=Count('installations', distinct=True)
        )
    
    def get_fieldsets(self, request, obj=None):
        """
        Return dynamic fieldsets based on auth_type.
        
        Requirements: 18.2, 18.3, 18.4, 18.5
        """
        # Determine auth_type
        auth_type = AuthType.OAUTH  # Default
        
        if obj and obj.pk:
            auth_type = obj.auth_type
        elif request.method == 'POST' and 'auth_type' in request.POST:
            auth_type = request.POST.get('auth_type')
        elif request.method == 'GET' and 'auth_type' in request.GET:
            auth_type = request.GET.get('auth_type')
        
        # Basic fieldsets (always shown)
        fieldsets = [
            ('Basic Information', {
                'fields': (
                    'type',
                    'name',
                    'icon',
                    'brief_description',
                    'description',
                    'category',
                    'is_active',
                )
            }),
            ('Authentication Type', {
                'fields': ('auth_type',),
                'description': 'Select the authentication method for this integration type.'
            }),
        ]
        
        # Add auth-type-specific fieldsets
        if auth_type == AuthType.OAUTH or auth_type == 'oauth':
            fieldsets.append(
                ('OAuth 2.0 Configuration', {
                    'fields': (
                        'oauth_client_id',
                        'oauth_client_secret',
                        'oauth_authorization_url',
                        'oauth_token_url',
                        'oauth_revoke_url',
                        'oauth_scopes',
                    ),
                    'description': 'Configure OAuth 2.0 settings. Client secret is encrypted on save. '
                                 'All URLs must use HTTPS protocol.'
                })
            )
        elif auth_type == AuthType.META or auth_type == 'meta':
            fieldsets.append(
                ('Meta Business Configuration', {
                    'fields': (
                        'meta_app_id',
                        'meta_app_secret',
                        'meta_config_id',
                        'meta_business_verification_url',
                    ),
                    'description': 'Configure Meta Business API settings for WhatsApp/Instagram. '
                                 'App secret is encrypted on save.'
                })
            )
        elif auth_type == AuthType.API_KEY or auth_type == 'api_key':
            fieldsets.append(
                ('API Key Configuration', {
                    'fields': (
                        'api_key_endpoint',
                        'api_key_header_name',
                        'api_key_format_hint',
                    ),
                    'description': 'Configure API key authentication settings. '
                                 'Users will provide their API key during installation.'
                })
            )
        
        # Add remaining fieldsets
        fieldsets.extend([
            ('Rate Limit Configuration', {
                'fields': (
                    'rate_limit_messages_per_minute',
                    'rate_limit_requests_per_minute',
                    'rate_limit_burst_limit',
                ),
                'description': 'Configure rate limits for this integration type. '
                             'Leave empty to use defaults (messages: 20/min, requests: 100/min, burst: 5). '
                             'Changes apply immediately without restart.'
            }),
            ('Permissions', {
                'fields': ('default_permissions',),
                'classes': ('collapse',),
            }),
            ('Advanced', {
                'fields': (
                    'auth_config_display',
                    'rate_limit_config_display',
                    'test_authentication_button',
                ),
                'classes': ('collapse',),
                'description': 'Advanced configuration and testing tools.'
            }),
            ('Metadata', {
                'fields': (
                    'id',
                    'installation_count',
                    'created_by',
                    'created_at',
                    'updated_at',
                ),
                'classes': ('collapse',),
            }),
        ])
        
        return fieldsets
    
    def auth_type_display(self, obj):
        """
        Display authentication type with colored badge.
        
        Requirements: 18.1
        """
        if not obj:
            return '-'
        
        colors = {
            AuthType.OAUTH: '#2196F3',  # Blue
            AuthType.META: '#4CAF50',   # Green
            AuthType.API_KEY: '#FF9800', # Orange
        }
        
        color = colors.get(obj.auth_type, '#757575')
        label = obj.get_auth_type_display()
        
        return format_html(
            '<span style="background-color: {}; color: white; padding: 3px 8px; '
            'border-radius: 3px; font-weight: bold; font-size: 11px;">{}</span>',
            color,
            label
        )
    auth_type_display.short_description = 'Auth Type'
    auth_type_display.admin_order_field = 'auth_type'
    
    def installation_count(self, obj):
        """Display number of user installations."""
        count = getattr(obj, '_installation_count', 0)
        if count > 0:
            return format_html(
                '<span style="color: green; font-weight: bold;">{}</span>',
                count
            )
        return count
    installation_count.short_description = 'Installations'
    installation_count.admin_order_field = '_installation_count'
    
    def auth_config_display(self, obj):
        """
        Display current auth_config as formatted JSON (read-only).
        
        Masks sensitive fields for security.
        """
        if not obj or not obj.pk:
            return '(empty)'
        
        if not obj.auth_config:
            return '(empty)'
        
        # Create a copy and mask sensitive fields
        config_display = obj.auth_config.copy()
        sensitive_fields = [
            'client_secret_encrypted',
            'app_secret_encrypted',
            'api_key_encrypted'
        ]
        
        for field in sensitive_fields:
            if field in config_display:
                config_display[field] = '***ENCRYPTED***'
        
        import json
        formatted = json.dumps(config_display, indent=2)
        
        return format_html(
            '<pre style="background: #f5f5f5; padding: 10px; '
            'border-radius: 4px; max-width: 600px; overflow-x: auto;">{}</pre>',
            formatted
        )
    auth_config_display.short_description = 'Auth Config (JSON)'
    
    def rate_limit_config_display(self, obj):
        """
        Display current rate_limit_config as formatted JSON (read-only).
        
        Shows configured values and defaults.
        
        Requirements: 26.6
        """
        if not obj or not obj.pk:
            return '(empty)'
        
        # Get rate limit config with defaults
        rate_config = obj.get_rate_limit_config()
        
        import json
        formatted = json.dumps(rate_config, indent=2)
        
        return format_html(
            '<pre style="background: #f5f5f5; padding: 10px; '
            'border-radius: 4px; max-width: 600px; overflow-x: auto;">{}</pre>',
            formatted
        )
    rate_limit_config_display.short_description = 'Rate Limit Config (JSON)'
    
    def test_authentication_button(self, obj):
        """
        Display a button to test authentication configuration.
        
        Requirements: 18.8
        """
        if not obj or not obj.pk:
            return '(Save first to enable testing)'
        
        # Note: Actual test endpoint would need to be implemented
        return mark_safe(
            '<a class="button" href="#" onclick="alert(\'Test authentication feature coming soon!\'); return false;">'
            'Test Authentication</a>'
            '<p style="color: #666; margin-top: 5px; font-size: 11px;">'
            'Validates configuration by attempting a test authentication flow.</p>'
        )
    test_authentication_button.short_description = 'Test Configuration'
    
    def save_model(self, request, obj, form, change):
        """
        Save model and invalidate auth config cache.
        
        Requirements: 22.5
        """
        super().save_model(request, obj, form, change)
        
        # Invalidate auth config cache when integration type is updated
        AuthConfigCache.invalidate(str(obj.id))
        
        import logging
        logger = logging.getLogger(__name__)
        logger.info(
            f'Saved IntegrationType {obj.name} (auth_type={obj.auth_type}), '
            f'invalidated auth config cache'
        )
    
    def delete_model(self, request, obj):
        """
        Delete model and invalidate cache.
        
        Requirements: 22.5
        """
        integration_type_id = str(obj.id)
        
        if obj.installations.exists():
            from django.contrib import messages
            messages.error(
                request,
                f'Cannot delete {obj.name} - it has active installations.'
            )
            return
        
        super().delete_model(request, obj)
        
        # Invalidate auth config cache
        AuthConfigCache.invalidate(integration_type_id)
    
    def has_delete_permission(self, request, obj=None):
        """Prevent deletion if installations exist."""
        if obj and hasattr(obj, '_installation_count'):
            if obj._installation_count > 0:
                return False
        return super().has_delete_permission(request, obj)
    
    # Removed Media class - custom CSS/JS not required for basic functionality


@admin.register(AutomationTemplate)
class AutomationTemplateAdmin(admin.ModelAdmin):
    """
    Admin configuration for AutomationTemplate model.
    
    Requirements: 6.1-6.7
    """
    
    list_display = [
        'name',
        'integration_type',
        'trigger_type',
        'is_enabled_by_default',
        'is_active',
        'created_at',
    ]
    
    list_filter = [
        'integration_type',
        'trigger_type',
        'is_active',
        'is_enabled_by_default',
        'created_at',
    ]
    
    search_fields = [
        'name',
        'description',
        'integration_type__name',
        'integration_type__type',
    ]
    
    readonly_fields = [
        'id',
        'created_at',
        'updated_at',
        'step_count',
    ]
    
    fieldsets = (
        ('Basic Information', {
            'fields': (
                'integration_type',
                'name',
                'description',
                'is_active',
                'is_enabled_by_default',
            )
        }),
        ('Trigger Configuration', {
            'fields': (
                'trigger_type',
                'trigger_config',
            )
        }),
        ('Workflow Steps', {
            'fields': (
                'steps',
                'step_count',
            ),
            'description': 'Define workflow steps as JSON array. Each step must include '
                          'action_type, integration_type_id, and parameters.'
        }),
        ('Metadata', {
            'fields': (
                'id',
                'created_by',
                'created_at',
                'updated_at',
            ),
            'classes': ('collapse',),
        }),
    )
    
    ordering = ['integration_type', 'name']
    
    def step_count(self, obj):
        """Display number of steps in template."""
        if obj:
            steps = obj.get_steps_list()
            return len(steps)
        return 0
    step_count.short_description = 'Number of Steps'


@admin.register(Integration)
class IntegrationAdmin(admin.ModelAdmin):
    """
    Admin configuration for Integration model.
    
    Requirements: 23.1-23.7
    """
    
    list_display = [
        'user',
        'integration_type_name',
        'status_display',
        'health_status_display',
        'token_status',
        'created_at',
    ]
    
    list_filter = [
        'integration_type',
        'is_active',
        'health_status',
        'created_at',
    ]
    
    search_fields = [
        'user__email',
        'user__first_name',
        'user__last_name',
        'integration_type__name',
        'integration_type__type',
        'waba_id',
        'business_id',
    ]
    
    readonly_fields = [
        'id',
        'created_at',
        'updated_at',
        'token_status',
        'token_expiration_info',
        'health_status_display',
        'last_successful_sync_at',
        'consecutive_failures',
        'scopes_display',
        'meta_info_display',
    ]
    
    fieldsets = (
        ('Integration Details', {
            'fields': (
                'user',
                'integration_type',
                'is_active',
            )
        }),
        ('Health Status', {
            'fields': (
                'health_status_display',
                'last_successful_sync_at',
                'consecutive_failures',
            ),
            'description': 'Integration health monitoring information.'
        }),
        ('Token Information', {
            'fields': (
                'token_status',
                'token_expiration_info',
                'token_expires_at',
                'scopes_display',
            ),
            'description': 'OAuth tokens are encrypted and cannot be displayed.'
        }),
        ('Meta-Specific Information', {
            'fields': (
                'meta_info_display',
                'waba_id',
                'phone_number_id',
                'business_id',
            ),
            'classes': ('collapse',),
            'description': 'Meta WhatsApp Business API specific fields.'
        }),
        ('Configuration', {
            'fields': (
                'scopes',
                'permissions',
                'steering_rules',
            ),
            'classes': ('collapse',),
        }),
        ('Metadata', {
            'fields': (
                'id',
                'created_at',
                'updated_at',
            ),
            'classes': ('collapse',),
        }),
    )
    
    actions = ['refresh_tokens_action']
    
    ordering = ['-created_at']
    
    def integration_type_name(self, obj):
        """Display integration type name."""
        if obj and obj.integration_type:
            return obj.integration_type.name
        return '(unknown)'
    integration_type_name.short_description = 'Integration Type'
    integration_type_name.admin_order_field = 'integration_type__name'
    
    def status_display(self, obj):
        """Display integration active status with colored badge."""
        if not obj:
            return '-'
        
        if obj.is_active:
            return format_html(
                '<span style="background-color: #4CAF50; color: white; padding: 3px 8px; '
                'border-radius: 3px; font-weight: bold; font-size: 11px;">Active</span>'
            )
        else:
            return format_html(
                '<span style="background-color: #757575; color: white; padding: 3px 8px; '
                'border-radius: 3px; font-weight: bold; font-size: 11px;">Inactive</span>'
            )
    status_display.short_description = 'Status'
    status_display.admin_order_field = 'is_active'
    
    def health_status_display(self, obj):
        """Display health status with colored badge."""
        if not obj:
            return '-'
        
        colors = {
            'healthy': '#4CAF50',    # Green
            'degraded': '#FF9800',   # Orange
            'disconnected': '#F44336', # Red
        }
        
        color = colors.get(obj.health_status, '#757575')
        label = obj.health_status.title()
        
        return format_html(
            '<span style="background-color: {}; color: white; padding: 3px 8px; '
            'border-radius: 3px; font-weight: bold; font-size: 11px;">{}</span>',
            color,
            label
        )
    health_status_display.short_description = 'Health Status'
    health_status_display.admin_order_field = 'health_status'
    
    def token_status(self, obj):
        """Display token expiration status."""
        if not obj:
            return 'N/A'
        
        if obj.is_token_expired:
            return format_html(
                '<span style="color: red; font-weight: bold;">⚠ Expired</span>'
            )
        elif obj.token_expires_at:
            from django.utils import timezone
            time_remaining = obj.token_expires_at - timezone.now()
            days_remaining = time_remaining.days
            
            if days_remaining < 1:
                color = 'red'
                status = f'Expires in {time_remaining.seconds // 3600}h'
            elif days_remaining < 7:
                color = 'orange'
                status = f'Expires in {days_remaining}d'
            else:
                color = 'green'
                status = f'Valid ({days_remaining}d left)'
            
            return format_html(
                '<span style="color: {}; font-weight: bold;">{}</span>',
                color,
                status
            )
        return 'No expiration'
    token_status.short_description = 'Token Status'
    
    def token_expiration_info(self, obj):
        """Display detailed token expiration information."""
        if not obj:
            return 'N/A'
        
        if not obj.token_expires_at:
            return 'Token does not expire (API Key or long-lived token)'
        
        from django.utils import timezone
        
        if obj.is_token_expired:
            expired_ago = timezone.now() - obj.token_expires_at
            return format_html(
                '<span style="color: red;">Expired {} ago</span>',
                self._format_timedelta(expired_ago)
            )
        else:
            time_remaining = obj.token_expires_at - timezone.now()
            return format_html(
                '<span style="color: green;">Expires in {}</span><br>'
                '<small>Exact time: {}</small>',
                self._format_timedelta(time_remaining),
                obj.token_expires_at.strftime('%Y-%m-%d %H:%M:%S %Z')
            )
    token_expiration_info.short_description = 'Token Expiration Details'
    
    def meta_info_display(self, obj):
        """Display Meta-specific information."""
        if not obj:
            return 'N/A'
        
        if obj.integration_type.auth_type not in ['meta', 'META']:
            return 'Not a Meta integration'
        
        info_parts = []
        
        if obj.waba_id:
            info_parts.append(f'<strong>WABA ID:</strong> {obj.waba_id}')
        if obj.phone_number_id:
            info_parts.append(f'<strong>Phone Number ID:</strong> {obj.phone_number_id}')
        if obj.business_id:
            info_parts.append(f'<strong>Business ID:</strong> {obj.business_id}')
        
        if not info_parts:
            return 'No Meta information available'
        
        return format_html('<br>'.join(info_parts))
    meta_info_display.short_description = 'Meta Information'
    
    def scopes_display(self, obj):
        """Display OAuth scopes as comma-separated list."""
        if obj:
            scopes = obj.get_scopes_list()
            return ', '.join(scopes) if scopes else '(none)'
        return '(none)'
    scopes_display.short_description = 'OAuth Scopes'
    
    def refresh_tokens_action(self, request, queryset):
        """
        Admin action to manually refresh tokens for selected integrations.
        
        Requirements: 23.1-23.7
        """
        from django.contrib import messages
        from .services.integration_refresh_service import IntegrationRefreshService
        
        success_count = 0
        error_count = 0
        errors = []
        
        for integration in queryset:
            try:
                # Only refresh if token is expiring or expired
                if integration.token_expires_at:
                    service = IntegrationRefreshService()
                    result = service.refresh_integration(integration)
                    
                    if result.get('success'):
                        success_count += 1
                    else:
                        error_count += 1
                        errors.append(f"{integration.integration_type.name} for {integration.user.email}: {result.get('error', 'Unknown error')}")
                else:
                    # Skip integrations without expiring tokens
                    pass
            except Exception as e:
                error_count += 1
                errors.append(f"{integration.integration_type.name} for {integration.user.email}: {str(e)}")
        
        # Display results
        if success_count > 0:
            messages.success(request, f'Successfully refreshed {success_count} integration(s).')
        
        if error_count > 0:
            error_message = f'Failed to refresh {error_count} integration(s):\n' + '\n'.join(errors[:5])
            if len(errors) > 5:
                error_message += f'\n... and {len(errors) - 5} more errors'
            messages.error(request, error_message)
        
        if success_count == 0 and error_count == 0:
            messages.info(request, 'No integrations required token refresh.')
    
    refresh_tokens_action.short_description = 'Refresh tokens for selected integrations'
    
    def _format_timedelta(self, td):
        """Format timedelta as human-readable string."""
        days = td.days
        hours = td.seconds // 3600
        minutes = (td.seconds % 3600) // 60
        
        parts = []
        if days > 0:
            parts.append(f'{days}d')
        if hours > 0:
            parts.append(f'{hours}h')
        if minutes > 0 and days == 0:
            parts.append(f'{minutes}m')
        
        return ' '.join(parts) if parts else '< 1m'



@admin.register(WebhookEvent)
class WebhookEventAdmin(admin.ModelAdmin):
    """
    Admin configuration for WebhookEvent model.
    
    Requirements: 22.1-22.7
    """
    
    list_display = [
        'id_short',
        'integration_type_name',
        'integration_user',
        'status_display',
        'processing_time_display',
        'created_at',
    ]
    
    list_filter = [
        'status',
        'integration_type',
        'created_at',
        'processed_at',
    ]
    
    search_fields = [
        'id',
        'integration_type__name',
        'integration__user__email',
        'error_message',
    ]
    
    readonly_fields = [
        'id',
        'integration_type',
        'integration',
        'payload_display',
        'signature',
        'status',
        'error_message',
        'processing_time_display',
        'created_at',
        'updated_at',
        'processed_at',
    ]
    
    fieldsets = (
        ('Webhook Information', {
            'fields': (
                'id',
                'integration_type',
                'integration',
                'status',
                'created_at',
            )
        }),
        ('Processing Details', {
            'fields': (
                'processing_time_display',
                'processed_at',
                'error_message',
            )
        }),
        ('Webhook Data', {
            'fields': (
                'payload_display',
                'signature',
            ),
            'classes': ('collapse',),
            'description': 'Raw webhook payload and signature for verification.'
        }),
        ('Metadata', {
            'fields': (
                'updated_at',
            ),
            'classes': ('collapse',),
        }),
    )
    
    actions = ['retry_failed_webhooks']
    
    ordering = ['-created_at']
    
    def has_add_permission(self, request):
        """Prevent manual creation of webhook events."""
        return False
    
    def has_change_permission(self, request, obj=None):
        """Make webhook events read-only."""
        return False
    
    def id_short(self, obj):
        """Display shortened UUID."""
        if obj:
            return str(obj.id)[:8]
        return '-'
    id_short.short_description = 'ID'
    
    def integration_type_name(self, obj):
        """Display integration type name."""
        if obj and obj.integration_type:
            return obj.integration_type.name
        return '(unknown)'
    integration_type_name.short_description = 'Integration Type'
    integration_type_name.admin_order_field = 'integration_type__name'
    
    def integration_user(self, obj):
        """Display user email if integration is identified."""
        if obj and obj.integration and obj.integration.user:
            return obj.integration.user.email
        return '(unidentified)'
    integration_user.short_description = 'User'
    integration_user.admin_order_field = 'integration__user__email'
    
    def status_display(self, obj):
        """Display webhook status with colored badge."""
        if not obj:
            return '-'
        
        colors = {
            'pending': '#2196F3',     # Blue
            'processing': '#FF9800',  # Orange
            'processed': '#4CAF50',   # Green
            'failed': '#F44336',      # Red
        }
        
        color = colors.get(obj.status, '#757575')
        label = obj.get_status_display()
        
        return format_html(
            '<span style="background-color: {}; color: white; padding: 3px 8px; '
            'border-radius: 3px; font-weight: bold; font-size: 11px;">{}</span>',
            color,
            label
        )
    status_display.short_description = 'Status'
    status_display.admin_order_field = 'status'
    
    def processing_time_display(self, obj):
        """Display webhook processing time."""
        if not obj:
            return 'N/A'
        
        if obj.status == 'pending':
            from django.utils import timezone
            waiting_time = timezone.now() - obj.created_at
            return format_html(
                '<span style="color: orange;">Waiting: {}</span>',
                self._format_timedelta(waiting_time)
            )
        
        if obj.processed_at:
            processing_time = obj.processed_at - obj.created_at
            
            # Color based on processing time
            total_seconds = processing_time.total_seconds()
            if total_seconds < 5:
                color = 'green'
            elif total_seconds < 10:
                color = 'orange'
            else:
                color = 'red'
            
            return format_html(
                '<span style="color: {};">{:.2f}s</span>',
                color,
                total_seconds
            )
        
        return 'Not processed'
    processing_time_display.short_description = 'Processing Time'
    
    def payload_display(self, obj):
        """Display webhook payload as formatted JSON."""
        if not obj or not obj.payload:
            return '(empty)'
        
        import json
        
        try:
            formatted = json.dumps(obj.payload, indent=2, sort_keys=True)
            
            # Truncate if too long
            if len(formatted) > 5000:
                formatted = formatted[:5000] + '\n... (truncated)'
            
            return format_html(
                '<pre style="background: #f5f5f5; padding: 10px; '
                'border-radius: 4px; max-height: 400px; overflow: auto; '
                'font-size: 12px; line-height: 1.4;">{}</pre>',
                formatted
            )
        except Exception as e:
            return format_html(
                '<span style="color: red;">Error formatting payload: {}</span>',
                str(e)
            )
    payload_display.short_description = 'Webhook Payload'
    
    def retry_failed_webhooks(self, request, queryset):
        """
        Admin action to retry failed webhook processing.
        
        Requirements: 22.1-22.7
        """
        from django.contrib import messages
        
        # Filter to only failed webhooks
        failed_webhooks = queryset.filter(status='failed')
        
        if not failed_webhooks.exists():
            messages.warning(request, 'No failed webhooks selected.')
            return
        
        # Import the Celery task
        try:
            from apps.automation.tasks.webhook_tasks import process_incoming_message
            
            retry_count = 0
            for webhook in failed_webhooks:
                # Reset status to pending
                webhook.status = 'pending'
                webhook.error_message = ''
                webhook.save(update_fields=['status', 'error_message', 'updated_at'])
                
                # Re-enqueue the task
                process_incoming_message.delay(str(webhook.id))
                retry_count += 1
            
            messages.success(
                request,
                f'Successfully re-queued {retry_count} webhook(s) for processing.'
            )
        except ImportError:
            messages.error(
                request,
                'Webhook processing task not available. Ensure Celery is configured.'
            )
        except Exception as e:
            messages.error(
                request,
                f'Error retrying webhooks: {str(e)}'
            )
    
    retry_failed_webhooks.short_description = 'Retry failed webhook processing'
    
    def _format_timedelta(self, td):
        """Format timedelta as human-readable string."""
        total_seconds = int(td.total_seconds())
        
        if total_seconds < 60:
            return f'{total_seconds}s'
        elif total_seconds < 3600:
            minutes = total_seconds // 60
            seconds = total_seconds % 60
            return f'{minutes}m {seconds}s'
        else:
            hours = total_seconds // 3600
            minutes = (total_seconds % 3600) // 60
            return f'{hours}h {minutes}m'



@admin.register(Message)
class MessageAdmin(admin.ModelAdmin):
    """
    Admin configuration for Message model.
    
    Requirements: 15.3-15.7
    """
    
    list_display = [
        'id_short',
        'conversation_info',
        'direction_display',
        'status_display',
        'content_preview',
        'retry_info',
        'created_at',
    ]
    
    list_filter = [
        'direction',
        'status',
        'created_at',
        'conversation__integration__integration_type',
    ]
    
    search_fields = [
        'id',
        'content',
        'external_message_id',
        'conversation__external_contact_name',
        'conversation__integration__user__email',
    ]
    
    readonly_fields = [
        'id',
        'conversation',
        'conversation_context',
        'direction',
        'content',
        'status',
        'external_message_id',
        'retry_count',
        'last_retry_at',
        'metadata_display',
        'created_at',
        'updated_at',
    ]
    
    fieldsets = (
        ('Message Information', {
            'fields': (
                'id',
                'conversation',
                'conversation_context',
                'direction',
                'status',
            )
        }),
        ('Content', {
            'fields': (
                'content',
            )
        }),
        ('Delivery Details', {
            'fields': (
                'external_message_id',
                'retry_count',
                'last_retry_at',
            )
        }),
        ('Metadata', {
            'fields': (
                'metadata_display',
                'created_at',
                'updated_at',
            ),
            'classes': ('collapse',),
        }),
    )
    
    actions = ['retry_failed_messages']
    
    ordering = ['-created_at']
    
    def has_add_permission(self, request):
        """Prevent manual creation of messages."""
        return False
    
    def has_change_permission(self, request, obj=None):
        """Make messages read-only."""
        return False
    
    def id_short(self, obj):
        """Display shortened UUID."""
        if obj:
            return str(obj.id)[:8]
        return '-'
    id_short.short_description = 'ID'
    
    def conversation_info(self, obj):
        """Display conversation information."""
        if obj and obj.conversation:
            contact = obj.conversation.external_contact_name or obj.conversation.external_contact_id
            integration = obj.conversation.integration.integration_type.name
            return f'{contact} ({integration})'
        return '(unknown)'
    conversation_info.short_description = 'Conversation'
    conversation_info.admin_order_field = 'conversation__external_contact_name'
    
    def conversation_context(self, obj):
        """Display detailed conversation context."""
        if not obj or not obj.conversation:
            return 'N/A'
        
        conv = obj.conversation
        integration = conv.integration
        
        info_parts = [
            f'<strong>Contact:</strong> {conv.external_contact_name or conv.external_contact_id}',
            f'<strong>Integration:</strong> {integration.integration_type.name}',
            f'<strong>User:</strong> {integration.user.email}',
            f'<strong>Status:</strong> {conv.get_status_display()}',
        ]
        
        if conv.last_message_at:
            info_parts.append(f'<strong>Last Message:</strong> {conv.last_message_at.strftime("%Y-%m-%d %H:%M:%S")}')
        
        # Add link to conversation in admin
        conv_url = reverse('admin:automation_conversation_change', args=[conv.id])
        info_parts.append(f'<a href="{conv_url}">View Conversation</a>')
        
        return format_html('<br>'.join(info_parts))
    conversation_context.short_description = 'Conversation Context'
    
    def direction_display(self, obj):
        """Display message direction with icon."""
        if not obj:
            return '-'
        
        if obj.direction == 'inbound':
            icon = '⬇'
            color = '#2196F3'
            label = 'Inbound'
        else:
            icon = '⬆'
            color = '#4CAF50'
            label = 'Outbound'
        
        return format_html(
            '<span style="color: {}; font-weight: bold;">{} {}</span>',
            color,
            icon,
            label
        )
    direction_display.short_description = 'Direction'
    direction_display.admin_order_field = 'direction'
    
    def status_display(self, obj):
        """Display message status with colored badge."""
        if not obj:
            return '-'
        
        colors = {
            'pending': '#2196F3',    # Blue
            'sent': '#4CAF50',       # Green
            'delivered': '#8BC34A',  # Light Green
            'read': '#CDDC39',       # Lime
            'failed': '#F44336',     # Red
        }
        
        color = colors.get(obj.status, '#757575')
        label = obj.get_status_display()
        
        return format_html(
            '<span style="background-color: {}; color: white; padding: 3px 8px; '
            'border-radius: 3px; font-weight: bold; font-size: 11px;">{}</span>',
            color,
            label
        )
    status_display.short_description = 'Status'
    status_display.admin_order_field = 'status'
    
    def content_preview(self, obj):
        """Display message content preview."""
        if obj and obj.content:
            preview = obj.content[:100]
            if len(obj.content) > 100:
                preview += '...'
            return preview
        return '(empty)'
    content_preview.short_description = 'Content'
    
    def retry_info(self, obj):
        """Display retry count and status."""
        if not obj:
            return '-'
        
        if obj.retry_count == 0:
            return format_html('<span style="color: green;">No retries</span>')
        
        max_retries = 5
        if obj.retry_count >= max_retries:
            color = 'red'
            status = f'{obj.retry_count}/{max_retries} (max)'
        elif obj.retry_count >= 3:
            color = 'orange'
            status = f'{obj.retry_count}/{max_retries}'
        else:
            color = 'blue'
            status = f'{obj.retry_count}/{max_retries}'
        
        result = format_html(
            '<span style="color: {}; font-weight: bold;">{}</span>',
            color,
            status
        )
        
        if obj.last_retry_at:
            result = format_html(
                '{}<br><small>Last: {}</small>',
                result,
                obj.last_retry_at.strftime('%Y-%m-%d %H:%M')
            )
        
        return result
    retry_info.short_description = 'Retry Count'
    retry_info.admin_order_field = 'retry_count'
    
    def metadata_display(self, obj):
        """Display message metadata as formatted JSON."""
        if not obj or not obj.metadata:
            return '(empty)'
        
        import json
        
        try:
            formatted = json.dumps(obj.metadata, indent=2, sort_keys=True)
            
            return format_html(
                '<pre style="background: #f5f5f5; padding: 10px; '
                'border-radius: 4px; max-height: 300px; overflow: auto; '
                'font-size: 12px; line-height: 1.4;">{}</pre>',
                formatted
            )
        except Exception as e:
            return format_html(
                '<span style="color: red;">Error formatting metadata: {}</span>',
                str(e)
            )
    metadata_display.short_description = 'Metadata'
    
    def retry_failed_messages(self, request, queryset):
        """
        Admin action to retry failed message delivery.
        
        Requirements: 15.3-15.7
        """
        from django.contrib import messages as django_messages
        
        # Filter to only failed or pending messages that can be retried
        retryable_messages = queryset.filter(
            status__in=['failed', 'pending'],
            retry_count__lt=5
        )
        
        if not retryable_messages.exists():
            django_messages.warning(request, 'No retryable messages selected.')
            return
        
        # Import the Celery task
        try:
            from apps.automation.tasks.message_tasks import send_outgoing_message
            
            retry_count = 0
            for message in retryable_messages:
                # Reset status to pending if failed
                if message.status == 'failed':
                    message.status = 'pending'
                    message.save(update_fields=['status', 'updated_at'])
                
                # Re-enqueue the task
                send_outgoing_message.delay(str(message.id))
                retry_count += 1
            
            django_messages.success(
                request,
                f'Successfully re-queued {retry_count} message(s) for delivery.'
            )
        except ImportError:
            django_messages.error(
                request,
                'Message delivery task not available. Ensure Celery is configured.'
            )
        except Exception as e:
            django_messages.error(
                request,
                f'Error retrying messages: {str(e)}'
            )
    
    retry_failed_messages.short_description = 'Retry failed message delivery'


@admin.register(Conversation)
class ConversationAdmin(admin.ModelAdmin):
    """
    Admin configuration for Conversation model.
    
    Requirements: 15.1-15.2, 20.1-20.3
    """
    
    list_display = [
        'id_short',
        'integration_info',
        'external_contact_name',
        'status_display',
        'message_count',
        'last_message_at',
    ]
    
    list_filter = [
        'status',
        'integration__integration_type',
        'created_at',
        'last_message_at',
    ]
    
    search_fields = [
        'id',
        'external_contact_id',
        'external_contact_name',
        'integration__user__email',
    ]
    
    readonly_fields = [
        'id',
        'integration',
        'external_contact_id',
        'external_contact_name',
        'status',
        'message_count',
        'unread_count',
        'last_message_at',
        'created_at',
        'updated_at',
    ]
    
    fieldsets = (
        ('Conversation Information', {
            'fields': (
                'id',
                'integration',
                'external_contact_id',
                'external_contact_name',
                'status',
            )
        }),
        ('Statistics', {
            'fields': (
                'message_count',
                'unread_count',
                'last_message_at',
            )
        }),
        ('Metadata', {
            'fields': (
                'created_at',
                'updated_at',
            ),
            'classes': ('collapse',),
        }),
    )
    
    ordering = ['-last_message_at']
    
    def has_add_permission(self, request):
        """Prevent manual creation of conversations."""
        return False
    
    def has_change_permission(self, request, obj=None):
        """Make conversations read-only."""
        return False
    
    def id_short(self, obj):
        """Display shortened UUID."""
        if obj:
            return str(obj.id)[:8]
        return '-'
    id_short.short_description = 'ID'
    
    def integration_info(self, obj):
        """Display integration information."""
        if obj and obj.integration:
            integration = obj.integration
            return f'{integration.integration_type.name} - {integration.user.email}'
        return '(unknown)'
    integration_info.short_description = 'Integration'
    integration_info.admin_order_field = 'integration__integration_type__name'
    
    def status_display(self, obj):
        """Display conversation status with colored badge."""
        if not obj:
            return '-'
        
        colors = {
            'active': '#4CAF50',     # Green
            'archived': '#757575',   # Gray
            'blocked': '#F44336',    # Red
        }
        
        color = colors.get(obj.status, '#757575')
        label = obj.get_status_display()
        
        return format_html(
            '<span style="background-color: {}; color: white; padding: 3px 8px; '
            'border-radius: 3px; font-weight: bold; font-size: 11px;">{}</span>',
            color,
            label
        )
    status_display.short_description = 'Status'
    status_display.admin_order_field = 'status'
    
    def message_count(self, obj):
        """Display total message count."""
        if obj:
            count = obj.messages.count()
            return format_html(
                '<span style="font-weight: bold;">{}</span>',
                count
            )
        return 0
    message_count.short_description = 'Messages'
