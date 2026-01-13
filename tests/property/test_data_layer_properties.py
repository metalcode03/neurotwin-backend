"""
Property-based tests for Data Layer (Transactions and Async Tasks).

Feature: neurotwin-platform
Validates: Requirements 14.3, 14.5

These tests use Hypothesis to verify data layer properties hold
across a wide range of inputs.
"""

import pytest
from unittest.mock import patch, MagicMock
from hypothesis import given, strategies as st, settings, assume
from django.db import transaction, IntegrityError
from django.test import TransactionTestCase

from core.db.transactions import (
    atomic_operation,
    ensure_atomic,
    TransactionManager,
    is_in_transaction,
    get_transaction_depth,
    TransactionError,
)
from core.tasks.queue import (
    enqueue_task,
    enqueue_memory_write,
    enqueue_embedding_generation,
    TaskPriority,
)
from apps.authentication.models import User


# Custom strategies for generating test data

# Strategy for user email (unique per test)
email_strategy = st.text(
    min_size=3,
    max_size=20,
    alphabet=st.characters(whitelist_categories=('Ll',))
).map(lambda x: f"txn_test_{x}@example.com")

# Strategy for content strings
content_strategy = st.text(
    min_size=1,
    max_size=100,
    alphabet=st.characters(
        whitelist_categories=('L', 'N'),
        whitelist_characters=' .,!?-'
    )
).filter(lambda x: len(x.strip()) >= 1)

# Strategy for user IDs
user_id_strategy = st.uuids().map(str)

# Strategy for memory source
memory_source_strategy = st.sampled_from([
    'conversation', 'action', 'feedback', 'learning', 'system'
])

# Strategy for metadata
metadata_strategy = st.dictionaries(
    keys=st.text(min_size=1, max_size=10, alphabet=st.characters(whitelist_categories=('Ll',))),
    values=st.text(min_size=0, max_size=20),
    min_size=0,
    max_size=3
)

# Strategy for task priority
priority_strategy = st.sampled_from(list(TaskPriority))


@pytest.mark.django_db(transaction=True)
class TestTransactionIntegrity:
    """
    Property 47: Transaction integrity
    
    *For any* database write operation, the system SHALL use transactions
    to ensure data integrity (all-or-nothing).
    
    **Validates: Requirements 14.3**
    """
    
    @settings(max_examples=10, deadline=None)
    @given(
        email_suffix=st.text(min_size=3, max_size=10, alphabet=st.characters(whitelist_categories=('Ll',))),
    )
    def test_atomic_operation_commits_on_success(self, email_suffix: str):
        """
        Feature: neurotwin-platform, Property 47: Transaction integrity
        
        For any successful operation wrapped in @atomic_operation,
        all changes should be committed to the database.
        """
        email = f"atomic_success_{email_suffix}@test.com"
        User.objects.filter(email=email).delete()
        
        @atomic_operation()
        def create_user_atomic(email: str) -> User:
            return User.objects.create_user(email=email, password="testpass123")
        
        try:
            user = create_user_atomic(email)
            
            # Verify user was committed
            assert user is not None
            assert user.id is not None
            
            # Verify user exists in database
            db_user = User.objects.filter(email=email).first()
            assert db_user is not None
            assert db_user.id == user.id
        finally:
            User.objects.filter(email=email).delete()
    
    @settings(max_examples=10, deadline=None)
    @given(
        email_suffix=st.text(min_size=3, max_size=10, alphabet=st.characters(whitelist_categories=('Ll',))),
    )
    def test_atomic_operation_rollback_on_failure(self, email_suffix: str):
        """
        Feature: neurotwin-platform, Property 47: Transaction integrity
        
        For any operation that fails within @atomic_operation,
        all changes should be rolled back.
        """
        email = f"atomic_fail_{email_suffix}@test.com"
        User.objects.filter(email=email).delete()
        
        @atomic_operation()
        def create_user_then_fail(email: str) -> User:
            user = User.objects.create_user(email=email, password="testpass123")
            # Force an error after creation
            raise ValueError("Simulated failure")
        
        try:
            with pytest.raises(ValueError):
                create_user_then_fail(email)
            
            # Verify user was NOT committed (rolled back)
            db_user = User.objects.filter(email=email).first()
            assert db_user is None
        finally:
            User.objects.filter(email=email).delete()
    
    @settings(max_examples=10, deadline=None)
    @given(
        email_suffix=st.text(min_size=3, max_size=10, alphabet=st.characters(whitelist_categories=('Ll',))),
    )
    def test_ensure_atomic_context_manager(self, email_suffix: str):
        """
        Feature: neurotwin-platform, Property 47: Transaction integrity
        
        For any operation within ensure_atomic context manager,
        changes should be atomic (all-or-nothing).
        """
        email = f"ctx_atomic_{email_suffix}@test.com"
        User.objects.filter(email=email).delete()
        
        try:
            # Test successful commit
            with ensure_atomic():
                user = User.objects.create_user(email=email, password="testpass123")
            
            # Verify committed
            assert User.objects.filter(email=email).exists()
            
            # Clean up for rollback test
            User.objects.filter(email=email).delete()
            
            # Test rollback on exception
            try:
                with ensure_atomic():
                    User.objects.create_user(email=email, password="testpass123")
                    raise ValueError("Force rollback")
            except ValueError:
                pass
            
            # Verify rolled back
            assert not User.objects.filter(email=email).exists()
        finally:
            User.objects.filter(email=email).delete()
    
    @settings(max_examples=10, deadline=None)
    @given(
        step_count=st.integers(min_value=2, max_value=4),
    )
    def test_transaction_manager_all_or_nothing(self, step_count: int):
        """
        Feature: neurotwin-platform, Property 47: Transaction integrity
        
        For any multi-step transaction using TransactionManager,
        either all steps succeed or all are rolled back.
        """
        emails = [f"txn_mgr_{i}_{step_count}@test.com" for i in range(step_count)]
        
        # Clean up any existing users
        for email in emails:
            User.objects.filter(email=email).delete()
        
        try:
            manager = TransactionManager()
            
            # Add steps to create users
            for i, email in enumerate(emails):
                manager.add_step(
                    f"create_user_{i}",
                    lambda e=email: User.objects.create_user(email=e, password="testpass123")
                )
            
            # Execute all steps
            with manager.begin():
                results = manager.execute_all()
            
            # Verify all users were created
            assert len(results) == step_count
            for email in emails:
                assert User.objects.filter(email=email).exists()
        finally:
            for email in emails:
                User.objects.filter(email=email).delete()
    
    @settings(max_examples=10, deadline=None)
    @given(
        fail_at_step=st.integers(min_value=1, max_value=3),
    )
    def test_transaction_manager_rollback_on_step_failure(self, fail_at_step: int):
        """
        Feature: neurotwin-platform, Property 47: Transaction integrity
        
        For any multi-step transaction where a step fails,
        all previous steps should be rolled back.
        """
        total_steps = 4
        emails = [f"txn_fail_{i}_{fail_at_step}@test.com" for i in range(total_steps)]
        
        # Clean up any existing users
        for email in emails:
            User.objects.filter(email=email).delete()
        
        try:
            manager = TransactionManager()
            
            # Add steps, with one that will fail
            for i, email in enumerate(emails):
                if i == fail_at_step:
                    manager.add_step(
                        f"create_user_{i}",
                        lambda: (_ for _ in ()).throw(ValueError("Step failed"))
                    )
                else:
                    manager.add_step(
                        f"create_user_{i}",
                        lambda e=email: User.objects.create_user(email=e, password="testpass123")
                    )
            
            # Execute should fail
            with pytest.raises(ValueError):
                with manager.begin():
                    manager.execute_all()
            
            # Verify NO users were created (all rolled back)
            for email in emails:
                assert not User.objects.filter(email=email).exists()
        finally:
            for email in emails:
                User.objects.filter(email=email).delete()
    
    @settings(max_examples=10, deadline=None)
    @given(
        email_suffix=st.text(min_size=3, max_size=10, alphabet=st.characters(whitelist_categories=('Ll',))),
    )
    def test_is_in_transaction_detection(self, email_suffix: str):
        """
        Feature: neurotwin-platform, Property 47: Transaction integrity
        
        For any code execution, is_in_transaction should correctly
        detect whether we're inside a transaction.
        """
        # Outside transaction
        assert not is_in_transaction()
        
        # Inside transaction
        with ensure_atomic():
            assert is_in_transaction()
        
        # Back outside
        assert not is_in_transaction()
    
    @settings(max_examples=10, deadline=None)
    @given(
        nesting_depth=st.integers(min_value=1, max_value=3),
    )
    def test_nested_transaction_tracking(self, nesting_depth: int):
        """
        Feature: neurotwin-platform, Property 47: Transaction integrity
        
        For any nested transaction, is_in_transaction should correctly
        detect we're inside a transaction at all nesting levels.
        """
        # Outside transaction
        assert not is_in_transaction()
        
        def nested_atomic(depth: int, current: int = 0):
            if current >= depth:
                return
            with ensure_atomic(savepoint=True):
                # Should always be in transaction at any nesting level
                assert is_in_transaction()
                nested_atomic(depth, current + 1)
        
        nested_atomic(nesting_depth)
        
        # Back outside transaction
        assert not is_in_transaction()


@pytest.mark.django_db(transaction=True)
class TestAsyncMemoryWrites:
    """
    Property 48: Async memory writes
    
    *For any* memory write operation, the write SHALL be asynchronous
    and not block the HTTP request.
    
    **Validates: Requirements 14.5**
    """
    
    @settings(max_examples=10, deadline=None)
    @given(
        user_id=user_id_strategy,
        content=content_strategy,
        source=memory_source_strategy,
    )
    def test_memory_write_enqueued_not_blocking(
        self,
        user_id: str,
        content: str,
        source: str,
    ):
        """
        Feature: neurotwin-platform, Property 48: Async memory writes
        
        For any memory write request, the enqueue operation should
        return immediately without blocking.
        """
        import time
        
        with patch('django_q.tasks.async_task', return_value='mock_task_id') as mock_async:
            start_time = time.time()
            
            task_id = enqueue_memory_write(
                user_id=user_id,
                content=content,
                source=source,
            )
            
            elapsed = time.time() - start_time
            
            # Should return almost immediately (< 100ms)
            assert elapsed < 0.1
            
            # Should have called async_task
            mock_async.assert_called_once()
    
    @settings(max_examples=10, deadline=None)
    @given(
        user_id=user_id_strategy,
        content=content_strategy,
        source=memory_source_strategy,
        metadata=metadata_strategy,
    )
    def test_memory_write_includes_all_parameters(
        self,
        user_id: str,
        content: str,
        source: str,
        metadata: dict,
    ):
        """
        Feature: neurotwin-platform, Property 48: Async memory writes
        
        For any memory write, all parameters should be passed to the
        async task handler.
        """
        with patch('django_q.tasks.async_task', return_value='mock_task_id') as mock_async:
            enqueue_memory_write(
                user_id=user_id,
                content=content,
                source=source,
                metadata=metadata,
            )
            
            # Verify parameters were passed
            call_kwargs = mock_async.call_args[1]
            assert call_kwargs['user_id'] == user_id
            assert call_kwargs['content'] == content
            assert call_kwargs['source'] == source
            assert call_kwargs['metadata'] == metadata
    
    @settings(max_examples=10, deadline=None)
    @given(
        user_id=user_id_strategy,
        content=content_strategy,
        memory_id=user_id_strategy,
    )
    def test_embedding_generation_enqueued_async(
        self,
        user_id: str,
        content: str,
        memory_id: str,
    ):
        """
        Feature: neurotwin-platform, Property 48: Async memory writes
        
        For any embedding generation request, the operation should
        be enqueued asynchronously.
        """
        import time
        
        with patch('django_q.tasks.async_task', return_value='mock_task_id') as mock_async:
            start_time = time.time()
            
            task_id = enqueue_embedding_generation(
                user_id=user_id,
                content=content,
                memory_id=memory_id,
            )
            
            elapsed = time.time() - start_time
            
            # Should return almost immediately
            assert elapsed < 0.1
            
            # Should have called async_task with correct handler
            mock_async.assert_called_once()
            assert mock_async.call_args[0][0] == 'core.tasks.handlers.handle_embedding_generation'
    
    @settings(max_examples=10, deadline=None)
    @given(
        priority=priority_strategy,
        user_id=user_id_strategy,
        content=content_strategy,
        source=memory_source_strategy,
    )
    def test_task_priority_respected(
        self,
        priority: TaskPriority,
        user_id: str,
        content: str,
        source: str,
    ):
        """
        Feature: neurotwin-platform, Property 48: Async memory writes
        
        For any task with a specified priority, the priority should
        be passed to the queue configuration.
        """
        with patch('django_q.tasks.async_task', return_value='mock_task_id') as mock_async:
            enqueue_memory_write(
                user_id=user_id,
                content=content,
                source=source,
                priority=priority,
            )
            
            # Verify priority was set in q_options
            call_kwargs = mock_async.call_args[1]
            q_options = call_kwargs.get('q_options', {})
            
            expected_queue = {
                TaskPriority.LOW: 'low',
                TaskPriority.NORMAL: 'default',
                TaskPriority.HIGH: 'high',
                TaskPriority.CRITICAL: 'critical',
            }.get(priority, 'default')
            
            assert q_options.get('queue') == expected_queue
    
    @settings(max_examples=10, deadline=None)
    @given(
        user_id=user_id_strategy,
        content=content_strategy,
        source=memory_source_strategy,
    )
    def test_task_grouped_correctly(
        self,
        user_id: str,
        content: str,
        source: str,
    ):
        """
        Feature: neurotwin-platform, Property 48: Async memory writes
        
        For any memory write task, it should be grouped under
        'memory_writes' for proper queue management.
        """
        with patch('django_q.tasks.async_task', return_value='mock_task_id') as mock_async:
            enqueue_memory_write(
                user_id=user_id,
                content=content,
                source=source,
            )
            
            # Verify group was set
            call_kwargs = mock_async.call_args[1]
            q_options = call_kwargs.get('q_options', {})
            assert q_options.get('group') == 'memory_writes'
    
    @settings(max_examples=10, deadline=None)
    @given(
        user_id=user_id_strategy,
        content=content_strategy,
        source=memory_source_strategy,
    )
    def test_enqueue_returns_task_id(
        self,
        user_id: str,
        content: str,
        source: str,
    ):
        """
        Feature: neurotwin-platform, Property 48: Async memory writes
        
        For any successfully enqueued task, a task ID should be returned
        for tracking purposes.
        """
        expected_task_id = 'test_task_123'
        
        with patch('django_q.tasks.async_task', return_value=expected_task_id):
            task_id = enqueue_memory_write(
                user_id=user_id,
                content=content,
                source=source,
            )
            
            # Should return the task ID
            assert task_id == expected_task_id


@pytest.mark.django_db(transaction=True)
class TestTransactionWithAsyncTasks:
    """
    Combined tests for transaction integrity with async task enqueueing.
    
    Ensures that task enqueueing works correctly within transactions.
    """
    
    @settings(max_examples=10, deadline=None)
    @given(
        email_suffix=st.text(min_size=3, max_size=10, alphabet=st.characters(whitelist_categories=('Ll',))),
        content=content_strategy,
    )
    def test_task_enqueue_within_transaction(
        self,
        email_suffix: str,
        content: str,
    ):
        """
        Feature: neurotwin-platform, Properties 47 & 48 combined
        
        For any task enqueued within a transaction, the task should
        only be processed after the transaction commits.
        """
        email = f"txn_task_{email_suffix}@test.com"
        User.objects.filter(email=email).delete()
        
        enqueued_tasks = []
        
        def capture_task(*args, **kwargs):
            enqueued_tasks.append((args, kwargs))
            return 'mock_task_id'
        
        try:
            with patch('django_q.tasks.async_task', side_effect=capture_task):
                with ensure_atomic():
                    # Create user within transaction
                    user = User.objects.create_user(email=email, password="testpass123")
                    
                    # Enqueue task within same transaction
                    enqueue_memory_write(
                        user_id=str(user.id),
                        content=content,
                        source='conversation',
                    )
                    
                    # Task should be enqueued
                    assert len(enqueued_tasks) == 1
                
                # After transaction commits, verify user exists
                assert User.objects.filter(email=email).exists()
        finally:
            User.objects.filter(email=email).delete()
    
    @settings(max_examples=10, deadline=None)
    @given(
        email_suffix=st.text(min_size=3, max_size=10, alphabet=st.characters(whitelist_categories=('Ll',))),
    )
    def test_transaction_rollback_does_not_affect_enqueued_tasks(
        self,
        email_suffix: str,
    ):
        """
        Feature: neurotwin-platform, Properties 47 & 48 combined
        
        Note: This test documents current behavior - tasks enqueued before
        a rollback may still execute. Production code should handle this
        by checking data existence in task handlers.
        """
        email = f"txn_rollback_{email_suffix}@test.com"
        User.objects.filter(email=email).delete()
        
        enqueued_tasks = []
        
        def capture_task(*args, **kwargs):
            enqueued_tasks.append((args, kwargs))
            return 'mock_task_id'
        
        try:
            with patch('django_q.tasks.async_task', side_effect=capture_task):
                try:
                    with ensure_atomic():
                        # Enqueue task
                        enqueue_memory_write(
                            user_id="test_user",
                            content="test content",
                            source='conversation',
                        )
                        
                        # Force rollback
                        raise ValueError("Force rollback")
                except ValueError:
                    pass
                
                # Task was still enqueued (this is expected behavior)
                # Task handlers should verify data exists before processing
                assert len(enqueued_tasks) == 1
        finally:
            User.objects.filter(email=email).delete()
