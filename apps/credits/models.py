"""
Credit system models for NeuroTwin platform.

Defines models for credit tracking, usage logging, AI request logging,
routing configuration, and credit top-ups.

Requirements: 16.1-16.10
"""

import uuid
from django.db import models
from django.conf import settings
from django.core.exceptions import ValidationError


class UserCredits(models.Model):
    """
    Tracks credit balance and usage for each user.
    
    Requirements: 16.1, 16.2, 16.3
    """
    
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='credits',
        help_text='The user this credit record belongs to'
    )
    monthly_credits = models.IntegerField(
        help_text='Monthly credit allocation based on subscription tier'
    )
    remaining_credits = models.IntegerField(
        help_text='Current available credits'
    )
    used_credits = models.IntegerField(
        default=0,
        help_text='Credits consumed this billing period'
    )
    purchased_credits = models.IntegerField(
        default=0,
        help_text='Additional credits purchased (future feature)'
    )
    last_reset_date = models.DateField(
        help_text='Last date credits were reset'
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'user_credits'
        verbose_name = 'User Credits'
        verbose_name_plural = 'User Credits'
        indexes = [
            models.Index(fields=['user']),
            models.Index(fields=['last_reset_date']),
        ]
    
    def __str__(self) -> str:
        return f"Credits for {self.user.email}: {self.remaining_credits}/{self.monthly_credits}"


class CreditUsageLog(models.Model):
    """
    Audit log of credit consumption.
    
    Requirements: 16.4, 16.5, 16.6
    """
    
    OPERATION_TYPE_CHOICES = [
        ('simple_response', 'Simple Response'),
        ('long_response', 'Long Response'),
        ('summarization', 'Summarization'),
        ('complex_reasoning', 'Complex Reasoning'),
        ('automation', 'Automation'),
    ]
    
    BRAIN_MODE_CHOICES = [
        ('brain', 'Brain'),
        ('brain_pro', 'Brain Pro'),
        ('brain_gen', 'Brain Gen'),
    ]
    
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='credit_usage_logs',
        help_text='User who consumed the credits'
    )
    timestamp = models.DateTimeField(
        auto_now_add=True,
        db_index=True,
        help_text='When the credits were consumed'
    )
    credits_consumed = models.IntegerField(
        help_text='Number of credits consumed'
    )
    operation_type = models.CharField(
        max_length=50,
        choices=OPERATION_TYPE_CHOICES,
        help_text='Type of operation performed'
    )
    brain_mode = models.CharField(
        max_length=20,
        choices=BRAIN_MODE_CHOICES,
        help_text='Brain mode used for the request'
    )
    model_used = models.CharField(
        max_length=50,
        help_text='AI model that processed the request'
    )
    request_id = models.UUIDField(
        null=True,
        blank=True,
        help_text='UUID of the associated AI request'
    )
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'credit_usage_log'
        verbose_name = 'Credit Usage Log'
        verbose_name_plural = 'Credit Usage Logs'
        ordering = ['-timestamp']
        indexes = [
            models.Index(fields=['user', 'timestamp']),
            models.Index(fields=['user', 'operation_type']),
            models.Index(fields=['user', 'brain_mode']),
        ]
    
    def __str__(self) -> str:
        return f"{self.user.email} - {self.credits_consumed} credits ({self.operation_type})"


class AIRequestLog(models.Model):
    """
    Comprehensive audit log of AI requests.
    
    Requirements: 16.7, 16.8, 16.9
    """
    
    STATUS_CHOICES = [
        ('success', 'Success'),
        ('failed', 'Failed'),
        ('insufficient_credits', 'Insufficient Credits'),
        ('model_error', 'Model Error'),
    ]
    
    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='ai_request_logs',
        help_text='User who made the request'
    )
    timestamp = models.DateTimeField(
        auto_now_add=True,
        db_index=True,
        help_text='When the request was made'
    )
    brain_mode = models.CharField(
        max_length=20,
        help_text='Brain mode used for the request'
    )
    operation_type = models.CharField(
        max_length=50,
        help_text='Type of operation performed'
    )
    model_used = models.CharField(
        max_length=50,
        help_text='AI model that processed the request'
    )
    prompt_length = models.IntegerField(
        help_text='Length of the prompt in characters'
    )
    response_length = models.IntegerField(
        null=True,
        blank=True,
        help_text='Length of the response in characters'
    )
    tokens_used = models.IntegerField(
        null=True,
        blank=True,
        help_text='Number of tokens consumed'
    )
    credits_consumed = models.IntegerField(
        null=True,
        blank=True,
        help_text='Number of credits consumed'
    )
    latency_ms = models.IntegerField(
        null=True,
        blank=True,
        help_text='Request latency in milliseconds'
    )
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        db_index=True,
        help_text='Status of the request'
    )
    error_message = models.TextField(
        null=True,
        blank=True,
        help_text='Error message if request failed'
    )
    error_type = models.CharField(
        max_length=100,
        null=True,
        blank=True,
        help_text='Type of error that occurred'
    )
    cognitive_blend_value = models.IntegerField(
        null=True,
        blank=True,
        help_text='Cognitive blend value at time of request'
    )
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'ai_request_log'
        verbose_name = 'AI Request Log'
        verbose_name_plural = 'AI Request Logs'
        ordering = ['-timestamp']
        indexes = [
            models.Index(fields=['user', 'timestamp']),
            models.Index(fields=['user', 'status']),
            models.Index(fields=['model_used', 'timestamp']),
        ]
    
    def __str__(self) -> str:
        return f"{self.user.email} - {self.brain_mode} ({self.status})"


class BrainRoutingConfig(models.Model):
    """
    Stores routing configuration for Brain modes.
    
    Requirements: 6.9
    """
    
    config_name = models.CharField(
        max_length=100,
        unique=True,
        help_text='Unique name for this configuration'
    )
    routing_rules = models.JSONField(
        help_text='JSON mapping of brain_mode -> operation_type -> model'
    )
    is_active = models.BooleanField(
        default=False,
        help_text='Whether this configuration is currently active'
    )
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        help_text='Admin user who created this configuration'
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'brain_routing_config'
        verbose_name = 'Brain Routing Config'
        verbose_name_plural = 'Brain Routing Configs'
    
    def clean(self):
        """Validate routing_rules JSON structure."""
        if not isinstance(self.routing_rules, dict):
            raise ValidationError('routing_rules must be a JSON object')
        
        # Validate structure: brain_mode -> operation_type -> model
        valid_brain_modes = ['brain', 'brain_pro', 'brain_gen']
        valid_operation_types = [
            'simple_response', 'long_response', 'summarization',
            'complex_reasoning', 'automation'
        ]
        
        for brain_mode, operations in self.routing_rules.items():
            if brain_mode not in valid_brain_modes:
                raise ValidationError(f'Invalid brain_mode: {brain_mode}')
            
            if not isinstance(operations, dict):
                raise ValidationError(
                    f'Operations for {brain_mode} must be a JSON object'
                )
            
            for operation_type, model in operations.items():
                if operation_type not in valid_operation_types:
                    raise ValidationError(
                        f'Invalid operation_type: {operation_type}'
                    )
                
                if not isinstance(model, str):
                    raise ValidationError(
                        f'Model for {brain_mode}.{operation_type} must be a string'
                    )
    
    def save(self, *args, **kwargs):
        """Run validation before saving."""
        self.clean()
        super().save(*args, **kwargs)
    
    def __str__(self) -> str:
        status = 'active' if self.is_active else 'inactive'
        return f"{self.config_name} ({status})"


class CreditTopUp(models.Model):
    """
    Records credit purchases (future feature).
    
    Requirements: 17.4, 17.5, 17.6
    """
    
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('completed', 'Completed'),
        ('failed', 'Failed'),
        ('refunded', 'Refunded'),
    ]
    
    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='credit_topups',
        help_text='User who purchased the credits'
    )
    amount = models.IntegerField(
        help_text='Number of credits purchased'
    )
    price_paid = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        help_text='Price paid in currency'
    )
    payment_method = models.CharField(
        max_length=50,
        help_text='Payment method used'
    )
    transaction_id = models.CharField(
        max_length=255,
        unique=True,
        help_text='Unique transaction identifier'
    )
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        help_text='Status of the transaction'
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'credit_topup'
        verbose_name = 'Credit Top-Up'
        verbose_name_plural = 'Credit Top-Ups'
        indexes = [
            models.Index(fields=['user', 'created_at']),
            models.Index(fields=['transaction_id']),
        ]
    
    def __str__(self) -> str:
        return f"{self.user.email} - {self.amount} credits ({self.status})"
