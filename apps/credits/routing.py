"""
Model routing service for Brain mode abstraction.

Selects appropriate AI models based on Brain mode and operation type,
with configurable routing rules and fallback logic.

Requirements: 6.1-6.9, 20.6
"""

import logging
import threading
import time
from datetime import datetime, timedelta
from typing import Dict, List, Optional
from django.core.cache import cache
from django.db.models import Q

from apps.credits.models import BrainRoutingConfig
from apps.credits.enums import BrainMode, OperationType
from apps.credits.dataclasses import ModelSelection
from apps.credits.constants import (
    ROUTING_RULES,
    MODEL_FALLBACKS,
    ROUTING_CONFIG_CACHE_TTL,
)
from apps.credits.metrics import (
    model_selections_total,
    model_routing_latency_seconds,
)


logger = logging.getLogger(__name__)


class ModelRouter:
    """
    Routes AI requests to appropriate models based on Brain mode and operation type.
    
    Requirements: 6.1, 6.9, 20.6
    
    Features:
    - Configurable routing rules stored in database
    - In-memory caching with 5-minute refresh
    - Fallback model selection for failure handling
    - Thread-safe cache access
    """
    
    # Class-level cache for routing rules
    _routing_cache: Optional[Dict] = None
    _cache_timestamp: Optional[datetime] = None
    _cache_lock = threading.Lock()
    
    def __init__(self):
        """Initialize ModelRouter."""
        self.cache_ttl_seconds = ROUTING_CONFIG_CACHE_TTL
    
    def load_routing_config(self) -> Dict[str, Dict[str, str]]:
        """
        Load routing configuration from database or cache.
        
        Requirements: 6.1, 6.9, 20.6
        
        Returns:
            Dict mapping brain_mode -> operation_type -> model_name
        
        Cache Strategy:
        - First checks in-memory cache (5-minute TTL)
        - Falls back to database if cache miss or expired
        - Thread-safe cache access using lock
        """
        # Check if cache is valid
        if self._is_cache_valid():
            logger.debug("Using cached routing rules")
            return self._routing_cache.copy()
        
        # Acquire lock for cache update
        with self._cache_lock:
            # Double-check cache validity after acquiring lock
            if self._is_cache_valid():
                return self._routing_cache.copy()
            
            # Load from database
            logger.info("Loading routing configuration from database")
            routing_rules = self._load_from_database()
            
            # Update cache
            self._routing_cache = routing_rules
            self._cache_timestamp = datetime.now()
            
            return routing_rules.copy()
    
    def _is_cache_valid(self) -> bool:
        """Check if in-memory cache is valid."""
        if self._routing_cache is None or self._cache_timestamp is None:
            return False
        
        cache_age = datetime.now() - self._cache_timestamp
        return cache_age.total_seconds() < self.cache_ttl_seconds
    
    def _load_from_database(self) -> Dict[str, Dict[str, str]]:
        """
        Load routing configuration from database.
        
        Returns:
            Dict mapping brain_mode -> operation_type -> model_name
        
        Fallback:
            If no active config found, returns default ROUTING_RULES from constants
        """
        try:
            # Get active routing configuration
            active_config = BrainRoutingConfig.objects.filter(
                is_active=True
            ).order_by('-updated_at').first()
            
            if active_config:
                logger.info(
                    f"Loaded routing config: {active_config.config_name}"
                )
                return active_config.routing_rules
            else:
                logger.warning(
                    "No active routing configuration found, using defaults"
                )
                return ROUTING_RULES
        
        except Exception as e:
            logger.error(
                f"Error loading routing config from database: {e}",
                exc_info=True
            )
            # Fallback to default routing rules
            return ROUTING_RULES
    
    def invalidate_cache(self) -> None:
        """
        Invalidate routing cache.
        
        Call this when routing configuration is updated in database.
        Requirements: 6.9
        """
        with self._cache_lock:
            self._routing_cache = None
            self._cache_timestamp = None
            logger.info("Routing cache invalidated")
    
    def select_model(
        self,
        brain_mode: BrainMode,
        operation_type: OperationType
    ) -> ModelSelection:
        """
        Select appropriate AI model based on Brain mode and operation type.
        
        Requirements: 6.2-6.6
        
        Args:
            brain_mode: Brain intelligence level (brain, brain_pro, brain_gen)
            operation_type: Type of operation (simple_response, long_response, etc.)
        
        Returns:
            ModelSelection with primary model and fallback list
        
        Routing Rules:
        - brain + simple_response → cerebras
        - brain + long_response → gemini-2.5-flash
        - brain + summarization → mistral
        - brain + complex_reasoning → gemini-2.5-pro
        - brain + automation → gemini-2.5-pro
        - brain_pro + all operations → gemini-3-pro
        - brain_gen + all operations → gemini-3.1-pro
        """
        start_time = time.time()
        
        # Load routing configuration
        routing_rules = self.load_routing_config()
        
        # Convert enums to strings for lookup
        brain_mode_str = brain_mode.value
        operation_type_str = operation_type.value
        
        # Get primary model from routing rules
        try:
            primary_model = routing_rules[brain_mode_str][operation_type_str]
        except KeyError:
            logger.error(
                f"No routing rule found for {brain_mode_str}.{operation_type_str}"
            )
            # Fallback to default model
            primary_model = 'gemini-2.5-flash'
        
        # Get fallback models
        fallback_models = self.get_fallback_models(primary_model)
        
        # Create selection reason
        selection_reason = (
            f"Selected {primary_model} for {brain_mode_str} mode "
            f"with {operation_type_str} operation"
        )
        
        # Create ModelSelection
        selection = ModelSelection(
            primary_model=primary_model,
            fallback_models=fallback_models,
            selection_reason=selection_reason,
            brain_mode=brain_mode_str,
            operation_type=operation_type_str,
        )
        
        logger.info(
            f"Model selection: {primary_model} "
            f"(brain_mode={brain_mode_str}, operation_type={operation_type_str})"
        )
        
        # Record metrics
        latency = time.time() - start_time
        model_routing_latency_seconds.labels(brain_mode=brain_mode_str).observe(latency)
        model_selections_total.labels(
            brain_mode=brain_mode_str,
            operation_type=operation_type_str,
            selected_model=primary_model
        ).inc()
        
        return selection
    
    def get_fallback_models(self, primary_model: str) -> List[str]:
        """
        Get fallback models for given primary model.
        
        Requirements: 6.7
        
        Args:
            primary_model: Name of the primary model
        
        Returns:
            List of fallback model names in priority order
        
        Fallback Order:
        - cerebras → gemini-2.5-flash → gemini-2.5-pro
        - gemini-2.5-flash → gemini-2.5-pro → cerebras
        - gemini-2.5-pro → gemini-2.5-flash → gemini-3-pro
        - gemini-3-pro → gemini-2.5-pro → gemini-3.1-pro
        - gemini-3.1-pro → gemini-3-pro → gemini-2.5-pro
        - mistral → gemini-2.5-flash → cerebras
        """
        fallbacks = MODEL_FALLBACKS.get(primary_model, [])
        
        logger.debug(
            f"Fallback models for {primary_model}: {fallbacks}"
        )
        
        return fallbacks
    
    def validate_routing_config(self, config: Dict[str, Dict[str, str]]) -> bool:
        """
        Validate routing configuration structure.
        
        Requirements: 6.9
        
        Args:
            config: Routing configuration to validate
        
        Returns:
            True if valid, False otherwise
        
        Validation Rules:
        - Must be a dict
        - Must contain all brain modes (brain, brain_pro, brain_gen)
        - Each brain mode must map to dict of operation types
        - Each operation type must map to string model name
        """
        if not isinstance(config, dict):
            logger.error("Routing config must be a dict")
            return False
        
        # Valid brain modes and operation types
        valid_brain_modes = [mode.value for mode in BrainMode]
        valid_operation_types = [op.value for op in OperationType]
        
        # Check all brain modes present
        for brain_mode in valid_brain_modes:
            if brain_mode not in config:
                logger.error(f"Missing brain_mode: {brain_mode}")
                return False
            
            operations = config[brain_mode]
            if not isinstance(operations, dict):
                logger.error(
                    f"Operations for {brain_mode} must be a dict"
                )
                return False
            
            # Check all operation types present
            for operation_type in valid_operation_types:
                if operation_type not in operations:
                    logger.error(
                        f"Missing operation_type: {brain_mode}.{operation_type}"
                    )
                    return False
                
                model = operations[operation_type]
                if not isinstance(model, str) or not model:
                    logger.error(
                        f"Model for {brain_mode}.{operation_type} "
                        f"must be a non-empty string"
                    )
                    return False
        
        logger.info("Routing configuration is valid")
        return True
    
    def log_routing_decision(
        self,
        selection: ModelSelection,
        user_id: Optional[int] = None
    ) -> None:
        """
        Log routing decision for audit trail.
        
        Requirements: 6.8
        
        Args:
            selection: ModelSelection result from select_model()
            user_id: Optional user ID for user-specific logging
        
        Note:
            This method logs to application logger. The actual AIRequestLog
            record is created by AIService when processing the request.
        """
        log_data = {
            'selected_model': selection.primary_model,
            'brain_mode': selection.brain_mode,
            'operation_type': selection.operation_type,
            'selection_reason': selection.selection_reason,
            'fallback_models': selection.fallback_models,
        }
        
        if user_id:
            log_data['user_id'] = user_id
        
        logger.info(
            f"Routing decision: {log_data}",
            extra={'routing_decision': log_data}
        )
    
    def get_routing_summary(self) -> Dict[str, any]:
        """
        Get summary of current routing configuration.
        
        Returns:
            Dict with routing summary information
        """
        routing_rules = self.load_routing_config()
        
        # Count unique models
        unique_models = set()
        for brain_mode, operations in routing_rules.items():
            for model in operations.values():
                unique_models.add(model)
        
        return {
            'brain_modes': list(routing_rules.keys()),
            'unique_models': list(unique_models),
            'total_routes': sum(
                len(ops) for ops in routing_rules.values()
            ),
            'cache_valid': self._is_cache_valid(),
            'cache_age_seconds': (
                (datetime.now() - self._cache_timestamp).total_seconds()
                if self._cache_timestamp else None
            ),
        }


# Singleton instance
_router_instance: Optional[ModelRouter] = None
_router_lock = threading.Lock()


def get_model_router() -> ModelRouter:
    """
    Get singleton ModelRouter instance.
    
    Thread-safe singleton pattern.
    """
    global _router_instance
    
    if _router_instance is None:
        with _router_lock:
            if _router_instance is None:
                _router_instance = ModelRouter()
    
    return _router_instance
