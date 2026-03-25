"""
Memory REST API views for NeuroTwin platform.

Provides endpoints for listing, searching, and retrieving memories.
Requirements: 5.1, 5.3, 5.6
"""

from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework import status
from django.db.models import Q
from asgiref.sync import async_to_sync

from core.api.views import BaseAPIView
from core.api.permissions import IsVerifiedUser
from .models import MemoryRecord
from .serializers import (
    MemoryEntrySerializer,
    MemoryDetailSerializer,
    MemorySearchSerializer,
    MemoryListResponseSerializer,
    MemoryCreateSerializer,
)
from .services import VectorMemoryEngine
from .dataclasses import MemoryQuery


class MemoryListCreateView(BaseAPIView):
    """
    GET /api/v1/csm/memories
    POST /api/v1/csm/memories
    
    List user's memories or create a new memory.
    Requirements: 5.1, 5.3
    """
    permission_classes = [IsAuthenticated, IsVerifiedUser]
    
    def get(self, request):
        """
        List memories with optional search query.
        
        Query Parameters:
            q (str): Search query text
            source (str): Filter by source (conversation, action, feedback, learning, system)
            limit (int): Maximum results (default: 20, max: 100)
            offset (int): Pagination offset (default: 0)
        """
        # Validate query parameters
        search_serializer = MemorySearchSerializer(data=request.query_params)
        search_serializer.is_valid(raise_exception=True)
        
        query_text = search_serializer.validated_data.get('query', '')
        source_filter = search_serializer.validated_data.get('source')
        limit = search_serializer.validated_data.get('limit', 20)
        offset = search_serializer.validated_data.get('offset', 0)
        
        # Build queryset
        queryset = MemoryRecord.objects.filter(user_id=request.user.id)
        
        # Apply source filter
        if source_filter:
            queryset = queryset.filter(source=source_filter)
        
        # Apply text search if query provided
        if query_text:
            # Simple text search on content
            # For semantic search, use the VectorMemoryEngine
            queryset = queryset.filter(
                Q(content__icontains=query_text) |
                Q(metadata__icontains=query_text)
            )
        
        # Get total count
        total = queryset.count()
        
        # Apply pagination
        memories = queryset.order_by('-created_at')[offset:offset + limit]
        
        # Serialize
        serializer = MemoryEntrySerializer(memories, many=True)
        
        # Calculate pagination
        has_more = total > (offset + limit)
        next_cursor = offset + limit if has_more else None
        
        return self.success_response(
            data={
                'memories': serializer.data,
                'total': total,
                'hasMore': has_more,
                'nextCursor': next_cursor,
            }
        )
    
    def post(self, request):
        """
        Create a new memory.
        
        Request Body:
            content (str): Memory content
            source (str): Memory source
            metadata (dict): Additional metadata
        """
        serializer = MemoryCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        content = serializer.validated_data['content']
        source = serializer.validated_data['source']
        metadata = serializer.validated_data.get('metadata', {})
        
        # Create memory using VectorMemoryEngine
        memory_engine = VectorMemoryEngine()
        
        try:
            memory = async_to_sync(memory_engine.store_memory)(
                user_id=str(request.user.id),
                content=content,
                source=source,
                metadata=metadata
            )
            
            # Get the created record
            record = MemoryRecord.objects.get(id=memory.id)
            response_serializer = MemoryDetailSerializer(record)
            
            return self.success_response(
                data=response_serializer.data,
                status_code=status.HTTP_201_CREATED
            )
            
        except Exception as e:
            return self.error_response(
                message=f"Failed to create memory: {str(e)}",
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


# Keep the old views for backwards compatibility but mark as deprecated
class MemoryListView(MemoryListCreateView):
    """Deprecated: Use MemoryListCreateView instead."""
    def post(self, request):
        return self.error_response(
            message="POST not allowed on this endpoint. Use MemoryListCreateView.",
            status_code=status.HTTP_405_METHOD_NOT_ALLOWED
        )


class MemoryCreateView(MemoryListCreateView):
    """Deprecated: Use MemoryListCreateView instead."""
    def get(self, request):
        return self.error_response(
            message="GET not allowed on this endpoint. Use MemoryListCreateView.",
            status_code=status.HTTP_405_METHOD_NOT_ALLOWED
        )


class MemoryDetailView(BaseAPIView):
    """
    GET /api/v1/csm/memories/{memory_id}
    
    Get detailed information about a specific memory.
    Requirements: 5.6
    """
    permission_classes = [IsAuthenticated, IsVerifiedUser]
    
    def get(self, request, memory_id):
        """
        Retrieve detailed memory information.
        
        Path Parameters:
            memory_id (uuid): Memory ID
        """
        try:
            memory = MemoryRecord.objects.get(
                id=memory_id,
                user_id=request.user.id
            )
        except MemoryRecord.DoesNotExist:
            return self.error_response(
                message="Memory not found",
                status_code=status.HTTP_404_NOT_FOUND
            )
        
        serializer = MemoryDetailSerializer(memory)
        
        return self.success_response(data=serializer.data)


class MemorySearchView(BaseAPIView):
    """
    POST /api/v1/csm/memories/search
    
    Semantic search across memories using vector embeddings.
    Requirements: 5.3, 5.7
    """
    permission_classes = [IsAuthenticated, IsVerifiedUser]
    
    def post(self, request):
        """
        Perform semantic search on memories.
        
        Request Body:
            query (str): Search query text
            max_results (int): Maximum results (default: 10)
            min_relevance (float): Minimum relevance score (default: 0.5)
            recency_weight (float): Weight for recency (default: 0.3)
            source_filter (list): Filter by sources
        """
        query_text = request.data.get('query', '')
        
        if not query_text or not query_text.strip():
            return self.error_response(
                message="Search query is required",
                status_code=status.HTTP_400_BAD_REQUEST
            )
        
        # Build memory query
        memory_query = MemoryQuery(
            query_text=query_text.strip(),
            max_results=request.data.get('max_results', 10),
            min_relevance=request.data.get('min_relevance', 0.5),
            recency_weight=request.data.get('recency_weight', 0.3),
            source_filter=request.data.get('source_filter'),
        )
        
        # Perform semantic search
        memory_engine = VectorMemoryEngine()
        
        try:
            # Run async search in sync context
            memories = async_to_sync(memory_engine.retrieve_relevant)(
                user_id=str(request.user.id),
                query=memory_query
            )
            
            # Convert to MemoryRecord format for serialization
            memory_records = []
            for memory in memories:
                try:
                    record = MemoryRecord.objects.get(id=memory.id)
                    memory_records.append(record)
                except MemoryRecord.DoesNotExist:
                    continue
            
            serializer = MemoryEntrySerializer(memory_records, many=True)
            
            return self.success_response(
                data={
                    'memories': serializer.data,
                    'total': len(memory_records),
                    'query': query_text,
                }
            )
            
        except Exception as e:
            return self.error_response(
                message=f"Search failed: {str(e)}",
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class MemoryCreateView(BaseAPIView):
    """
    POST /api/v1/csm/memories
    
    Create a new memory entry.
    Requirements: 5.1
    """
    permission_classes = [IsAuthenticated, IsVerifiedUser]
    
    def post(self, request):
        """
        Create a new memory.
        
        Request Body:
            content (str): Memory content
            source (str): Memory source
            metadata (dict): Additional metadata
        """
        serializer = MemoryCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        content = serializer.validated_data['content']
        source = serializer.validated_data['source']
        metadata = serializer.validated_data.get('metadata', {})
        
        # Create memory using VectorMemoryEngine
        memory_engine = VectorMemoryEngine()
        
        try:
            memory = async_to_sync(memory_engine.store_memory)(
                user_id=str(request.user.id),
                content=content,
                source=source,
                metadata=metadata
            )
            
            # Get the created record
            record = MemoryRecord.objects.get(id=memory.id)
            response_serializer = MemoryDetailSerializer(record)
            
            return self.success_response(
                data=response_serializer.data,
                status_code=status.HTTP_201_CREATED
            )
            
        except Exception as e:
            return self.error_response(
                message=f"Failed to create memory: {str(e)}",
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class MemoryStatsView(BaseAPIView):
    """
    GET /api/v1/csm/memories/stats
    
    Get memory statistics for the user.
    Requirements: 5.6
    """
    permission_classes = [IsAuthenticated, IsVerifiedUser]
    
    def get(self, request):
        """
        Get memory statistics.
        
        Returns:
            total_memories: Total number of memories
            by_source: Breakdown by source type
            recent_count: Memories in last 7 days
        """
        from django.db.models import Count
        from datetime import timedelta
        from django.utils import timezone
        
        user_id = request.user.id
        
        # Total memories
        total = MemoryRecord.objects.filter(user_id=user_id).count()
        
        # By source
        by_source = MemoryRecord.objects.filter(user_id=user_id).values('source').annotate(
            count=Count('id')
        )
        
        # Recent memories (last 7 days)
        seven_days_ago = timezone.now() - timedelta(days=7)
        recent_count = MemoryRecord.objects.filter(
            user_id=user_id,
            created_at__gte=seven_days_ago
        ).count()
        
        return self.success_response(
            data={
                'total_memories': total,
                'by_source': {item['source']: item['count'] for item in by_source},
                'recent_count': recent_count,
            }
        )
