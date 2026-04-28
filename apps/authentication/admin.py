"""Admin configuration for authentication models."""

from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from unfold.admin import ModelAdmin as UnfoldModelAdmin
from unfold.decorators import display

from .models import User, VerificationToken, PasswordResetToken


@admin.register(User)
class UserAdmin(UnfoldModelAdmin, BaseUserAdmin):
    """Admin configuration for User model."""
    
    list_display = ('email', 'display_is_verified', 'display_is_active', 'is_staff', 'created_at')
    list_filter = ('is_verified', 'is_active', 'is_staff', 'oauth_provider')
    search_fields = ('email',)
    ordering = ('-created_at',)
    
    fieldsets = (
        (None, {'fields': ('email', 'password')}),
        ('OAuth', {'fields': ('oauth_provider', 'oauth_id')}),
        ('Status', {'fields': ('is_verified', 'is_active', 'is_staff', 'is_superuser')}),
        ('Permissions', {'fields': ('groups', 'user_permissions')}),
        ('Timestamps', {'fields': ('created_at', 'updated_at')}),
    )
    
    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': ('email', 'password1', 'password2'),
        }),
    )
    
    readonly_fields = ('created_at', 'updated_at')

    @display(
        description="Verified",
        label={
            True: "success",
            False: "danger",
        },
    )
    def display_is_verified(self, obj):
        return obj.is_verified

    @display(
        description="Active",
        label={
            True: "success",
            False: "danger",
        },
    )
    def display_is_active(self, obj):
        return obj.is_active


@admin.register(VerificationToken)
class VerificationTokenAdmin(UnfoldModelAdmin):
    """Admin configuration for VerificationToken model."""
    
    list_display = ('user', 'is_used', 'expires_at', 'created_at')
    list_filter = ('is_used', 'created_at')
    search_fields = ('user__email',)
    ordering = ('-created_at',)


@admin.register(PasswordResetToken)
class PasswordResetTokenAdmin(UnfoldModelAdmin):
    """Admin configuration for PasswordResetToken model."""
    
    list_display = ('user', 'is_used', 'expires_at', 'created_at')
    list_filter = ('is_used', 'created_at')
    search_fields = ('user__email',)
    ordering = ('-created_at',)
