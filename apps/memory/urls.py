"""
Memory API URL configuration.

Requirements: 5.1, 5.3, 5.6
"""

from django.urls import path
from .views import (
    MemoryListCreateView,
    MemoryDetailView,
    MemorySearchView,
    MemoryStatsView,
)

app_name = 'memory'

urlpatterns = [
    # List and create memories (combined endpoint)
    path('', MemoryListCreateView.as_view(), name='list-create'),
    
    # Search and stats
    path('search', MemorySearchView.as_view(), name='search'),
    path('stats', MemoryStatsView.as_view(), name='stats'),
    
    # Detail view
    path('<uuid:memory_id>', MemoryDetailView.as_view(), name='detail'),
]
