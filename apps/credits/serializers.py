"""
Serializers for credit management API endpoints.

Requirements: 13.1, 13.2
"""

from rest_framework import serializers
from apps.credits.models import CreditUsageLog
from apps.credits.enums import BrainMode, OperationType


class CreditBalanceSerializer(serializers.Serializer):
    """
    Serializer for credit balance response.
    
    Requirements: 1.10, 4.5
    """
    monthly_credits = serializers.IntegerField(
        help_text="Monthly credit allocation based on subscription tier"
    )
    remaining_credits = serializers.IntegerField(
        help_text="Current available credits"
    )
    used_credits = serializers.IntegerField(
        help_text="Credits consumed this billing period"
    )
    purchased_credits = serializers.IntegerField(
        help_text="Additional credits purchased"
    )
    last_reset_date = serializers.DateField(
        help_text="Last date credits were reset"
    )
    next_reset_date = serializers.DateField(
        help_text="Next date credits will be reset"
    )
    days_until_reset = serializers.IntegerField(
        help_text="Days until next reset"
    )
    usage_percentage = serializers.FloatField(
        help_text="Percentage of credits used"
    )


class CreditEstimateRequestSerializer(serializers.Serializer):
    """
    Serializer for credit estimate request parameters.
    
    Requirements: 4.5
    """
    operation_type = serializers.ChoiceField(
        choices=[
            ('simple_response', 'Simple Response'),
            ('long_response', 'Long Response'),
            ('summarization', 'Summarization'),
            ('complex_reasoning', 'Complex Reasoning'),
            ('automation', 'Automation'),
        ],
        required=True,
        help_text="Type of AI operation"
    )
    brain_mode = serializers.ChoiceField(
        choices=[
            ('brain', 'Brain'),
            ('brain_pro', 'Brain Pro'),
            ('brain_gen', 'Brain Gen'),
        ],
        required=True,
        help_text="Brain intelligence level"
    )
    estimated_tokens = serializers.IntegerField(
        default=500,
        min_value=1,
        max_value=100000,
        help_text="Estimated number of tokens"
    )
    
    def validate_operation_type(self, value):
        """Validate operation_type against enum."""
        try:
            OperationType(value)
        except ValueError:
            raise serializers.ValidationError(
                f"Invalid operation_type. Must be one of: {', '.join([e.value for e in OperationType])}"
            )
        return value
    
    def validate_brain_mode(self, value):
        """Validate brain_mode against enum."""
        try:
            BrainMode(value)
        except ValueError:
            raise serializers.ValidationError(
                f"Invalid brain_mode. Must be one of: {', '.join([e.value for e in BrainMode])}"
            )
        return value


class CreditEstimateSerializer(serializers.Serializer):
    """
    Serializer for credit estimate response.
    
    Requirements: 4.5
    """
    estimated_cost = serializers.IntegerField(
        help_text="Estimated credit cost for the operation"
    )
    operation_type = serializers.CharField(
        help_text="Type of AI operation"
    )
    brain_mode = serializers.CharField(
        help_text="Brain intelligence level"
    )
    estimated_tokens = serializers.IntegerField(
        help_text="Estimated number of tokens"
    )
    sufficient_credits = serializers.BooleanField(
        help_text="Whether user has sufficient credits"
    )
    remaining_credits = serializers.IntegerField(
        help_text="User's remaining credit balance"
    )


class CreditUsageLogSerializer(serializers.ModelSerializer):
    """
    Serializer for credit usage log records.
    
    Requirements: 10.3
    """
    timestamp = serializers.DateTimeField(
        format='%Y-%m-%dT%H:%M:%SZ',
        help_text="Timestamp of credit consumption"
    )
    
    class Meta:
        model = CreditUsageLog
        fields = [
            'id',
            'timestamp',
            'credits_consumed',
            'operation_type',
            'brain_mode',
            'model_used',
            'request_id',
        ]
        read_only_fields = fields


class CreditUsageHistoryRequestSerializer(serializers.Serializer):
    """
    Serializer for credit usage history request parameters.
    
    Requirements: 10.3, 10.4, 10.5, 10.6
    """
    page = serializers.IntegerField(
        default=1,
        min_value=1,
        help_text="Page number"
    )
    page_size = serializers.IntegerField(
        default=20,
        min_value=1,
        max_value=100,
        help_text="Number of records per page"
    )
    start_date = serializers.DateTimeField(
        required=False,
        help_text="Filter from date (ISO 8601)"
    )
    end_date = serializers.DateTimeField(
        required=False,
        help_text="Filter to date (ISO 8601)"
    )
    operation_type = serializers.ChoiceField(
        choices=[
            ('simple_response', 'Simple Response'),
            ('long_response', 'Long Response'),
            ('summarization', 'Summarization'),
            ('complex_reasoning', 'Complex Reasoning'),
            ('automation', 'Automation'),
        ],
        required=False,
        help_text="Filter by operation type"
    )
    brain_mode = serializers.ChoiceField(
        choices=[
            ('brain', 'Brain'),
            ('brain_pro', 'Brain Pro'),
            ('brain_gen', 'Brain Gen'),
        ],
        required=False,
        help_text="Filter by brain mode"
    )


class CreditUsageHistorySerializer(serializers.Serializer):
    """
    Serializer for paginated credit usage history response.
    
    Requirements: 10.3, 10.6
    """
    count = serializers.IntegerField(
        help_text="Total number of records"
    )
    next = serializers.CharField(
        allow_null=True,
        help_text="URL to next page"
    )
    previous = serializers.CharField(
        allow_null=True,
        help_text="URL to previous page"
    )
    results = CreditUsageLogSerializer(
        many=True,
        help_text="Usage log records"
    )
    summary = serializers.DictField(
        help_text="Summary statistics"
    )


class CreditUsageSummaryRequestSerializer(serializers.Serializer):
    """
    Serializer for credit usage summary request parameters.
    
    Requirements: 10.7, 10.8
    """
    days = serializers.IntegerField(
        default=30,
        min_value=1,
        max_value=365,
        help_text="Number of days to include in summary"
    )


class DailyBreakdownSerializer(serializers.Serializer):
    """Serializer for daily breakdown item."""
    date = serializers.DateField()
    credits = serializers.IntegerField()
    requests = serializers.IntegerField()


class PeriodSerializer(serializers.Serializer):
    """Serializer for period information."""
    start_date = serializers.DateField()
    end_date = serializers.DateField()
    days = serializers.IntegerField()


class CreditUsageSummarySerializer(serializers.Serializer):
    """
    Serializer for aggregated credit usage summary.
    
    Requirements: 10.7, 10.8
    """
    period = PeriodSerializer(
        help_text="Period information"
    )
    total_credits_consumed = serializers.IntegerField(
        help_text="Total credits consumed in period"
    )
    daily_breakdown = DailyBreakdownSerializer(
        many=True,
        help_text="Daily credit consumption breakdown"
    )
    by_operation_type = serializers.DictField(
        help_text="Breakdown by operation type"
    )
    by_brain_mode = serializers.DictField(
        help_text="Breakdown by brain mode"
    )


# Admin serializers

class AIRequestLogSerializer(serializers.Serializer):
    """
    Serializer for AI request log records (admin view).
    
    Requirements: 11.5, 11.6, 11.7
    """
    id = serializers.UUIDField()
    user_id = serializers.IntegerField()
    timestamp = serializers.DateTimeField(format='%Y-%m-%dT%H:%M:%SZ')
    brain_mode = serializers.CharField()
    operation_type = serializers.CharField()
    model_used = serializers.CharField()
    prompt_length = serializers.IntegerField()
    response_length = serializers.IntegerField(allow_null=True)
    tokens_used = serializers.IntegerField(allow_null=True)
    credits_consumed = serializers.IntegerField(allow_null=True)
    latency_ms = serializers.IntegerField(allow_null=True)
    status = serializers.CharField()
    error_message = serializers.CharField(allow_null=True)
    error_type = serializers.CharField(allow_null=True)
    cognitive_blend_value = serializers.IntegerField(allow_null=True)


class BrainRoutingConfigSerializer(serializers.Serializer):
    """
    Serializer for Brain routing configuration.
    
    Requirements: 6.9, 21.1-21.10
    """
    id = serializers.IntegerField(read_only=True)
    config_name = serializers.CharField(
        max_length=100,
        help_text="Unique name for this configuration"
    )
    routing_rules = serializers.JSONField(
        help_text="JSON mapping of brain_mode -> operation_type -> model"
    )
    is_active = serializers.BooleanField(
        default=False,
        help_text="Whether this configuration is currently active"
    )
    created_by = serializers.IntegerField(
        read_only=True,
        help_text="User ID of creator"
    )
    created_at = serializers.DateTimeField(
        read_only=True,
        format='%Y-%m-%dT%H:%M:%SZ'
    )
    updated_at = serializers.DateTimeField(
        read_only=True,
        format='%Y-%m-%dT%H:%M:%SZ'
    )
    
    def validate_routing_rules(self, value):
        """
        Validate routing rules structure.
        
        Requirements: 21.2, 21.3
        """
        if not isinstance(value, dict):
            raise serializers.ValidationError("routing_rules must be a JSON object")
        
        # Validate required brain modes
        required_modes = ['brain', 'brain_pro', 'brain_gen']
        for mode in required_modes:
            if mode not in value:
                raise serializers.ValidationError(f"Missing required brain_mode: {mode}")
        
        # Validate operation types for each brain mode
        required_operations = [
            'simple_response',
            'long_response',
            'summarization',
            'complex_reasoning',
            'automation'
        ]
        
        for mode, operations in value.items():
            if not isinstance(operations, dict):
                raise serializers.ValidationError(
                    f"Operations for {mode} must be a JSON object"
                )
            
            for operation in required_operations:
                if operation not in operations:
                    raise serializers.ValidationError(
                        f"Missing required operation_type '{operation}' for brain_mode '{mode}'"
                    )
                
                # Validate model reference exists
                model = operations[operation]
                if not isinstance(model, str):
                    raise serializers.ValidationError(
                        f"Model for {mode}.{operation} must be a string"
                    )
        
        return value
    
    def validate_config_name(self, value):
        """Validate config_name is unique."""
        from apps.credits.models import BrainRoutingConfig
        
        # Check if config_name already exists (excluding current instance on update)
        instance = self.instance
        queryset = BrainRoutingConfig.objects.filter(config_name=value)
        
        if instance:
            queryset = queryset.exclude(pk=instance.pk)
        
        if queryset.exists():
            raise serializers.ValidationError(
                f"Configuration with name '{value}' already exists"
            )
        
        return value


class HealthCheckSerializer(serializers.Serializer):
    """
    Serializer for health check response.
    
    Requirements: 23.10
    """
    status = serializers.ChoiceField(
        choices=['healthy', 'degraded', 'unhealthy'],
        help_text="Overall system health status"
    )
    timestamp = serializers.DateTimeField(
        help_text="Timestamp of health check"
    )
    components = serializers.DictField(
        help_text="Status of individual components"
    )
    metrics = serializers.DictField(
        help_text="Performance metrics"
    )


# Payment Serializers

class PaymentInitiateSerializer(serializers.Serializer):
    """
    Serializer for initiating a Flutterwave payment.
    """
    tier = serializers.ChoiceField(
        choices=['free', 'pro', 'twin_plus', 'executive'],
        required=False,
        help_text="Subscription tier to upgrade to"
    )
    topup_package = serializers.ChoiceField(
        choices=['small', 'medium', 'large'],
        required=False,
        help_text="Credit top-up package to purchase"
    )

    def validate(self, attrs):
        if not attrs.get('tier') and not attrs.get('topup_package'):
            raise serializers.ValidationError("Either tier or topup_package must be provided.")
        if attrs.get('tier') and attrs.get('topup_package'):
            raise serializers.ValidationError("Cannot provide both tier and topup_package.")
        return attrs


class PaymentVerifySerializer(serializers.Serializer):
    """
    Serializer for verifying a Flutterwave payment.
    """
    transaction_id = serializers.CharField(
        required=True,
        help_text="Flutterwave transaction ID to verify"
    )
    tier = serializers.ChoiceField(
        choices=['free', 'pro', 'twin_plus', 'executive'],
        required=False
    )
    topup_package = serializers.ChoiceField(
        choices=['small', 'medium', 'large'],
        required=False
    )

    def validate(self, attrs):
        if not (attrs.get('tier') or attrs.get('topup_package')):
            raise serializers.ValidationError("Either tier or topup_package must be provided for verification routing.")
        return attrs


class PaymentResponseSerializer(serializers.Serializer):
    """
    Serializer for payment initialization response.
    """
    tx_ref = serializers.CharField()
    amount = serializers.DecimalField(max_digits=10, decimal_places=2)
    currency = serializers.CharField(default="USD")
    public_key = serializers.CharField()
    customer_email = serializers.EmailField()
    customer_name = serializers.CharField()
