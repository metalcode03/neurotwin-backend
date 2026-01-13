"""
AI Service for NeuroTwin platform.

Provides centralized AI model interaction including:
- Response generation with CSM and blend application
- Feature extraction for learning
- Embedding generation for memory

Requirements: 2.3, 4.2, 4.3, 4.4, 4.5, 5.2, 6.1
"""

import os
from typing import List, Dict, Any, Optional
from dataclasses import asdict

from .dataclasses import (
    AIResponse,
    AIConfig,
    AIModel,
    BlendMode,
    BlendedProfile,
)


class AIService:
    """
    Centralized AI model interaction service.
    
    Handles response generation with personality matching,
    feature extraction for learning, and embedding generation.
    
    Requirements: 2.3, 4.2, 4.3, 4.4, 4.5, 5.2, 6.1
    """
    
    def __init__(self, config: Optional[AIConfig] = None):
        """
        Initialize the AI service.
        
        Args:
            config: Optional AIConfig, uses defaults if not provided
        """
        self.config = config or AIConfig()
        self._client = None
    
    def _get_client(self):
        """
        Get or create the Google GenAI client.
        
        Returns:
            Google GenAI client instance
        """
        if self._client is None:
            try:
                from google import genai
                api_key = os.environ.get('GOOGLE_API_KEY') or os.environ.get('GEMINI_API_KEY')
                if api_key:
                    self._client = genai.Client(api_key=api_key)
                else:
                    # Return a mock client for testing
                    self._client = MockAIClient()
            except ImportError:
                # Return a mock client if google-genai is not installed
                self._client = MockAIClient()
        return self._client
    
    def apply_blend(
        self,
        csm_profile_data: Dict[str, Any],
        blend: int
    ) -> BlendedProfile:
        """
        Apply cognitive blend to CSM profile for response generation.
        
        Requirements: 4.2, 4.3, 4.4, 4.5
        
        The blend value (0-100) controls how much personality vs AI logic:
        - 0-30%: Pure AI logic with minimal personality mimicry
        - 31-70%: Balanced blend of user personality + AI reasoning
        - 71-100%: Heavy personality mimicry, requires confirmation
        
        Args:
            csm_profile_data: CSM profile data dictionary
            blend: Cognitive blend value (0-100)
            
        Returns:
            BlendedProfile with applied blend settings
            
        Raises:
            ValueError: If blend is not between 0 and 100
        """
        if not 0 <= blend <= 100:
            raise ValueError(f"Blend must be between 0 and 100, got {blend}")
        
        mode = BlendMode.from_blend_value(blend)
        personality_weight = blend / 100.0
        
        # Get personality traits with blend applied
        personality = csm_profile_data.get('personality', {})
        blended_personality = self._blend_traits(personality, personality_weight)
        
        # Get tone preferences with blend applied
        tone = csm_profile_data.get('tone', {})
        blended_tone = self._blend_traits(tone, personality_weight)
        
        return BlendedProfile(
            mode=mode,
            blend_value=blend,
            personality_weight=personality_weight,
            requires_confirmation=mode.requires_confirmation(),
            personality=blended_personality,
            tone=blended_tone,
            communication=csm_profile_data.get('communication', {}),
            decision_style=csm_profile_data.get('decision_style', {}),
            vocabulary_patterns=csm_profile_data.get('vocabulary_patterns', []),
            custom_rules=csm_profile_data.get('custom_rules', {}),
        )
    
    def _blend_traits(
        self,
        traits: Dict[str, float],
        weight: float
    ) -> Dict[str, float]:
        """
        Blend trait values with neutral baseline.
        
        At weight=0, returns neutral (0.5) values.
        At weight=1, returns full trait values.
        
        Args:
            traits: Dictionary of trait values (0.0-1.0)
            weight: Blend weight (0.0-1.0)
            
        Returns:
            Dictionary of blended trait values
        """
        neutral = 0.5
        blended = {}
        
        for trait, value in traits.items():
            if isinstance(value, (int, float)):
                blended[trait] = neutral + (float(value) - neutral) * weight
            else:
                blended[trait] = value
        
        return blended
    
    def generate_response(
        self,
        prompt: str,
        csm_profile_data: Dict[str, Any],
        cognitive_blend: int,
        model: Optional[AIModel] = None,
        context_memories: Optional[List[Dict[str, Any]]] = None,
        include_reasoning: bool = False
    ) -> AIResponse:
        """
        Generate response with personality matching.
        
        Requirements: 2.3, 4.2, 4.3, 4.4, 4.5
        
        Args:
            prompt: The user's prompt/query
            csm_profile_data: CSM profile data dictionary
            cognitive_blend: Blend value (0-100)
            model: AI model to use (defaults to config default)
            context_memories: Optional list of relevant memories
            include_reasoning: Whether to include reasoning chain
            
        Returns:
            AIResponse with generated content and metadata
        """
        model = model or self.config.default_model
        
        # Apply cognitive blend to profile
        blended_profile = self.apply_blend(csm_profile_data, cognitive_blend)
        
        # Build system prompt with personality instructions
        system_prompt = self._build_system_prompt(blended_profile, context_memories)
        
        # Generate response using the AI model
        client = self._get_client()
        
        try:
            if isinstance(client, MockAIClient):
                # Use mock response for testing
                content = client.generate(prompt, system_prompt)
                tokens_used = len(prompt.split()) + len(content.split())
            else:
                # Use actual Google GenAI
                response = client.models.generate_content(
                    model=model.get_model_id(),
                    contents=prompt,
                    config={
                        'system_instruction': system_prompt,
                        'max_output_tokens': self.config.max_tokens,
                        'temperature': self.config.temperature,
                    }
                )
                content = response.text
                tokens_used = getattr(response, 'usage_metadata', {}).get('total_token_count', 0)
        except Exception as e:
            # Fallback to mock on error
            content = f"[AI Service Error: {str(e)}] I understand your request but encountered an issue."
            tokens_used = 0
        
        # Generate reasoning chain if requested
        reasoning_chain = None
        if include_reasoning:
            reasoning_chain = self._generate_reasoning_chain(
                prompt, blended_profile, content
            )
        
        return AIResponse(
            content=content,
            model_used=model.value,
            tokens_used=tokens_used,
            reasoning_chain=reasoning_chain,
            blend_mode=blended_profile.mode,
            blend_value=cognitive_blend,
            requires_confirmation=blended_profile.requires_confirmation,
            metadata={
                'personality_weight': blended_profile.personality_weight,
            }
        )
    
    def _build_system_prompt(
        self,
        blended_profile: BlendedProfile,
        context_memories: Optional[List[Dict[str, Any]]] = None
    ) -> str:
        """
        Build system prompt with personality and context.
        
        Args:
            blended_profile: The blended CSM profile
            context_memories: Optional relevant memories
            
        Returns:
            System prompt string
        """
        parts = [
            "You are a cognitive digital twin assistant.",
            "Respond authentically based on the user's personality profile.",
            "",
            blended_profile.get_system_prompt_additions(),
        ]
        
        # Add context from memories if available
        if context_memories:
            parts.append("")
            parts.append("Relevant context from previous interactions:")
            for memory in context_memories[:5]:  # Limit to 5 memories
                content = memory.get('content', '')
                if content:
                    parts.append(f"- {content[:200]}")
        
        return '\n'.join(parts)
    
    def _generate_reasoning_chain(
        self,
        prompt: str,
        blended_profile: BlendedProfile,
        response: str
    ) -> str:
        """
        Generate reasoning chain for transparency.
        
        Args:
            prompt: Original prompt
            blended_profile: Applied blend profile
            response: Generated response
            
        Returns:
            Reasoning chain string
        """
        return (
            f"Blend Mode: {blended_profile.mode.value}\n"
            f"Personality Weight: {blended_profile.personality_weight:.2f}\n"
            f"Requires Confirmation: {blended_profile.requires_confirmation}\n"
            f"Response Length: {len(response)} chars"
        )

    
    def extract_features(self, action: Dict[str, Any]) -> Dict[str, Any]:
        """
        Extract learning features from user action.
        
        Requirements: 6.1
        
        Analyzes user actions to extract patterns for CSM updates.
        
        Args:
            action: Dictionary containing action details
                - action_type: Type of action performed
                - content: Text content of the action
                - context: Additional context
                - metadata: Action metadata
                
        Returns:
            Dictionary of extracted features including:
                - action_type: The type of action
                - category: Action category
                - patterns: Detected patterns
                - sentiment: Sentiment score (-1.0 to 1.0)
                - confidence: Extraction confidence (0.0 to 1.0)
                - personality_signals: Detected personality traits
                - tone_signals: Detected tone preferences
                - vocabulary_additions: New vocabulary patterns
                - decision_signals: Decision style signals
        """
        action_type = action.get('action_type', 'unknown')
        content = action.get('content', '')
        context = action.get('context', {})
        
        # Determine action category
        category = self._determine_category(action_type)
        
        # Extract patterns from content
        patterns = self._extract_patterns(content)
        
        # Analyze sentiment
        sentiment = self._analyze_sentiment(content)
        
        # Extract signals based on category
        personality_signals = {}
        tone_signals = {}
        decision_signals = {}
        vocabulary_additions = []
        
        if category == 'communication':
            tone_signals = self._extract_tone_signals(content, context)
            vocabulary_additions = self._extract_vocabulary(content)
        elif category == 'decision':
            decision_signals = self._extract_decision_signals(context)
            personality_signals = self._extract_personality_signals(context)
        elif category == 'preference':
            personality_signals = self._extract_personality_signals(context)
            tone_signals = self._extract_tone_signals(content, context)
        
        return {
            'action_type': action_type,
            'category': category,
            'context': context,
            'patterns': patterns,
            'sentiment': sentiment,
            'confidence': 0.8,  # Default confidence
            'personality_signals': personality_signals,
            'tone_signals': tone_signals,
            'vocabulary_additions': vocabulary_additions,
            'decision_signals': decision_signals,
        }
    
    def _determine_category(self, action_type: str) -> str:
        """Determine the category of an action."""
        action_lower = action_type.lower()
        
        if any(kw in action_lower for kw in ['message', 'email', 'chat', 'reply']):
            return 'communication'
        elif any(kw in action_lower for kw in ['decide', 'approve', 'reject', 'choose']):
            return 'decision'
        elif any(kw in action_lower for kw in ['setting', 'preference', 'config']):
            return 'preference'
        elif any(kw in action_lower for kw in ['feedback', 'rate', 'review']):
            return 'feedback'
        else:
            return 'interaction'
    
    def _extract_patterns(self, content: str) -> List[str]:
        """Extract patterns from content."""
        patterns = []
        
        if not content:
            return patterns
        
        words = content.lower().split()
        
        # Response length pattern
        if len(words) < 10:
            patterns.append('brief_response')
        elif len(words) > 50:
            patterns.append('detailed_response')
        else:
            patterns.append('moderate_response')
        
        # Tone patterns
        if any(word in content.lower() for word in ['please', 'thank you', 'regards']):
            patterns.append('formal_tone')
        if any(word in content.lower() for word in ['hey', 'hi', 'cool', 'awesome']):
            patterns.append('casual_tone')
        
        return patterns
    
    def _analyze_sentiment(self, content: str) -> float:
        """
        Analyze sentiment of content.
        
        Returns a value between -1.0 (negative) and 1.0 (positive).
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
    
    def _extract_tone_signals(
        self,
        content: str,
        context: Dict[str, Any]
    ) -> Dict[str, float]:
        """Extract tone preference signals."""
        signals = {}
        content_lower = content.lower()
        
        # Formality signal
        formal_indicators = ['dear', 'sincerely', 'regards', 'respectfully']
        casual_indicators = ['hey', 'hi', 'yo', 'sup', 'lol']
        
        formal_count = sum(1 for ind in formal_indicators if ind in content_lower)
        casual_count = sum(1 for ind in casual_indicators if ind in content_lower)
        
        if formal_count > casual_count:
            signals['formality'] = min(0.7 + formal_count * 0.1, 1.0)
        elif casual_count > formal_count:
            signals['formality'] = max(0.3 - casual_count * 0.1, 0.0)
        
        # Directness signal
        if any(word in content_lower for word in ['please', 'could you', 'would you']):
            signals['directness'] = 0.3
        elif any(word in content_lower for word in ['do this', 'need', 'must', 'now']):
            signals['directness'] = 0.8
        
        return signals
    
    def _extract_personality_signals(
        self,
        context: Dict[str, Any]
    ) -> Dict[str, float]:
        """Extract personality trait signals."""
        signals = {}
        
        # Risk tolerance from context
        if 'risk_level' in context:
            risk = context['risk_level']
            if risk == 'high':
                signals['risk_tolerance'] = 0.8
            elif risk == 'low':
                signals['risk_tolerance'] = 0.2
        
        # Collaboration preference
        if 'collaboration' in context:
            signals['collaboration_preference'] = 0.8 if context['collaboration'] else 0.2
        
        return signals
    
    def _extract_decision_signals(
        self,
        context: Dict[str, Any]
    ) -> Dict[str, float]:
        """Extract decision style signals."""
        signals = {}
        
        # Speed vs accuracy from decision timing
        if 'decision_time_seconds' in context:
            time = context['decision_time_seconds']
            if time < 5:
                signals['speed_vs_accuracy'] = 0.9
            elif time > 60:
                signals['speed_vs_accuracy'] = 0.1
            else:
                signals['speed_vs_accuracy'] = 0.5
        
        return signals
    
    def _extract_vocabulary(self, content: str) -> List[str]:
        """Extract vocabulary patterns from content."""
        if not content:
            return []
        
        words = content.split()
        
        # Filter for characteristic vocabulary
        characteristic_words = [
            word.lower() for word in words
            if len(word) > 4 and word.isalpha()
        ]
        
        return list(set(characteristic_words))[:10]
    
    async def generate_embeddings(self, text: str) -> List[float]:
        """
        Generate embeddings for vector storage.
        
        Requirements: 5.2
        
        Args:
            text: Text to generate embeddings for
            
        Returns:
            List of float values representing the embedding
        """
        if not text or not text.strip():
            return []
        
        client = self._get_client()
        
        try:
            if isinstance(client, MockAIClient):
                # Use mock embeddings for testing
                return client.generate_embedding(text)
            else:
                # Use actual Google GenAI embeddings
                response = client.models.embed_content(
                    model=self.config.embedding_model,
                    content=text
                )
                return response.embedding
        except Exception:
            # Return mock embedding on error
            return MockAIClient().generate_embedding(text)
    
    def generate_embeddings_sync(self, text: str) -> List[float]:
        """
        Synchronous version of generate_embeddings.
        
        Args:
            text: Text to generate embeddings for
            
        Returns:
            List of float values representing the embedding
        """
        import asyncio
        
        try:
            loop = asyncio.get_event_loop()
            if loop.is_running():
                # If we're already in an async context, use a new thread
                import concurrent.futures
                with concurrent.futures.ThreadPoolExecutor() as executor:
                    future = executor.submit(
                        asyncio.run,
                        self.generate_embeddings(text)
                    )
                    return future.result()
            else:
                return loop.run_until_complete(self.generate_embeddings(text))
        except RuntimeError:
            # No event loop, create one
            return asyncio.run(self.generate_embeddings(text))


class MockAIClient:
    """
    Mock AI client for testing when Google GenAI is not available.
    
    Provides deterministic responses for testing purposes.
    """
    
    def generate(self, prompt: str, system_prompt: str = "") -> str:
        """
        Generate a mock response.
        
        Args:
            prompt: User prompt
            system_prompt: System instructions
            
        Returns:
            Mock response string
        """
        # Generate a deterministic response based on prompt
        response_parts = [
            "I understand your request.",
        ]
        
        # Add personality-based response elements
        if "formal" in system_prompt.lower():
            response_parts.append("I shall address this matter professionally.")
        elif "casual" in system_prompt.lower():
            response_parts.append("Sure thing, let me help you out!")
        else:
            response_parts.append("Let me help you with that.")
        
        # Add content-based response
        if "?" in prompt:
            response_parts.append("Based on my analysis, here's what I think:")
        
        response_parts.append(f"Regarding: {prompt[:50]}...")
        
        return " ".join(response_parts)
    
    def generate_embedding(self, text: str) -> List[float]:
        """
        Generate a mock embedding.
        
        Creates a deterministic embedding based on text hash.
        
        Args:
            text: Text to embed
            
        Returns:
            List of 768 float values
        """
        import hashlib
        
        # Create deterministic embedding from text hash
        text_hash = hashlib.sha256(text.encode()).hexdigest()
        
        # Convert hash to list of floats
        embedding = []
        for i in range(0, min(len(text_hash), 64), 2):
            # Convert each pair of hex chars to a float between -1 and 1
            value = int(text_hash[i:i+2], 16) / 255.0 * 2 - 1
            embedding.append(value)
        
        # Pad to 768 dimensions
        while len(embedding) < 768:
            # Repeat pattern with slight variation
            idx = len(embedding) % 32
            embedding.append(embedding[idx] * 0.9)
        
        return embedding[:768]
