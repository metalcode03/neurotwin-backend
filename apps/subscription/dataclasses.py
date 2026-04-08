"""
Data classes for subscription service.

These provide structured types for subscription operations.
Requirements: 3.1, 3.2, 3.3, 3.4, 3.5
"""

from dataclasses import dataclass
from typing import List


@dataclass
class TierFeatures:
    """
    Features available for a subscription tier.
    
    Requirements: 3.2, 3.3, 3.4, 3.5
    """
    
    tier_name: str
    available_models: List[str]
    has_cognitive_learning: bool
    has_voice_twin: bool
    has_autonomous_workflows: bool
    has_custom_models: bool
    monthly_workflow_limit: int | None  # None = unlimited
    
    @classmethod
    def free_tier(cls) -> 'TierFeatures':
        """
        Free tier features.
        
        Requirements: 3.2, 18.4
        - Access to Cerebras, Gemini 2.5 Flash, and Mistral models
        - Chat and light memory features
        - No autonomous workflows
        """
        return cls(
            tier_name='free',
            available_models=['cerebras', 'gemini-2.5-flash', 'mistral'],
            has_cognitive_learning=False,
            has_voice_twin=False,
            has_autonomous_workflows=False,
            has_custom_models=False,
            monthly_workflow_limit=0,
        )
    
    @classmethod
    def pro_tier(cls) -> 'TierFeatures':
        """
        Pro tier features.
        
        Requirements: 3.3, 18.4
        - Access to Cerebras, Gemini 2.5 Flash, Gemini 2.5 Pro, Gemini 3 Pro, Mistral
        - Full cognitive learning capabilities
        - Autonomous workflows (50/month limit)
        """
        return cls(
            tier_name='pro',
            available_models=['cerebras', 'gemini-2.5-flash', 'gemini-2.5-pro', 'gemini-3-pro', 'mistral'],
            has_cognitive_learning=True,
            has_voice_twin=False,
            has_autonomous_workflows=True,
            has_custom_models=False,
            monthly_workflow_limit=2000,
        )
    
    @classmethod
    def twin_plus_tier(cls) -> 'TierFeatures':
        """
        Twin+ tier features.
        
        Requirements: 3.4, 18.4
        - Pro features plus Voice_Twin functionality
        - Autonomous workflows (200/month limit)
        """
        return cls(
            tier_name='twin_plus',
            available_models=['cerebras', 'gemini-2.5-flash', 'gemini-2.5-pro', 'gemini-3-pro', 'mistral'],
            has_cognitive_learning=True,
            has_voice_twin=True,
            has_autonomous_workflows=True,
            has_custom_models=False,
            monthly_workflow_limit=12000,
        )
    
    @classmethod
    def executive_tier(cls) -> 'TierFeatures':
        """
        Executive tier features.
        
        Requirements: 3.5, 18.4
        - Twin+ features plus custom model options
        - Unlimited autonomous workflows
        - Access to all models including Gemini 3.1 Pro
        """
        return cls(
            tier_name='executive',
            available_models=['cerebras', 'gemini-2.5-flash', 'gemini-2.5-pro', 'gemini-3-pro', 'gemini-3.1-pro', 'mistral'],
            has_cognitive_learning=True,
            has_voice_twin=True,
            has_autonomous_workflows=True,
            has_custom_models=True,
            monthly_workflow_limit=None,
        )
