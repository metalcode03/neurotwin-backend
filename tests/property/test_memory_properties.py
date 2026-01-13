"""
Property-based tests for Memory (Vector Memory Engine).

Feature: neurotwin-platform
Validates: Requirements 5.1, 5.2, 5.3, 5.4, 5.6, 5.7

These tests use Hypothesis to verify memory properties hold
across a wide range of inputs.
"""

import pytest
import asyncio
from hypothesis import given, strategies as st, settings, assume, HealthCheck
from datetime import datetime, timedelta
from django.utils import timezone

from apps.memory.dataclasses import Memory, MemoryQuery, MemorySource
from apps.memory.models import MemoryRecord
from apps.memory.services import VectorMemoryEngine
from apps.memory.vector_client import (
    InMemoryVectorClient,
    MockEmbeddingGenerator,
    reset_clients,
    set_vector_client,
    set_embedding_generator,
)
from apps.authentication.models import User


# Custom strategies for generating memory data

# Strategy for memory content (non-empty strings)
memory_content_strategy = st.text(
    min_size=1,
    max_size=200,
    alphabet=st.characters(
        whitelist_categories=('L', 'N'),
        whitelist_characters=' .,!?-'
    )
).filter(lambda x: len(x.strip()) >= 1)

# Strategy for memory source
memory_source_strategy = st.sampled_from([
    MemorySource.CONVERSATION.value,
    MemorySource.ACTION.value,
    MemorySource.FEEDBACK.value,
    MemorySource.LEARNING.value,
    MemorySource.SYSTEM.value,
])

# Strategy for metadata
metadata_strategy = st.dictionaries(
    keys=st.text(
        min_size=1,
        max_size=10,
        alphabet=st.characters(whitelist_categories=('L',), whitelist_characters='_')
    ),
    values=st.text(min_size=0, max_size=20),
    min_size=0,
    max_size=3
)

# Strategy for query text
query_text_strategy = st.text(
    min_size=1,
    max_size=100,
    alphabet=st.characters(
        whitelist_categories=('L', 'N'),
        whitelist_characters=' .,!?-'
    )
).filter(lambda x: len(x.strip()) >= 1)

# Strategy for relevance threshold
relevance_strategy = st.floats(min_value=0.0, max_value=1.0, allow_nan=False, allow_infinity=False)

# Strategy for recency weight
recency_weight_strategy = st.floats(min_value=0.0, max_value=1.0, allow_nan=False, allow_infinity=False)

# Strategy for max results
max_results_strategy = st.integers(min_value=1, max_value=50)


def create_test_user(email_suffix: str) -> User:
    """Create a test user with unique email."""
    email = f"memory_test_{email_suffix}@example.com"
    User.objects.filter(email=email).delete()
    return User.objects.create_user(email=email, password="testpass123")


def setup_fresh_clients():
    """Set up fresh in-memory clients for testing."""
    reset_clients()
    vector_client = InMemoryVectorClient()
    embedding_generator = MockEmbeddingGenerator(dimension=768)
    set_vector_client(vector_client)
    set_embedding_generator(embedding_generator)
    return vector_client, embedding_generator


def run_async(coro):
    """Helper to run async functions in sync tests."""
    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        loop = None
    
    if loop and loop.is_running():
        # If there's a running loop, create a new one in a thread
        import concurrent.futures
        with concurrent.futures.ThreadPoolExecutor() as executor:
            future = executor.submit(asyncio.run, coro)
            return future.result()
    else:
        # Create a new event loop for each call
        return asyncio.run(coro)



@pytest.mark.django_db(transaction=True)
class TestInteractionEmbeddingStorage:
    """
    Property 12: Interaction embedding storage
    
    *For any* user interaction, the system SHALL asynchronously generate
    an embedding and store it in the vector database.
    
    **Validates: Requirements 5.1, 5.2**
    """
    
    @settings(max_examples=10, deadline=None)
    @given(
        content=memory_content_strategy,
        source=memory_source_strategy,
    )
    def test_memory_storage_generates_embedding(
        self,
        content: str,
        source: str,
    ):
        """
        Feature: neurotwin-platform, Property 12: Interaction embedding storage
        
        For any valid content, storing a memory should generate an embedding
        and store it in both PostgreSQL and the vector database.
        """
        vector_client, embedding_generator = setup_fresh_clients()
        engine = VectorMemoryEngine(
            vector_client=vector_client,
            embedding_generator=embedding_generator
        )
        
        email = f"embed_store_{hash(content) % 100000}@test.com"
        User.objects.filter(email=email).delete()
        user = User.objects.create_user(email=email, password="testpass123")
        
        try:
            # Store memory
            memory = run_async(engine.store_memory(
                user_id=str(user.id),
                content=content,
                source=source,
            ))
            
            # Verify memory was created
            assert memory is not None
            assert memory.id is not None
            assert memory.user_id == str(user.id)
            assert memory.content == content
            assert memory.source == source
            
            # Verify embedding was generated
            assert memory.embedding is not None
            assert len(memory.embedding) == embedding_generator.dimension
            
            # Verify stored in PostgreSQL
            record = MemoryRecord.objects.get(id=memory.id)
            assert record is not None
            assert record.content == content
            assert record.has_embedding is True
            
            # Verify stored in vector database
            vector_exists = run_async(vector_client.exists(memory.id))
            assert vector_exists is True
        finally:
            User.objects.filter(id=user.id).delete()
    
    @settings(max_examples=10, deadline=None)
    @given(
        content=memory_content_strategy,
        source=memory_source_strategy,
    )
    def test_duplicate_content_not_stored_twice(
        self,
        content: str,
        source: str,
    ):
        """
        Feature: neurotwin-platform, Property 12: Interaction embedding storage
        
        For any content stored twice, the system should detect the duplicate
        and return the existing memory instead of creating a new one.
        """
        vector_client, embedding_generator = setup_fresh_clients()
        engine = VectorMemoryEngine(
            vector_client=vector_client,
            embedding_generator=embedding_generator
        )
        
        email = f"dedup_{hash(content) % 100000}@test.com"
        User.objects.filter(email=email).delete()
        user = User.objects.create_user(email=email, password="testpass123")
        
        try:
            # Store memory first time
            memory1 = run_async(engine.store_memory(
                user_id=str(user.id),
                content=content,
                source=source,
            ))
            
            # Store same content again
            memory2 = run_async(engine.store_memory(
                user_id=str(user.id),
                content=content,
                source=source,
            ))
            
            # Should return the same memory
            assert memory1.id == memory2.id
            
            # Should only have one record in database
            count = MemoryRecord.objects.filter(user_id=user.id).count()
            assert count == 1
        finally:
            User.objects.filter(id=user.id).delete()



@pytest.mark.django_db(transaction=True)
class TestMemoryRetrievalRelevance:
    """
    Property 13: Memory retrieval relevance
    
    *For any* context query, the memory engine SHALL return memories
    ordered by relevance and recency scoring.
    
    **Validates: Requirements 5.3, 5.7**
    """
    
    @settings(max_examples=10, deadline=None)
    @given(
        contents=st.lists(memory_content_strategy, min_size=2, max_size=5, unique=True),
        query=query_text_strategy,
        recency_weight=recency_weight_strategy,
    )
    def test_memories_returned_in_score_order(
        self,
        contents: list,
        query: str,
        recency_weight: float,
    ):
        """
        Feature: neurotwin-platform, Property 13: Memory retrieval relevance
        
        For any set of stored memories and query, retrieved memories
        should be ordered by their combined relevance/recency score.
        """
        vector_client, embedding_generator = setup_fresh_clients()
        engine = VectorMemoryEngine(
            vector_client=vector_client,
            embedding_generator=embedding_generator
        )
        
        email = f"relevance_{hash(str(contents)) % 100000}@test.com"
        User.objects.filter(email=email).delete()
        user = User.objects.create_user(email=email, password="testpass123")
        
        try:
            # Store multiple memories
            for content in contents:
                run_async(engine.store_memory(
                    user_id=str(user.id),
                    content=content,
                    source=MemorySource.CONVERSATION.value,
                ))
            
            # Query memories
            memory_query = MemoryQuery(
                query_text=query,
                max_results=len(contents),
                min_relevance=0.0,
                recency_weight=recency_weight,
            )
            
            results = run_async(engine.retrieve_relevant(
                user_id=str(user.id),
                query=memory_query
            ))
            
            # Verify results are ordered by score (descending)
            if len(results) > 1:
                for i in range(len(results) - 1):
                    score_current = results[i].relevance_score or 0
                    score_next = results[i + 1].relevance_score or 0
                    assert score_current >= score_next
        finally:
            User.objects.filter(id=user.id).delete()
    
    @settings(max_examples=10, deadline=None)
    @given(
        contents=st.lists(memory_content_strategy, min_size=3, max_size=5, unique=True),
        max_results=st.integers(min_value=1, max_value=3),
    )
    def test_max_results_limit_respected(
        self,
        contents: list,
        max_results: int,
    ):
        """
        Feature: neurotwin-platform, Property 13: Memory retrieval relevance
        
        For any max_results limit, the number of returned memories
        should not exceed that limit.
        """
        vector_client, embedding_generator = setup_fresh_clients()
        engine = VectorMemoryEngine(
            vector_client=vector_client,
            embedding_generator=embedding_generator
        )
        
        email = f"max_res_{hash(str(contents)) % 100000}@test.com"
        User.objects.filter(email=email).delete()
        user = User.objects.create_user(email=email, password="testpass123")
        
        try:
            # Store multiple memories
            for content in contents:
                run_async(engine.store_memory(
                    user_id=str(user.id),
                    content=content,
                    source=MemorySource.CONVERSATION.value,
                ))
            
            # Query with max_results limit
            memory_query = MemoryQuery(
                query_text="test query",
                max_results=max_results,
                min_relevance=0.0,
            )
            
            results = run_async(engine.retrieve_relevant(
                user_id=str(user.id),
                query=memory_query
            ))
            
            # Should not exceed max_results
            assert len(results) <= max_results
        finally:
            User.objects.filter(id=user.id).delete()



@pytest.mark.django_db(transaction=True)
class TestMemoryExistenceValidation:
    """
    Property 14: Memory existence validation
    
    *For any* memory reference made by the Twin, that memory SHALL exist
    in the vector store (no fabrication).
    
    **Validates: Requirements 5.4**
    """
    
    @settings(max_examples=10, deadline=None)
    @given(
        content=memory_content_strategy,
        source=memory_source_strategy,
    )
    def test_stored_memory_validates_as_existing(
        self,
        content: str,
        source: str,
    ):
        """
        Feature: neurotwin-platform, Property 14: Memory existence validation
        
        For any stored memory, validate_memory_exists should return True.
        """
        vector_client, embedding_generator = setup_fresh_clients()
        engine = VectorMemoryEngine(
            vector_client=vector_client,
            embedding_generator=embedding_generator
        )
        
        email = f"exist_valid_{hash(content) % 100000}@test.com"
        User.objects.filter(email=email).delete()
        user = User.objects.create_user(email=email, password="testpass123")
        
        try:
            # Store a memory
            memory = run_async(engine.store_memory(
                user_id=str(user.id),
                content=content,
                source=source,
            ))
            
            # Validate it exists
            exists = run_async(engine.validate_memory_exists(memory.id))
            assert exists is True
        finally:
            User.objects.filter(id=user.id).delete()
    
    @settings(max_examples=10, deadline=None)
    @given(
        fake_id=st.uuids().map(str),
    )
    def test_nonexistent_memory_validates_as_missing(
        self,
        fake_id: str,
    ):
        """
        Feature: neurotwin-platform, Property 14: Memory existence validation
        
        For any non-existent memory ID, validate_memory_exists should return False.
        This prevents the Twin from fabricating memories.
        """
        vector_client, embedding_generator = setup_fresh_clients()
        engine = VectorMemoryEngine(
            vector_client=vector_client,
            embedding_generator=embedding_generator
        )
        
        # Validate non-existent memory
        exists = run_async(engine.validate_memory_exists(fake_id))
        assert exists is False
    
    @settings(max_examples=10, deadline=None)
    @given(
        content=memory_content_strategy,
        source=memory_source_strategy,
    )
    def test_deleted_memory_validates_as_missing(
        self,
        content: str,
        source: str,
    ):
        """
        Feature: neurotwin-platform, Property 14: Memory existence validation
        
        For any deleted memory, validate_memory_exists should return False.
        """
        vector_client, embedding_generator = setup_fresh_clients()
        engine = VectorMemoryEngine(
            vector_client=vector_client,
            embedding_generator=embedding_generator
        )
        
        email = f"del_valid_{hash(content) % 100000}@test.com"
        User.objects.filter(email=email).delete()
        user = User.objects.create_user(email=email, password="testpass123")
        
        try:
            # Store a memory
            memory = run_async(engine.store_memory(
                user_id=str(user.id),
                content=content,
                source=source,
            ))
            
            # Delete it
            deleted = run_async(engine.delete_memory(memory.id))
            assert deleted is True
            
            # Validate it no longer exists
            exists = run_async(engine.validate_memory_exists(memory.id))
            assert exists is False
        finally:
            User.objects.filter(id=user.id).delete()



@pytest.mark.django_db(transaction=True)
class TestMemoryTimestampInclusion:
    """
    Property 15: Memory timestamp inclusion
    
    *For any* memory read operation, the result SHALL include the source
    timestamp for validation.
    
    **Validates: Requirements 5.6**
    """
    
    @settings(max_examples=10, deadline=None)
    @given(
        content=memory_content_strategy,
        source=memory_source_strategy,
    )
    def test_stored_memory_has_timestamp(
        self,
        content: str,
        source: str,
    ):
        """
        Feature: neurotwin-platform, Property 15: Memory timestamp inclusion
        
        For any stored memory, the returned Memory object should include
        a valid timestamp.
        """
        vector_client, embedding_generator = setup_fresh_clients()
        engine = VectorMemoryEngine(
            vector_client=vector_client,
            embedding_generator=embedding_generator
        )
        
        email = f"ts_store_{hash(content) % 100000}@test.com"
        User.objects.filter(email=email).delete()
        user = User.objects.create_user(email=email, password="testpass123")
        
        try:
            before_store = timezone.now()
            
            # Store a memory
            memory = run_async(engine.store_memory(
                user_id=str(user.id),
                content=content,
                source=source,
            ))
            
            after_store = timezone.now()
            
            # Verify timestamp is present and valid
            assert memory.timestamp is not None
            assert isinstance(memory.timestamp, datetime)
            
            # Timestamp should be between before and after store
            assert before_store <= memory.timestamp <= after_store
        finally:
            User.objects.filter(id=user.id).delete()
    
    @settings(max_examples=10, deadline=None)
    @given(
        content=memory_content_strategy,
        source=memory_source_strategy,
    )
    def test_retrieved_memory_has_timestamp(
        self,
        content: str,
        source: str,
    ):
        """
        Feature: neurotwin-platform, Property 15: Memory timestamp inclusion
        
        For any retrieved memory via get_memory_with_source, the result
        should include the original timestamp.
        """
        vector_client, embedding_generator = setup_fresh_clients()
        engine = VectorMemoryEngine(
            vector_client=vector_client,
            embedding_generator=embedding_generator
        )
        
        email = f"ts_retrieve_{hash(content) % 100000}@test.com"
        User.objects.filter(email=email).delete()
        user = User.objects.create_user(email=email, password="testpass123")
        
        try:
            # Store a memory
            stored_memory = run_async(engine.store_memory(
                user_id=str(user.id),
                content=content,
                source=source,
            ))
            
            # Retrieve it
            retrieved_memory = run_async(engine.get_memory_with_source(stored_memory.id))
            
            # Verify timestamp is present and matches
            assert retrieved_memory is not None
            assert retrieved_memory.timestamp is not None
            assert isinstance(retrieved_memory.timestamp, datetime)
            assert retrieved_memory.timestamp == stored_memory.timestamp
        finally:
            User.objects.filter(id=user.id).delete()
    
    @settings(max_examples=10, deadline=None)
    @given(
        contents=st.lists(memory_content_strategy, min_size=2, max_size=3, unique=True),
    )
    def test_search_results_have_timestamps(
        self,
        contents: list,
    ):
        """
        Feature: neurotwin-platform, Property 15: Memory timestamp inclusion
        
        For any memory search results, all returned memories should
        include their timestamps.
        """
        vector_client, embedding_generator = setup_fresh_clients()
        engine = VectorMemoryEngine(
            vector_client=vector_client,
            embedding_generator=embedding_generator
        )
        
        email = f"ts_search_{hash(str(contents)) % 100000}@test.com"
        User.objects.filter(email=email).delete()
        user = User.objects.create_user(email=email, password="testpass123")
        
        try:
            # Store multiple memories
            for content in contents:
                run_async(engine.store_memory(
                    user_id=str(user.id),
                    content=content,
                    source=MemorySource.CONVERSATION.value,
                ))
            
            # Search for memories
            memory_query = MemoryQuery(
                query_text="test query",
                max_results=len(contents),
                min_relevance=0.0,
            )
            
            results = run_async(engine.retrieve_relevant(
                user_id=str(user.id),
                query=memory_query
            ))
            
            # All results should have timestamps
            for memory in results:
                assert memory.timestamp is not None
                assert isinstance(memory.timestamp, datetime)
        finally:
            User.objects.filter(id=user.id).delete()
    
    @settings(max_examples=10, deadline=None)
    @given(
        content=memory_content_strategy,
    )
    def test_nonexistent_memory_returns_none(
        self,
        content: str,
    ):
        """
        Feature: neurotwin-platform, Property 15: Memory timestamp inclusion
        
        For any non-existent memory ID, get_memory_with_source should
        return None rather than fabricating data.
        """
        vector_client, embedding_generator = setup_fresh_clients()
        engine = VectorMemoryEngine(
            vector_client=vector_client,
            embedding_generator=embedding_generator
        )
        
        import uuid
        fake_id = str(uuid.uuid4())
        
        # Try to retrieve non-existent memory
        result = run_async(engine.get_memory_with_source(fake_id))
        
        # Should return None, not fabricate
        assert result is None



@pytest.mark.django_db(transaction=True)
class TestMemoryDataclassRoundTrip:
    """
    Additional property test for Memory dataclass serialization.
    
    Ensures Memory objects can be serialized and deserialized correctly.
    """
    
    @settings(deadline=None)
    @given(
        content=memory_content_strategy,
        source=memory_source_strategy,
        metadata=metadata_strategy,
        relevance_score=st.one_of(st.none(), relevance_strategy),
    )
    def test_memory_json_round_trip(
        self,
        content: str,
        source: str,
        metadata: dict,
        relevance_score: float,
    ):
        """
        Feature: neurotwin-platform, Memory JSON serialization round-trip
        
        For any valid Memory object, serializing to JSON and deserializing
        should produce an equivalent Memory.
        """
        import uuid
        
        # Create a Memory object
        memory = Memory(
            id=str(uuid.uuid4()),
            user_id=str(uuid.uuid4()),
            content=content,
            embedding=[0.1, 0.2, 0.3],
            source=source,
            timestamp=timezone.now(),
            metadata=metadata,
            relevance_score=relevance_score,
        )
        
        # Serialize to JSON
        json_str = memory.to_json()
        
        # Deserialize from JSON
        restored = Memory.from_json(json_str)
        
        # Verify all fields match
        assert restored.id == memory.id
        assert restored.user_id == memory.user_id
        assert restored.content == memory.content
        assert restored.embedding == memory.embedding
        assert restored.source == memory.source
        assert restored.metadata == memory.metadata
        assert restored.relevance_score == memory.relevance_score
        
        # Timestamp comparison (may have microsecond differences due to ISO format)
        assert abs((restored.timestamp - memory.timestamp).total_seconds()) < 1
    
    @settings(deadline=None)
    @given(
        content=memory_content_strategy,
        source=memory_source_strategy,
        metadata=metadata_strategy,
    )
    def test_memory_dict_round_trip(
        self,
        content: str,
        source: str,
        metadata: dict,
    ):
        """
        Feature: neurotwin-platform, Memory dict serialization round-trip
        
        For any valid Memory object, converting to dict and back
        should produce an equivalent Memory.
        """
        import uuid
        
        # Create a Memory object
        memory = Memory(
            id=str(uuid.uuid4()),
            user_id=str(uuid.uuid4()),
            content=content,
            embedding=[0.5, -0.5, 0.0],
            source=source,
            timestamp=timezone.now(),
            metadata=metadata,
        )
        
        # Convert to dict
        data_dict = memory.to_dict()
        
        # Restore from dict
        restored = Memory.from_dict(data_dict)
        
        # Verify equivalence
        assert restored.id == memory.id
        assert restored.user_id == memory.user_id
        assert restored.content == memory.content
        assert restored.source == memory.source
        assert restored.metadata == memory.metadata


@pytest.mark.django_db(transaction=True)
class TestMemoryQueryValidation:
    """
    Additional property test for MemoryQuery validation.
    
    Ensures MemoryQuery properly validates its parameters.
    """
    
    @settings(deadline=None)
    @given(
        query_text=query_text_strategy,
        max_results=max_results_strategy,
        min_relevance=relevance_strategy,
        recency_weight=recency_weight_strategy,
    )
    def test_valid_query_creation(
        self,
        query_text: str,
        max_results: int,
        min_relevance: float,
        recency_weight: float,
    ):
        """
        Feature: neurotwin-platform, MemoryQuery validation
        
        For any valid parameters, MemoryQuery should be created successfully.
        """
        query = MemoryQuery(
            query_text=query_text,
            max_results=max_results,
            min_relevance=min_relevance,
            recency_weight=recency_weight,
        )
        
        assert query.query_text == query_text
        assert query.max_results == max_results
        assert query.min_relevance == min_relevance
        assert query.recency_weight == recency_weight
    
    @settings(deadline=None)
    @given(
        query_text=query_text_strategy,
        source_filter=st.lists(memory_source_strategy, min_size=1, max_size=3, unique=True),
    )
    def test_source_filter_validation(
        self,
        query_text: str,
        source_filter: list,
    ):
        """
        Feature: neurotwin-platform, MemoryQuery source filter validation
        
        For any valid source filter, MemoryQuery should accept it.
        """
        query = MemoryQuery(
            query_text=query_text,
            source_filter=source_filter,
        )
        
        assert query.source_filter == source_filter
    
    def test_invalid_min_relevance_rejected(self):
        """
        Feature: neurotwin-platform, MemoryQuery validation
        
        Invalid min_relevance values should be rejected.
        """
        with pytest.raises(ValueError):
            MemoryQuery(query_text="test", min_relevance=1.5)
        
        with pytest.raises(ValueError):
            MemoryQuery(query_text="test", min_relevance=-0.1)
    
    def test_invalid_recency_weight_rejected(self):
        """
        Feature: neurotwin-platform, MemoryQuery validation
        
        Invalid recency_weight values should be rejected.
        """
        with pytest.raises(ValueError):
            MemoryQuery(query_text="test", recency_weight=1.5)
        
        with pytest.raises(ValueError):
            MemoryQuery(query_text="test", recency_weight=-0.1)
    
    def test_invalid_max_results_rejected(self):
        """
        Feature: neurotwin-platform, MemoryQuery validation
        
        Invalid max_results values should be rejected.
        """
        with pytest.raises(ValueError):
            MemoryQuery(query_text="test", max_results=0)
        
        with pytest.raises(ValueError):
            MemoryQuery(query_text="test", max_results=-1)
    
    def test_empty_query_text_rejected(self):
        """
        Feature: neurotwin-platform, MemoryQuery validation
        
        Empty query text should be rejected.
        """
        with pytest.raises(ValueError):
            MemoryQuery(query_text="")
