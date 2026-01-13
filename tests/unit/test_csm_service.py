"""
Unit tests for CSM service.

Tests the CSMService methods for profile creation, updates, versioning, and rollback.
"""

import pytest
from apps.csm.services import CSMService
from apps.csm.dataclasses import QuestionnaireResponse
from apps.csm.models import CSMProfile, CSMChangeLog
from apps.authentication.models import User


def create_test_user(email_suffix: str) -> User:
    """Create a test user with unique email."""
    email = f"csm_unit_test_{email_suffix}@example.com"
    User.objects.filter(email=email).delete()
    return User.objects.create_user(email=email, password="testpass123")


@pytest.fixture
def csm_service():
    """Provide a CSMService instance."""
    return CSMService()


@pytest.fixture
def sample_questionnaire():
    """Provide sample questionnaire responses."""
    return QuestionnaireResponse(
        communication_style={
            'openness': 0.8,
            'extraversion': 0.6,
            'agreeableness': 0.7,
            'formality': 0.4,
            'warmth': 0.8,
            'directness': 0.6,
            'preferred_greeting': 'Hey there',
            'sign_off_style': 'Cheers',
        },
        decision_patterns={
            'conscientiousness': 0.7,
            'risk_tolerance': 0.5,
            'speed_vs_accuracy': 0.4,
            'collaboration_preference': 0.8,
        },
        preferences={
            'neuroticism': 0.3,
            'humor_level': 0.5,
            'response_length': 'moderate',
            'emoji_usage': 'minimal',
            'vocabulary_patterns': ['technical', 'friendly'],
        }
    )


@pytest.mark.django_db(transaction=True)
class TestCSMService:
    """Tests for CSMService."""
    
    def test_create_from_questionnaire(self, csm_service, sample_questionnaire):
        """Test creating a CSM profile from questionnaire responses."""
        user = create_test_user("create_q")
        
        try:
            profile = csm_service.create_from_questionnaire(
                str(user.id), 
                sample_questionnaire
            )
            
            assert profile is not None
            assert profile.version == 1
            assert profile.is_current is True
            
            # Verify profile data
            data = profile.get_profile_data()
            assert data.personality.openness == 0.8
            assert data.tone.warmth == 0.8
            assert data.communication.preferred_greeting == 'Hey there'
            assert 'technical' in data.vocabulary_patterns
        finally:
            User.objects.filter(id=user.id).delete()
    
    def test_get_profile(self, csm_service, sample_questionnaire):
        """Test retrieving current profile."""
        user = create_test_user("get_profile")
        
        try:
            # Create profile
            csm_service.create_from_questionnaire(str(user.id), sample_questionnaire)
            
            # Retrieve it
            profile = csm_service.get_profile(str(user.id))
            
            assert profile is not None
            assert profile.is_current is True
        finally:
            User.objects.filter(id=user.id).delete()
    
    def test_update_profile(self, csm_service, sample_questionnaire):
        """Test updating a profile creates new version."""
        user = create_test_user("update_profile")
        
        try:
            # Create initial profile
            csm_service.create_from_questionnaire(str(user.id), sample_questionnaire)
            
            # Update it
            updated = csm_service.update_profile(
                str(user.id),
                {'personality': {'openness': 0.9}}
            )
            
            assert updated.version == 2
            assert updated.is_current is True
            
            # Verify old version is not current
            old = CSMProfile.objects.get(user_id=user.id, version=1)
            assert old.is_current is False
            
            # Verify update was applied
            data = updated.get_profile_data()
            assert data.personality.openness == 0.9
        finally:
            User.objects.filter(id=user.id).delete()
    
    def test_get_version_history(self, csm_service, sample_questionnaire):
        """Test getting version history."""
        user = create_test_user("version_history")
        
        try:
            # Create and update profile
            csm_service.create_from_questionnaire(str(user.id), sample_questionnaire)
            csm_service.update_profile(str(user.id), {'personality': {'openness': 0.9}})
            csm_service.update_profile(str(user.id), {'tone': {'warmth': 0.9}})
            
            # Get history
            history = csm_service.get_version_history(str(user.id))
            
            assert len(history) == 3
            assert history[0].version == 3  # Most recent first
            assert history[1].version == 2
            assert history[2].version == 1
        finally:
            User.objects.filter(id=user.id).delete()
    
    def test_rollback_to_version(self, csm_service, sample_questionnaire):
        """Test rolling back to a previous version."""
        user = create_test_user("rollback")
        
        try:
            # Create and update profile
            csm_service.create_from_questionnaire(str(user.id), sample_questionnaire)
            csm_service.update_profile(str(user.id), {'personality': {'openness': 0.9}})
            
            # Rollback to version 1
            rolled_back = csm_service.rollback_to_version(str(user.id), 1)
            
            # Should create new version with old data
            assert rolled_back.version == 3
            assert rolled_back.is_current is True
            
            # Verify data matches version 1
            data = rolled_back.get_profile_data()
            assert data.personality.openness == 0.8  # Original value
            
            # Verify change log
            log = CSMChangeLog.objects.filter(
                profile=rolled_back,
                change_type='rollback'
            ).first()
            assert log is not None
            assert log.change_summary['rolled_back_to'] == 1
        finally:
            User.objects.filter(id=user.id).delete()
    
    def test_apply_blend_low(self, csm_service, sample_questionnaire):
        """Test apply_blend with low blend (0-30%)."""
        user = create_test_user("blend_low")
        
        try:
            profile = csm_service.create_from_questionnaire(
                str(user.id), 
                sample_questionnaire
            )
            
            result = csm_service.apply_blend(profile, 20)
            
            assert result['mode'] == 'ai_logic'
            assert result['requires_confirmation'] is False
            assert result['personality_weight'] == 0.2
        finally:
            User.objects.filter(id=user.id).delete()
    
    def test_apply_blend_medium(self, csm_service, sample_questionnaire):
        """Test apply_blend with medium blend (31-70%)."""
        user = create_test_user("blend_medium")
        
        try:
            profile = csm_service.create_from_questionnaire(
                str(user.id), 
                sample_questionnaire
            )
            
            result = csm_service.apply_blend(profile, 50)
            
            assert result['mode'] == 'balanced'
            assert result['requires_confirmation'] is False
            assert result['personality_weight'] == 0.5
        finally:
            User.objects.filter(id=user.id).delete()
    
    def test_apply_blend_high(self, csm_service, sample_questionnaire):
        """Test apply_blend with high blend (71-100%)."""
        user = create_test_user("blend_high")
        
        try:
            profile = csm_service.create_from_questionnaire(
                str(user.id), 
                sample_questionnaire
            )
            
            result = csm_service.apply_blend(profile, 85)
            
            assert result['mode'] == 'personality_heavy'
            assert result['requires_confirmation'] is True
            assert result['personality_weight'] == 0.85
        finally:
            User.objects.filter(id=user.id).delete()
    
    def test_apply_blend_invalid(self, csm_service, sample_questionnaire):
        """Test apply_blend with invalid blend value."""
        user = create_test_user("blend_invalid")
        
        try:
            profile = csm_service.create_from_questionnaire(
                str(user.id), 
                sample_questionnaire
            )
            
            with pytest.raises(ValueError):
                csm_service.apply_blend(profile, 150)
            
            with pytest.raises(ValueError):
                csm_service.apply_blend(profile, -10)
        finally:
            User.objects.filter(id=user.id).delete()
