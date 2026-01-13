"""
Property-based tests for audit logging service.

Feature: neurotwin-platform
Validates: Requirements 11.1-11.5

These tests use Hypothesis to verify audit logging properties hold
across a wide range of inputs.
"""

import pytest
import uuid
from hypothesis import given, strategies as st, assume
from datetime import timedelta
from django.utils import timezone

from apps.safety.services import AuditService
from apps.safety.models import AuditEntry, AuditOutcome, ActionType, IntegrationType
from apps.safety.dataclasses import AuditFilterCriteria
from apps.authentication.models import User


# Custom strategies for generating test data
action_type_strategy = st.sampled_from(list(ActionType.values))
integration_strategy = st.sampled_from(list(IntegrationType.values))
outcome_strategy = st.sampled_from(list(AuditOutcome.values))
cognitive_blend_strategy = st.integers(min_value=0, max_value=100)
reasoning_chain_strategy = st.text(min_size=0, max_size=100)


@pytest.fixture
def audit_service():
    """Provide an AuditService instance."""
    return AuditService()


@pytest.fixture
def test_user(db):
    """Create a test user for audit tests."""
    email = f"audit_test_{uuid.uuid4().hex[:8]}@example.com"
    user = User.objects.create_user(email=email, password="testpass123")
    yield user
    User.objects.filter(id=user.id).delete()



@pytest.mark.django_db(transaction=True)
class TestComprehensiveAuditLogging:
    """
    Property 38: Comprehensive audit logging
    
    *For any* Twin action, the audit system SHALL log: timestamp, action type,
    target integration, input data, outcome, cognitive blend value, and
    reasoning chain.
    
    **Validates: Requirements 11.1, 11.5**
    """
    
    @given(
        action_type=action_type_strategy,
        target_integration=integration_strategy,
        outcome=outcome_strategy,
        cognitive_blend=cognitive_blend_strategy,
        reasoning_chain=reasoning_chain_strategy
    )
    def test_audit_entry_contains_all_required_fields(
        self,
        test_user,
        audit_service,
        action_type: str,
        target_integration: str,
        outcome: str,
        cognitive_blend: int,
        reasoning_chain: str
    ):
        """
        Feature: neurotwin-platform, Property 38: Comprehensive audit logging
        
        For any Twin action, the logged audit entry should contain all
        required fields.
        """
        twin_id = str(uuid.uuid4())
        input_data = {'action': 'test', 'count': 1}
        
        entry = audit_service.log_action(
            user_id=str(test_user.id),
            action_type=action_type,
            target_integration=target_integration,
            input_data=input_data,
            outcome=outcome,
            cognitive_blend=cognitive_blend,
            reasoning_chain=reasoning_chain,
            is_twin_generated=True,
            twin_id=twin_id
        )
        
        # Verify all required fields
        assert entry.id is not None
        assert entry.timestamp is not None
        assert entry.action_type == action_type
        assert entry.target_integration == target_integration
        assert entry.outcome == outcome
        assert entry.cognitive_blend == cognitive_blend
        assert entry.reasoning_chain == reasoning_chain
        assert entry.checksum is not None
        assert len(entry.checksum) == 64  # SHA-256
    
    @given(action_type=action_type_strategy, outcome=outcome_strategy)
    def test_audit_entry_timestamp_is_current(
        self,
        test_user,
        audit_service,
        action_type: str,
        outcome: str
    ):
        """
        Feature: neurotwin-platform, Property 38: Comprehensive audit logging
        
        For any logged action, the timestamp should be approximately current.
        """
        before_log = timezone.now()
        
        entry = audit_service.log_action(
            user_id=str(test_user.id),
            action_type=action_type,
            outcome=outcome
        )
        
        after_log = timezone.now()
        
        assert entry.timestamp >= before_log
        assert entry.timestamp <= after_log



@pytest.mark.django_db(transaction=True)
class TestAuditLogImmutability:
    """
    Property 39: Audit log immutability
    
    *For any* audit log entry, the system SHALL detect any tampering through
    checksum verification.
    
    **Validates: Requirements 11.2**
    """
    
    @given(
        action_type=action_type_strategy,
        outcome=outcome_strategy,
        cognitive_blend=cognitive_blend_strategy
    )
    def test_integrity_verification_passes_for_unmodified(
        self,
        test_user,
        audit_service,
        action_type: str,
        outcome: str,
        cognitive_blend: int
    ):
        """
        Feature: neurotwin-platform, Property 39: Audit log immutability
        
        For any unmodified audit entry, integrity verification should pass.
        """
        entry = audit_service.log_action(
            user_id=str(test_user.id),
            action_type=action_type,
            outcome=outcome,
            cognitive_blend=cognitive_blend
        )
        
        assert audit_service.verify_log_integrity(str(entry.id))
        assert entry.verify_integrity()
    
    @given(
        action_type=action_type_strategy,
        outcome=outcome_strategy,
        original_blend=cognitive_blend_strategy,
        tampered_blend=cognitive_blend_strategy
    )
    def test_detects_cognitive_blend_tampering(
        self,
        test_user,
        audit_service,
        action_type: str,
        outcome: str,
        original_blend: int,
        tampered_blend: int
    ):
        """
        Feature: neurotwin-platform, Property 39: Audit log immutability
        
        For any audit entry where cognitive_blend is tampered with,
        integrity verification should fail.
        """
        assume(original_blend != tampered_blend)
        
        entry = audit_service.log_action(
            user_id=str(test_user.id),
            action_type=action_type,
            outcome=outcome,
            cognitive_blend=original_blend
        )
        
        assert entry.verify_integrity()
        
        # Tamper with cognitive_blend
        AuditEntry.objects.filter(id=entry.id).update(cognitive_blend=tampered_blend)
        entry.refresh_from_db()
        
        assert not entry.verify_integrity()
        assert not audit_service.verify_log_integrity(str(entry.id))
    
    @given(
        action_type=action_type_strategy,
        original_outcome=outcome_strategy,
        tampered_outcome=outcome_strategy
    )
    def test_detects_outcome_tampering(
        self,
        test_user,
        audit_service,
        action_type: str,
        original_outcome: str,
        tampered_outcome: str
    ):
        """
        Feature: neurotwin-platform, Property 39: Audit log immutability
        
        For any audit entry where outcome is tampered with,
        integrity verification should fail.
        """
        assume(original_outcome != tampered_outcome)
        
        entry = audit_service.log_action(
            user_id=str(test_user.id),
            action_type=action_type,
            outcome=original_outcome
        )
        
        assert entry.verify_integrity()
        
        # Tamper with outcome
        AuditEntry.objects.filter(id=entry.id).update(outcome=tampered_outcome)
        entry.refresh_from_db()
        
        assert not entry.verify_integrity()
    
    @given(action_type=action_type_strategy, outcome=outcome_strategy)
    def test_checksum_is_deterministic(
        self,
        test_user,
        audit_service,
        action_type: str,
        outcome: str
    ):
        """
        Feature: neurotwin-platform, Property 39: Audit log immutability
        
        For any audit entry, computing the checksum multiple times
        should produce the same result.
        """
        entry = audit_service.log_action(
            user_id=str(test_user.id),
            action_type=action_type,
            outcome=outcome,
            cognitive_blend=50
        )
        
        checksum1 = entry.compute_checksum()
        checksum2 = entry.compute_checksum()
        checksum3 = entry.compute_checksum()
        
        assert checksum1 == checksum2 == checksum3
        assert checksum1 == entry.checksum



@pytest.mark.django_db(transaction=True)
class TestAuditLogFilterability:
    """
    Property 40: Audit log filterability
    
    *For any* filter criteria (date range, action type, integration), the
    system SHALL return matching audit entries.
    
    **Validates: Requirements 11.3**
    """
    
    @given(action_type=action_type_strategy, outcome=outcome_strategy)
    def test_filter_by_action_type(
        self,
        test_user,
        audit_service,
        action_type: str,
        outcome: str
    ):
        """
        Feature: neurotwin-platform, Property 40: Audit log filterability
        
        For any action type filter, only entries with that action type
        should be returned.
        """
        # Create entries with target action type
        for i in range(3):
            audit_service.log_action(
                user_id=str(test_user.id),
                action_type=action_type,
                outcome=outcome
            )
        
        # Create entries with different action type
        other_action = ActionType.READ if action_type != ActionType.READ else ActionType.WRITE
        for i in range(2):
            audit_service.log_action(
                user_id=str(test_user.id),
                action_type=other_action,
                outcome=outcome
            )
        
        filters = AuditFilterCriteria(action_type=action_type)
        results = audit_service.get_audit_history(str(test_user.id), filters=filters)
        
        # At least 3 entries should match (may have more from previous iterations)
        assert len(results) >= 3
        # All returned entries must match the filter
        for entry in results:
            assert entry.action_type == action_type
    
    @given(target_integration=integration_strategy, outcome=outcome_strategy)
    def test_filter_by_target_integration(
        self,
        test_user,
        audit_service,
        target_integration: str,
        outcome: str
    ):
        """
        Feature: neurotwin-platform, Property 40: Audit log filterability
        
        For any target integration filter, only entries with that integration
        should be returned.
        """
        # Create entries with target integration
        for i in range(3):
            audit_service.log_action(
                user_id=str(test_user.id),
                action_type=ActionType.READ,
                target_integration=target_integration,
                outcome=outcome
            )
        
        # Create entries with different integration
        other_integration = IntegrationType.GMAIL if target_integration != IntegrationType.GMAIL else IntegrationType.SLACK
        for i in range(2):
            audit_service.log_action(
                user_id=str(test_user.id),
                action_type=ActionType.READ,
                target_integration=other_integration,
                outcome=outcome
            )
        
        filters = AuditFilterCriteria(target_integration=target_integration)
        results = audit_service.get_audit_history(str(test_user.id), filters=filters)
        
        # At least 3 entries should match (may have more from previous iterations)
        assert len(results) >= 3
        # All returned entries must match the filter
        for entry in results:
            assert entry.target_integration == target_integration
    
    @given(target_outcome=outcome_strategy, action_type=action_type_strategy)
    def test_filter_by_outcome(
        self,
        test_user,
        audit_service,
        target_outcome: str,
        action_type: str
    ):
        """
        Feature: neurotwin-platform, Property 40: Audit log filterability
        
        For any outcome filter, only entries with that outcome should be returned.
        """
        # Create entries with target outcome
        for i in range(3):
            audit_service.log_action(
                user_id=str(test_user.id),
                action_type=action_type,
                outcome=target_outcome
            )
        
        # Create entries with different outcome
        other_outcome = AuditOutcome.SUCCESS if target_outcome != AuditOutcome.SUCCESS else AuditOutcome.FAILURE
        for i in range(2):
            audit_service.log_action(
                user_id=str(test_user.id),
                action_type=action_type,
                outcome=other_outcome
            )
        
        filters = AuditFilterCriteria(outcome=target_outcome)
        results = audit_service.get_audit_history(str(test_user.id), filters=filters)
        
        # At least 3 entries should match (may have more from previous iterations)
        assert len(results) >= 3
        # All returned entries must match the filter
        for entry in results:
            assert entry.outcome == target_outcome
    
    @given(action_type=action_type_strategy)
    def test_filter_by_date_range(
        self,
        test_user,
        audit_service,
        action_type: str
    ):
        """
        Feature: neurotwin-platform, Property 40: Audit log filterability
        
        For any date range filter, only entries within that range should be returned.
        """
        now = timezone.now()
        
        # Create entries for today
        for i in range(3):
            audit_service.log_action(
                user_id=str(test_user.id),
                action_type=action_type,
                outcome=AuditOutcome.SUCCESS
            )
        
        start_date = now - timedelta(hours=1)
        end_date = now + timedelta(hours=1)
        
        filters = AuditFilterCriteria(start_date=start_date, end_date=end_date)
        results = audit_service.get_audit_history(str(test_user.id), filters=filters)
        
        # At least 3 entries should match (may have more from previous iterations)
        assert len(results) >= 3
        # All returned entries must be within the date range
        for entry in results:
            assert entry.timestamp >= start_date
            assert entry.timestamp <= end_date
    
    @given(
        action_type=action_type_strategy,
        target_integration=integration_strategy,
        outcome=outcome_strategy
    )
    def test_filter_by_multiple_criteria(
        self,
        test_user,
        audit_service,
        action_type: str,
        target_integration: str,
        outcome: str
    ):
        """
        Feature: neurotwin-platform, Property 40: Audit log filterability
        
        For any combination of filter criteria, only entries matching ALL
        criteria should be returned.
        """
        # Create entries matching all criteria
        for i in range(2):
            audit_service.log_action(
                user_id=str(test_user.id),
                action_type=action_type,
                target_integration=target_integration,
                outcome=outcome
            )
        
        # Create entry with different action
        other_action = ActionType.READ if action_type != ActionType.READ else ActionType.WRITE
        audit_service.log_action(
            user_id=str(test_user.id),
            action_type=other_action,
            target_integration=target_integration,
            outcome=outcome
        )
        
        # Create entry with different integration
        other_integration = IntegrationType.GMAIL if target_integration != IntegrationType.GMAIL else IntegrationType.SLACK
        audit_service.log_action(
            user_id=str(test_user.id),
            action_type=action_type,
            target_integration=other_integration,
            outcome=outcome
        )
        
        filters = AuditFilterCriteria(
            action_type=action_type,
            target_integration=target_integration,
            outcome=outcome
        )
        results = audit_service.get_audit_history(str(test_user.id), filters=filters)
        
        # At least 2 entries should match (may have more from previous iterations)
        assert len(results) >= 2
        # All returned entries must match ALL filter criteria
        for entry in results:
            assert entry.action_type == action_type
            assert entry.target_integration == target_integration
            assert entry.outcome == outcome
    
    @given(action_type=action_type_strategy, outcome=outcome_strategy)
    def test_results_ordered_by_timestamp_descending(
        self,
        test_user,
        audit_service,
        action_type: str,
        outcome: str
    ):
        """
        Feature: neurotwin-platform, Property 40: Audit log filterability
        
        For any query, results should be ordered by timestamp descending.
        """
        for i in range(5):
            audit_service.log_action(
                user_id=str(test_user.id),
                action_type=action_type,
                outcome=outcome
            )
        
        results = audit_service.get_audit_history(str(test_user.id))
        
        assert len(results) >= 5
        for i in range(len(results) - 1):
            assert results[i].timestamp >= results[i + 1].timestamp

