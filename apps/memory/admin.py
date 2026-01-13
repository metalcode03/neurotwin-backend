"""
Admin configuration for Memory app.
"""

from django.contrib import admin
from .models import MemoryRecord, MemoryAccessLog


@admin.register(MemoryRecord)
class MemoryRecordAdmin(admin.ModelAdmin):
    """Admin configuration for MemoryRecord model."""
    
    list_display = [
        'id',
        'user',
        'source',
        'has_embedding',
        'created_at',
    ]
    list_filter = ['source', 'has_embedding', 'created_at']
    search_fields = ['content', 'user__email']
    readonly_fields = ['id', 'content_hash', 'created_at', 'updated_at']
    ordering = ['-created_at']
    
    fieldsets = [
        (None, {
            'fields': ['id', 'user', 'content', 'source']
        }),
        ('Embedding Info', {
            'fields': ['has_embedding', 'vector_id', 'embedding_model']
        }),
        ('Metadata', {
            'fields': ['metadata', 'content_hash']
        }),
        ('Timestamps', {
            'fields': ['created_at', 'updated_at']
        }),
    ]


@admin.register(MemoryAccessLog)
class MemoryAccessLogAdmin(admin.ModelAdmin):
    """Admin configuration for MemoryAccessLog model."""
    
    list_display = ['id', 'memory', 'access_type', 'accessed_at']
    list_filter = ['access_type', 'accessed_at']
    readonly_fields = ['id', 'accessed_at']
    ordering = ['-accessed_at']
