"""
Base serializers for NeuroTwin REST API.

Provides common serializer functionality and mixins.
Requirements: 13.2 - JSON request/response bodies
"""

from rest_framework import serializers


class BaseModelSerializer(serializers.ModelSerializer):
    """
    Base model serializer with common configuration.
    """
    
    class Meta:
        abstract = True


class TimestampMixin(serializers.Serializer):
    """
    Mixin that adds created_at and updated_at fields.
    """
    created_at = serializers.DateTimeField(read_only=True)
    updated_at = serializers.DateTimeField(read_only=True)


class UUIDPrimaryKeyMixin(serializers.Serializer):
    """
    Mixin that adds UUID id field.
    """
    id = serializers.UUIDField(read_only=True)
