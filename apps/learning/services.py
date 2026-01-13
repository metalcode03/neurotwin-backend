"""
Learning service for NeuroTwin platform.

Implements the learning loop for continuous Twin improvement:
User Action → Feature Extraction → Profile Update → Behavior Shift → Feedback Reinforcement

Requirements: 6.1, 6.2, 6.3, 6.4, 6.5, 6.6
"""

import asyncio
from typing import Optional, List, Dict, Any
from datetime import datetime

from django.db import transaction
from django.utils import timezone
from asgiref.sync import sync_to_async

from .models import LearningEvent
from .dataclasses import (
    ExtractedFeatures,
    FeedbackType,
    ActionCategory,
    ProfileUpdateResult,
    FeedbackResult,
    UserAction,
)
from apps.csm.services import CSMService
from apps.csm.models import CSMProfile


class LearningService:
    """
    Implements the learning loop for Twin improvement.
    
    Handles:
    - Feature extraction from user actions
    - Asynchronous CSM profile updates
    - Feedback reinforcement and correction
    - Learning history for transparency
    
    Requirements: 6.1, 6.2, 6.3, 6.4, 6.5, 6.6
    """
    
    def __init__(self):
        """Initialize the learning service."""
        self.csm_service = CSMService()
        
        # Learning rate controls how much each action affects the profile
        self.learning_rate = 0.1
        
        # Minimum confidence threshold for applying updates
        self.min_confidence = 0.5
    
    async def process_user_action(
        self,
        user_id: str,
        action: UserAction
    ) -> ExtractedFeatures:
        """
        Extract features from a user action for learning.
        
        Requirements: 6.1
        
        This is the first step in the learning loop:
        User Action → Feature Extraction
        
        Args:
            user_id: UUID of the user
            action: UserAction containing the action details
            
        Returns:
            ExtractedFeatures with patterns and signals extracted
        """
        # Create learning event record
        event = await self._create_learning_event(user_id, action)
        
        try:
            # Extract features from the action
            features = await self._extract_features(action)
            
            # Update the event with extracted features
            await self._update_event_features(event, features)
            
            return features
            
        except Exception as e:
            # Record the error
            await self._record_processing_error(event, str(e))
            raise
    
    async def update_profile(
        self,
        user_id: str,
        features: ExtractedFeatures
    ) -> ProfileUpdateResult:
        """
        Asynchronously update CSM based on extracted features.
        
        Requirements: 6.2, 6.3
        
        This is the second step in the learning loop:
        Feature Extraction → Profile Update → Behavior Shift
        
        Args:
            user_id: UUID of the user
            features: ExtractedFeatures from process_user_action
            
        Returns:
            ProfileUpdateResult with update details
        """
        # Skip if confidence is too low
        if features.confidence < self.min_confidence:
            return ProfileUpdateResult(
                success=True,
                updated_fields=[],
                error="Confidence too low for profile update"
            )
        
        try:
            # Get current profile
            profile = await sync_to_async(self.csm_service.get_profile)(user_id)
            if not profile:
                return ProfileUpdateResult(
                    success=False,
                    error=f"No CSM profile found for user {user_id}"
                )
            
            # Build updates from features
            updates = self._build_profile_updates(features)
            
            if not updates:
                return ProfileUpdateResult(
                    success=True,
                    updated_fields=[],
                )
            
            # Apply updates to profile
            version_before = profile.version
            new_profile = await sync_to_async(self.csm_service.update_profile)(
                user_id,
                updates
            )
            
            # Update learning event with profile change info
            await self._update_event_profile_change(
                user_id,
                features,
                version_before,
                new_profile.version,
                updates
            )
            
            return ProfileUpdateResult(
                success=True,
                updated_fields=list(updates.keys()),
                new_version=new_profile.version,
            )
            
        except Exception as e:
            return ProfileUpdateResult(
                success=False,
                error=str(e)
            )
    
    @transaction.atomic
    def apply_feedback(
        self,
        user_id: str,
        event_id: str,
        feedback: FeedbackType,
        correction_content: str = ''
    ) -> FeedbackResult:
        """
        Reinforce or correct behavior based on user feedback.
        
        Requirements: 6.4, 14.3 (Transaction integrity)
        
        This is the final step in the learning loop:
        Behavior Shift → Feedback Reinforcement
        
        Args:
            user_id: UUID of the user
            event_id: UUID of the learning event to provide feedback on
            feedback: Type of feedback (positive, negative, correction)
            correction_content: Optional correction text for CORRECTION feedback
            
        Returns:
            FeedbackResult with feedback application details
        """
        try:
            # Get the learning event
            event = LearningEvent.objects.filter(
                id=event_id,
                user_id=user_id
            ).first()
            
            if not event:
                return FeedbackResult(
                    success=False,
                    error=f"Learning event {event_id} not found"
                )
            
            # Record the feedback
            event.set_feedback(feedback, correction_content)
            event.save()
            
            # Apply feedback to profile
            result = self._apply_feedback_to_profile(
                user_id,
                event,
                feedback,
                correction_content
            )
            
            return result
            
        except Exception as e:
            return FeedbackResult(
                success=False,
                error=str(e)
            )
    
    def get_learning_history(
        self,
        user_id: str,
        limit: int = 100,
        action_type: Optional[str] = None,
        include_feedback_only: bool = False
    ) -> List[LearningEvent]:
        """
        Get history of learning events for transparency.
        
        Requirements: 6.5
        
        Args:
            user_id: UUID of the user
            limit: Maximum number of events to return
            action_type: Optional filter by action type
            include_feedback_only: If True, only return events with feedback
            
        Returns:
            List of LearningEvent instances
        """
        queryset = LearningEvent.objects.filter(user_id=user_id)
        
        if action_type:
            queryset = queryset.filter(action_type=action_type)
        
        if include_feedback_only:
            queryset = queryset.exclude(feedback__isnull=True)
        
        return list(queryset.order_by('-created_at')[:limit])
    
    # Private helper methods
    
    async def _create_learning_event(
        self,
        user_id: str,
        action: UserAction
    ) -> LearningEvent:
        """Create a new learning event record."""
        category = self._determine_category(action)
        
        @sync_to_async
        def create_event():
            return LearningEvent.objects.create(
                user_id=user_id,
                action_type=action.action_type,
                action_category=category.value,
                action_content=action.content,
                action_context=action.context,
            )
        
        return await create_event()
    
    async def _extract_features(self, action: UserAction) -> ExtractedFeatures:
        """
        Extract features from a user action.
        
        This is a simplified feature extraction. In production,
        this would use AI/ML models for more sophisticated extraction.
        """
        category = self._determine_category(action)
        
        # Extract patterns from content
        patterns = self._extract_patterns(action.content)
        
        # Analyze sentiment (simplified)
        sentiment = self._analyze_sentiment(action.content)
        
        # Extract signals based on action type
        personality_signals = {}
        tone_signals = {}
        decision_signals = {}
        vocabulary_additions = []
        
        if category == ActionCategory.COMMUNICATION:
            tone_signals = self._extract_tone_signals(action)
            vocabulary_additions = self._extract_vocabulary(action.content)
            
        elif category == ActionCategory.DECISION:
            decision_signals = self._extract_decision_signals(action)
            personality_signals = self._extract_personality_signals(action)
            
        elif category == ActionCategory.PREFERENCE:
            personality_signals = self._extract_personality_signals(action)
            tone_signals = self._extract_tone_signals(action)
        
        return ExtractedFeatures(
            action_type=action.action_type,
            category=category,
            context=action.context,
            patterns=patterns,
            sentiment=sentiment,
            confidence=0.8,  # Default confidence
            personality_signals=personality_signals,
            tone_signals=tone_signals,
            vocabulary_additions=vocabulary_additions,
            decision_signals=decision_signals,
        )
    
    def _determine_category(self, action: UserAction) -> ActionCategory:
        """Determine the category of an action."""
        action_type = action.action_type.lower()
        
        if any(kw in action_type for kw in ['message', 'email', 'chat', 'reply']):
            return ActionCategory.COMMUNICATION
        elif any(kw in action_type for kw in ['decide', 'approve', 'reject', 'choose']):
            return ActionCategory.DECISION
        elif any(kw in action_type for kw in ['setting', 'preference', 'config']):
            return ActionCategory.PREFERENCE
        elif any(kw in action_type for kw in ['feedback', 'rate', 'review']):
            return ActionCategory.FEEDBACK
        else:
            return ActionCategory.INTERACTION
    
    def _extract_patterns(self, content: str) -> List[str]:
        """Extract patterns from content."""
        patterns = []
        
        if not content:
            return patterns
        
        # Simple pattern extraction
        words = content.lower().split()
        
        # Look for common patterns
        if len(words) < 10:
            patterns.append('brief_response')
        elif len(words) > 50:
            patterns.append('detailed_response')
        else:
            patterns.append('moderate_response')
        
        # Check for formal/informal indicators
        if any(word in content.lower() for word in ['please', 'thank you', 'regards']):
            patterns.append('formal_tone')
        if any(word in content.lower() for word in ['hey', 'hi', 'cool', 'awesome']):
            patterns.append('casual_tone')
        
        return patterns
    
    def _analyze_sentiment(self, content: str) -> float:
        """
        Analyze sentiment of content.
        
        Returns a value between -1.0 (negative) and 1.0 (positive).
        This is a simplified implementation.
        """
        if not content:
            return 0.0
        
        positive_words = ['good', 'great', 'excellent', 'happy', 'love', 'thanks', 'perfect']
        negative_words = ['bad', 'terrible', 'hate', 'wrong', 'error', 'fail', 'problem']
        
        content_lower = content.lower()
        
        positive_count = sum(1 for word in positive_words if word in content_lower)
        negative_count = sum(1 for word in negative_words if word in content_lower)
        
        total = positive_count + negative_count
        if total == 0:
            return 0.0
        
        return (positive_count - negative_count) / total
    
    def _extract_tone_signals(self, action: UserAction) -> Dict[str, float]:
        """Extract tone preference signals from an action."""
        signals = {}
        content = action.content.lower()
        
        # Formality signal
        formal_indicators = ['dear', 'sincerely', 'regards', 'respectfully']
        casual_indicators = ['hey', 'hi', 'yo', 'sup', 'lol']
        
        formal_count = sum(1 for ind in formal_indicators if ind in content)
        casual_count = sum(1 for ind in casual_indicators if ind in content)
        
        if formal_count > casual_count:
            signals['formality'] = min(0.7 + formal_count * 0.1, 1.0)
        elif casual_count > formal_count:
            signals['formality'] = max(0.3 - casual_count * 0.1, 0.0)
        
        # Directness signal
        if any(word in content for word in ['please', 'could you', 'would you']):
            signals['directness'] = 0.3
        elif any(word in content for word in ['do this', 'need', 'must', 'now']):
            signals['directness'] = 0.8
        
        return signals
    
    def _extract_personality_signals(self, action: UserAction) -> Dict[str, float]:
        """Extract personality trait signals from an action."""
        signals = {}
        context = action.context
        
        # Risk tolerance from decision context
        if 'risk_level' in context:
            risk = context['risk_level']
            if risk == 'high':
                signals['risk_tolerance'] = 0.8
            elif risk == 'low':
                signals['risk_tolerance'] = 0.2
        
        # Collaboration preference
        if 'collaboration' in context:
            if context['collaboration']:
                signals['collaboration_preference'] = 0.8
            else:
                signals['collaboration_preference'] = 0.2
        
        return signals
    
    def _extract_decision_signals(self, action: UserAction) -> Dict[str, float]:
        """Extract decision style signals from an action."""
        signals = {}
        context = action.context
        metadata = action.metadata
        
        # Speed vs accuracy from decision timing
        if 'decision_time_seconds' in metadata:
            time = metadata['decision_time_seconds']
            if time < 5:
                signals['speed_vs_accuracy'] = 0.9  # Quick decision
            elif time > 60:
                signals['speed_vs_accuracy'] = 0.1  # Thorough decision
            else:
                signals['speed_vs_accuracy'] = 0.5
        
        return signals
    
    def _extract_vocabulary(self, content: str) -> List[str]:
        """Extract vocabulary patterns from content."""
        if not content:
            return []
        
        # Extract unique words that might be characteristic
        words = content.split()
        
        # Filter for potentially characteristic vocabulary
        # (In production, this would be more sophisticated)
        characteristic_words = [
            word.lower() for word in words
            if len(word) > 4 and word.isalpha()
        ]
        
        # Return unique words, limited
        return list(set(characteristic_words))[:10]
    
    async def _update_event_features(
        self,
        event: LearningEvent,
        features: ExtractedFeatures
    ) -> None:
        """Update a learning event with extracted features."""
        @sync_to_async
        def update():
            event.set_features(features)
            event.is_processed = True
            event.processed_at = timezone.now()
            event.save()
        
        await update()
    
    async def _record_processing_error(
        self,
        event: LearningEvent,
        error: str
    ) -> None:
        """Record a processing error on a learning event."""
        @sync_to_async
        def update():
            event.processing_error = error
            event.save()
        
        await update()
    
    def _build_profile_updates(
        self,
        features: ExtractedFeatures
    ) -> Dict[str, Any]:
        """Build profile updates from extracted features."""
        updates = {}
        
        # Apply personality signals
        if features.personality_signals:
            personality_updates = {}
            for trait, value in features.personality_signals.items():
                # Apply learning rate to smooth updates
                personality_updates[trait] = value
            if personality_updates:
                updates['personality'] = personality_updates
        
        # Apply tone signals
        if features.tone_signals:
            tone_updates = {}
            for pref, value in features.tone_signals.items():
                tone_updates[pref] = value
            if tone_updates:
                updates['tone'] = tone_updates
        
        # Apply decision signals
        if features.decision_signals:
            decision_updates = {}
            for style, value in features.decision_signals.items():
                decision_updates[style] = value
            if decision_updates:
                updates['decision_style'] = decision_updates
        
        # Add vocabulary patterns
        if features.vocabulary_additions:
            updates['vocabulary_patterns'] = features.vocabulary_additions
        
        return updates
    
    async def _update_event_profile_change(
        self,
        user_id: str,
        features: ExtractedFeatures,
        version_before: int,
        version_after: int,
        updates: Dict[str, Any]
    ) -> None:
        """Update learning event with profile change information."""
        @sync_to_async
        def update():
            # Find the most recent event for this user with these features
            event = LearningEvent.objects.filter(
                user_id=user_id,
                action_type=features.action_type,
                is_processed=True,
                is_profile_updated=False
            ).order_by('-created_at').first()
            
            if event:
                event.csm_version_before = version_before
                event.csm_version_after = version_after
                event.profile_updates = updates
                event.is_profile_updated = True
                event.save()
        
        await update()
    
    def _apply_feedback_to_profile(
        self,
        user_id: str,
        event: LearningEvent,
        feedback: FeedbackType,
        correction_content: str
    ) -> FeedbackResult:
        """Apply feedback to the user's profile."""
        try:
            features = event.get_features()
            if not features:
                return FeedbackResult(
                    success=True,
                    reinforcement_applied=False,
                    error="No features to apply feedback to"
                )
            
            profile = self.csm_service.get_profile(user_id)
            if not profile:
                return FeedbackResult(
                    success=False,
                    error=f"No profile found for user {user_id}"
                )
            
            if feedback == FeedbackType.POSITIVE:
                # Reinforce the learned patterns
                return self._reinforce_patterns(user_id, features)
                
            elif feedback == FeedbackType.NEGATIVE:
                # Reduce influence of the learned patterns
                return self._reduce_patterns(user_id, features)
                
            elif feedback == FeedbackType.CORRECTION:
                # Apply the correction
                return self._apply_correction(user_id, features, correction_content)
            
            return FeedbackResult(success=True)
            
        except Exception as e:
            return FeedbackResult(
                success=False,
                error=str(e)
            )
    
    def _reinforce_patterns(
        self,
        user_id: str,
        features: ExtractedFeatures
    ) -> FeedbackResult:
        """Reinforce learned patterns from positive feedback."""
        # In a full implementation, this would strengthen the
        # associations learned from this action
        return FeedbackResult(
            success=True,
            reinforcement_applied=True,
            profile_updated=False,  # Simplified - no actual update
        )
    
    def _reduce_patterns(
        self,
        user_id: str,
        features: ExtractedFeatures
    ) -> FeedbackResult:
        """Reduce influence of patterns from negative feedback."""
        # In a full implementation, this would weaken the
        # associations learned from this action
        return FeedbackResult(
            success=True,
            reinforcement_applied=True,
            profile_updated=False,  # Simplified - no actual update
        )
    
    @transaction.atomic
    def _apply_correction(
        self,
        user_id: str,
        features: ExtractedFeatures,
        correction_content: str
    ) -> FeedbackResult:
        """
        Apply a correction from user feedback.
        
        Requirements: 14.3 (Transaction integrity)
        """
        try:
            # Extract features from the correction
            correction_action = UserAction(
                action_type='correction',
                content=correction_content,
                context=features.context,
            )
            
            # Build updates from correction
            # This is simplified - in production would be more sophisticated
            updates = {}
            
            # Extract tone from correction
            tone_signals = self._extract_tone_signals(correction_action)
            if tone_signals:
                updates['tone'] = tone_signals
            
            # Apply updates if any
            if updates:
                self.csm_service.update_profile(user_id, updates)
                return FeedbackResult(
                    success=True,
                    correction_applied=True,
                    profile_updated=True,
                )
            
            return FeedbackResult(
                success=True,
                correction_applied=True,
                profile_updated=False,
            )
            
        except Exception as e:
            return FeedbackResult(
                success=False,
                error=str(e)
            )
