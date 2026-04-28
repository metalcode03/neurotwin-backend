"""
Payment transaction models for audit and security.

Tracks all payment webhooks and transactions for security and compliance.
"""

import uuid
from django.db import models
from django.conf import settings
from django.utils import timezone


class PaymentTransaction(models.Model):
    """
    Track all payment transactions for audit and idempotency.
    
    Prevents duplicate processing and provides audit trail.
    """
    
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('processing', 'Processing'),
        ('completed', 'Completed'),
        ('failed', 'Failed'),
        ('duplicate', 'Duplicate'),
    ]
    
    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False
    )
    
    # Transaction identifiers
    tx_ref = models.CharField(
        max_length=255,
        unique=True,
        db_index=True,
        help_text='Flutterwave transaction reference'
    )
    flutterwave_tx_id = models.CharField(
        max_length=255,
        null=True,
        blank=True,
        db_index=True,
        help_text='Flutterwave internal transaction ID'
    )
    
    # User and subscription
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='payment_transactions'
    )
    subscription = models.ForeignKey(
        'subscription.Subscription',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='payment_transactions'
    )
    
    # Payment details
    amount = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        help_text='Payment amount'
    )
    currency = models.CharField(
        max_length=3,
        default='NGN',
        help_text='Currency code (NGN, USD, etc.)'
    )
    tier = models.CharField(
        max_length=20,
        help_text='Target subscription tier'
    )
    
    # Status tracking
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='pending',
        db_index=True
    )
    payment_status = models.CharField(
        max_length=50,
        help_text='Flutterwave payment status'
    )
    
    # Webhook data
    webhook_payload = models.JSONField(
        help_text='Full webhook payload for audit'
    )
    webhook_received_at = models.DateTimeField(
        default=timezone.now,
        help_text='When webhook was received'
    )
    processed_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text='When transaction was processed'
    )
    
    # Security
    ip_address = models.GenericIPAddressField(
        null=True,
        blank=True,
        help_text='IP address of webhook request'
    )
    signature_verified = models.BooleanField(
        default=False,
        help_text='Whether webhook signature was verified'
    )
    
    # Error tracking
    error_message = models.TextField(
        null=True,
        blank=True,
        help_text='Error message if processing failed'
    )
    retry_count = models.IntegerField(
        default=0,
        help_text='Number of processing retries'
    )
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'payment_transactions'
        verbose_name = 'payment transaction'
        verbose_name_plural = 'payment transactions'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['user', '-created_at']),
            models.Index(fields=['status', '-created_at']),
            models.Index(fields=['tx_ref']),
            models.Index(fields=['flutterwave_tx_id']),
        ]
    
    def __str__(self) -> str:
        return f"{self.tx_ref} - {self.user.email} - {self.status}"
    
    def mark_processing(self):
        """Mark transaction as being processed."""
        self.status = 'processing'
        self.save(update_fields=['status', 'updated_at'])
    
    def mark_completed(self, subscription=None):
        """Mark transaction as completed."""
        self.status = 'completed'
        self.processed_at = timezone.now()
        if subscription:
            self.subscription = subscription
        self.save(update_fields=['status', 'processed_at', 'subscription', 'updated_at'])
    
    def mark_failed(self, error_message: str):
        """Mark transaction as failed."""
        self.status = 'failed'
        self.error_message = error_message
        self.processed_at = timezone.now()
        self.save(update_fields=['status', 'error_message', 'processed_at', 'updated_at'])
    
    def mark_duplicate(self):
        """Mark transaction as duplicate."""
        self.status = 'duplicate'
        self.processed_at = timezone.now()
        self.save(update_fields=['status', 'processed_at', 'updated_at'])


class WebhookLog(models.Model):
    """
    Log all webhook requests for security monitoring.
    
    Tracks all webhook attempts including failed/malicious ones.
    """
    
    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False
    )
    
    # Request details
    event_type = models.CharField(
        max_length=100,
        db_index=True,
        help_text='Webhook event type'
    )
    payload = models.JSONField(
        help_text='Full webhook payload'
    )
    headers = models.JSONField(
        help_text='Request headers'
    )
    
    # Security
    ip_address = models.GenericIPAddressField(
        help_text='IP address of request'
    )
    signature_provided = models.CharField(
        max_length=255,
        null=True,
        blank=True,
        help_text='Signature from webhook'
    )
    signature_valid = models.BooleanField(
        default=False,
        help_text='Whether signature was valid'
    )
    
    # Processing
    processed = models.BooleanField(
        default=False,
        help_text='Whether webhook was processed'
    )
    response_status = models.IntegerField(
        help_text='HTTP response status code'
    )
    error_message = models.TextField(
        null=True,
        blank=True,
        help_text='Error message if processing failed'
    )
    
    # Related transaction
    transaction = models.ForeignKey(
        PaymentTransaction,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='webhook_logs'
    )
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    
    class Meta:
        db_table = 'webhook_logs'
        verbose_name = 'webhook log'
        verbose_name_plural = 'webhook logs'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['-created_at']),
            models.Index(fields=['event_type', '-created_at']),
            models.Index(fields=['ip_address', '-created_at']),
            models.Index(fields=['signature_valid', '-created_at']),
        ]
    
    def __str__(self) -> str:
        return f"{self.event_type} - {self.ip_address} - {self.created_at}"
