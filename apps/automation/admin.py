"""
Django admin configuration for automation app.
"""

from django import forms
from django.contrib import admin
from django.db.models import Count
from django.utils.html import format_html

from .models import (
    AutomationTemplate,
    Integration,
    IntegrationTypeModel,
)


class OAuthConfigForm(forms.ModelForm):
    """Custom form for OAuth configuration with separate secret field."""
    
    oauth_client_secret = forms.CharField(
        required=False,
        widget=forms.PasswordInput(render_value=False),
        help_text='OAuth client secret (will be encrypted on save)'
    )
    
    class Meta:
        model = IntegrationTypeModel
        fields = '__all__'
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Pre-populate OAuth fields from oauth_config JSON
        if self.instance and self.instance.pk:
            oauth_config = self.instance.oauth_config or {}
            self.fields['oauth_client_secret'].initial = ''  # Never show secret
    
    def save(self, commit=True):
        instance = super().save(commit=False)
        
        # Handle OAuth client secret encryption
        secret = self.cleaned_data.get('oauth_client_secret')
        if secret:
            instance.set_oauth_client_secret(secret)
        
        if commit:
            instance.save()
        return instance


@admin.register(IntegrationTypeModel)
class IntegrationTypeAdmin(admin.ModelAdmin):
    """
    Admin configuration for IntegrationType model.
    
    Requirements: 1.1-1.7
    """
    
    form = OAuthConfigForm
    
    list_display = [
        'type',
        'name',
        'category',
        'is_active',
        'installation_count',
        'created_at',
    ]
    
    list_filter = [
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
        'oauth_client_id_display',
    ]
    
    fieldsets = (
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
        ('OAuth Configuration', {
            'fields': (
                'oauth_client_id_display',
                'oauth_client_secret',
                'oauth_config',
            ),
            'description': 'Configure OAuth 2.0 settings. Client secret is encrypted on save.'
        }),
        ('Permissions', {
            'fields': ('default_permissions',),
            'classes': ('collapse',),
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
    )
    
    ordering = ['name']
    
    def get_queryset(self, request):
        """Annotate queryset with installation count."""
        qs = super().get_queryset(request)
        return qs.annotate(
            _installation_count=Count('installations', distinct=True)
        )
    
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
    
    def oauth_client_id_display(self, obj):
        """Display OAuth client ID (read-only)."""
        if obj and obj.oauth_config:
            return obj.oauth_config.get('client_id', '(not set)')
        return '(not set)'
    oauth_client_id_display.short_description = 'OAuth Client ID'
    
    def has_delete_permission(self, request, obj=None):
        """Prevent deletion if installations exist."""
        if obj and hasattr(obj, '_installation_count'):
            if obj._installation_count > 0:
                return False
        return super().has_delete_permission(request, obj)
    
    def delete_model(self, request, obj):
        """Additional check before deletion."""
        if obj.installations.exists():
            from django.contrib import messages
            messages.error(
                request,
                f'Cannot delete {obj.name} - it has active installations.'
            )
            return
        super().delete_model(request, obj)


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
    
    Requirements: 5.1-5.7
    """
    
    list_display = [
        'user',
        'integration_type_name',
        'is_active',
        'token_status',
        'created_at',
    ]
    
    list_filter = [
        'integration_type',
        'is_active',
        'created_at',
    ]
    
    search_fields = [
        'user__email',
        'user__first_name',
        'user__last_name',
        'integration_type__name',
        'integration_type__type',
    ]
    
    readonly_fields = [
        'id',
        'created_at',
        'updated_at',
        'token_status',
        'scopes_display',
    ]
    
    fieldsets = (
        ('Integration Details', {
            'fields': (
                'user',
                'integration_type',
                'is_active',
            )
        }),
        ('OAuth Information', {
            'fields': (
                'token_status',
                'token_expires_at',
                'scopes_display',
            ),
            'description': 'OAuth tokens are encrypted and cannot be displayed.'
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
    
    ordering = ['-created_at']
    
    def integration_type_name(self, obj):
        """Display integration type name."""
        if obj and obj.integration_type:
            return obj.integration_type.name
        return '(unknown)'
    integration_type_name.short_description = 'Integration Type'
    integration_type_name.admin_order_field = 'integration_type__name'
    
    def token_status(self, obj):
        """Display token expiration status."""
        if not obj:
            return 'N/A'
        
        if obj.is_token_expired():
            return format_html(
                '<span style="color: red; font-weight: bold;">Expired</span>'
            )
        elif obj.token_expires_at:
            return format_html(
                '<span style="color: green;">Valid until {}</span>',
                obj.token_expires_at.strftime('%Y-%m-%d %H:%M')
            )
        return 'No expiration'
    token_status.short_description = 'Token Status'
    
    def scopes_display(self, obj):
        """Display OAuth scopes as comma-separated list."""
        if obj:
            scopes = obj.get_scopes_list()
            return ', '.join(scopes) if scopes else '(none)'
        return '(none)'
    scopes_display.short_description = 'OAuth Scopes'
