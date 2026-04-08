# Implementation Plan: Credit-Based AI Architecture

## Overview

This implementation plan transforms the NeuroTwin platform from direct model selection to a credit-based AI usage system with intelligent Brain mode abstraction. The architecture introduces three user-facing Brain modes (Brain, Brain Pro, Brain Gen) that automatically route requests to appropriate AI models based on task complexity and subscription tier, while tracking usage through a credit system.

The implementation follows a layered approach: database models and migrations first, then core backend services (CreditManager, ModelRouter, AIService), provider abstraction layer (Cerebras and Gemini integrations), API endpoints, and finally frontend components. Each phase builds incrementally with validation checkpoints to ensure system stability.

## Tasks

- [x] 1. Database models and migrations
  - [x] 1.1 Create UserCredits model with credit tracking fields
    - Create model in `apps/credits/models.py` with fields: user (OneToOne), monthly_credits, remaining_credits, used_credits, purchased_credits, last_reset_date, created_at, updated_at
    - Add database indexes on user_id and last_reset_date
    - Create migration file
    - _Requirements: 16.1, 16.2, 16.3_

  - [x] 1.2 Create CreditUsageLog model for audit trail
    - Create model with fields: user (ForeignKey), timestamp, credits_consumed, operation_type, brain_mode, model_used, request_id, created_at
    - Add composite indexes on (user_id, timestamp), (user_id, operation_type), (user_id, brain_mode)
    - Set ordering to ['-timestamp']
    - _Requirements: 16.4, 16.5, 16.6_

  - [x] 1.3 Create AIRequestLog model for comprehensive request logging
    - Create model with UUID primary key and fields: user, timestamp, brain_mode, operation_type, model_used, prompt_length, response_length, tokens_used, credits_consumed, latency_ms, status, error_message, error_type, cognitive_blend_value, created_at
    - Add composite indexes on (user_id, timestamp), (user_id, status), (model_used, timestamp)
    - _Requirements: 16.7, 16.8, 16.9_

  - [x] 1.4 Create BrainRoutingConfig model for dynamic routing rules
    - Create model with fields: config_name (unique), routing_rules (JSONField), is_active, created_by, created_at, updated_at
    - Add validation for routing_rules JSON structure
    - _Requirements: 6.9_

  - [x] 1.5 Create CreditTopUp model for future credit purchases
    - Create model with UUID primary key and fields: user, amount, price_paid, payment_method, transaction_id (unique), status, created_at, updated_at
    - Add composite index on (user_id, created_at) and index on transaction_id
    - _Requirements: 17.4, 17.5, 17.6_

  - [x] 1.6 Add brain_mode field to Twin model
    - Add brain_mode CharField with choices (brain, brain_pro, brain_gen), nullable, default='brain'
    - Create migration to add field to existing Twin model
    - _Requirements: 16.10_

  - [x] 1.7 Run migrations and verify database schema
    - Execute migrations: `uv run python manage.py migrate`
    - Verify all tables created with correct indexes
    - Test model creation and relationships
    - _Requirements: 16.1-16.10_


- [x] 2. Enums, constants, and dataclasses
  - [x] 2.1 Create BrainMode and OperationType enums
    - Create `apps/credits/enums.py` with BrainMode enum (BRAIN, BRAIN_PRO, BRAIN_GEN)
    - Create OperationType enum (SIMPLE_RESPONSE, LONG_RESPONSE, SUMMARIZATION, COMPLEX_REASONING, AUTOMATION)
    - Add value properties and validation methods
    - _Requirements: 3.1, 5.1_

  - [x] 2.2 Define credit allocation and routing constants
    - Create `apps/credits/constants.py` with TIER_CREDIT_ALLOCATIONS dict (FREE=50, PRO=2000, TWIN_PLUS=5000, EXECUTIVE=10000)
    - Define BRAIN_MODE_TIER_REQUIREMENTS dict mapping modes to allowed tiers
    - Define BASE_COSTS dict for operation types
    - Define BRAIN_MULTIPLIERS dict for brain modes
    - _Requirements: 1.3-1.6, 3.2-3.6, 3.8-3.10_

  - [x] 2.3 Create ProviderResponse dataclass
    - Create `apps/credits/dataclasses.py` with ProviderResponse dataclass
    - Add fields: content, tokens_used, model_used, latency_ms, metadata
    - Add validation and helper methods
    - _Requirements: 8.5_

  - [x] 2.4 Update AIModel enum to replace Qwen with Cerebras
    - Modify `apps/twin/dataclasses.py` AIModel enum
    - Replace QWEN with CEREBRAS (value: `"cerebras"`)
    - Update model identifiers: GEMINI_FLASH → `"gemini-2.5-flash"`, add GEMINI_PRO_25 → `"gemini-2.5-pro"`, GEMINI_PRO_3 → `"gemini-3-pro"`, GEMINI_PRO_31 → `"gemini-3.1-pro"`
    - Keep MISTRAL for backward compatibility but remove from `free_tier_models()` routing
    - Update `free_tier_models()` and `paid_tier_models()` methods
    - _Requirements: 18.2_

  - [x] 2.5 Update TierFeatures dataclasses for Cerebras
    - Modify `apps/subscription/dataclasses.py` TierFeatures
    - Replace 'qwen' with 'cerebras' in all available_models lists
    - Update free_tier(), pro_tier(), twin_plus_tier(), executive_tier() methods
    - _Requirements: 18.4_

- [x] 3. Credit management service
  - [x] 3.1 Implement CreditManager.get_balance() with Redis caching
    - Create `apps/credits/services.py` with CreditManager class
    - Implement get_balance() method with Redis cache (60s TTL)
    - Add cache key format: `credit_balance:{user_id}`
    - Fallback to database on cache miss and populate cache
    - _Requirements: 1.1, 1.10, 20.1_

  - [x] 3.2 Implement CreditManager.estimate_cost() calculation
    - Implement estimate_cost() method with formula: base_cost × (tokens/1000) × brain_multiplier
    - Use BASE_COSTS and BRAIN_MULTIPLIERS constants
    - Return max(1, round(calculated_cost))
    - _Requirements: 3.1-3.11_

  - [x] 3.3 Implement CreditManager.check_sufficient_credits() validation
    - Implement check_sufficient_credits() method
    - Compare remaining_credits with estimated_cost
    - Return boolean result
    - _Requirements: 4.1, 4.2, 4.4_

  - [x] 3.4 Implement CreditManager.deduct_credits() with atomic transaction
    - Implement deduct_credits() method using SELECT FOR UPDATE
    - Use database transaction for atomicity
    - Invalidate Redis cache immediately after deduction
    - Create CreditUsageLog record with metadata
    - Raise InsufficientCreditsError if balance insufficient
    - _Requirements: 3.1, 9.8, 20.3, 20.4_

  - [x] 3.5 Implement CreditManager.check_and_reset_if_needed() for monthly reset
    - Implement check_and_reset_if_needed() method
    - Check if current date is first of month and last_reset_date is previous month
    - Set remaining_credits = monthly_credits, used_credits = 0
    - Update last_reset_date to current date
    - Create reset log entry
    - Invalidate cache
    - _Requirements: 2.1-2.5_

  - [x] 3.6 Implement CreditManager.get_usage_history() with filtering
    - Implement get_usage_history() method with pagination
    - Support filters: date_range, operation_type, brain_mode
    - Return queryset of CreditUsageLog records
    - Calculate summary statistics (total consumed, average per request)
    - _Requirements: 10.1-10.6_

  - [x] 3.7 Implement CreditManager.get_usage_summary() for aggregated data
    - Implement get_usage_summary() method
    - Aggregate usage by day for specified period
    - Group by operation_type and brain_mode
    - Return daily breakdown and category breakdowns
    - _Requirements: 10.7, 10.8_

  - [ ]* 3.8 Write property test for credit cost calculation
    - **Property 7: Credit Cost Calculation**
    - **Validates: Requirements 3.1-3.11**
    - Use Hypothesis to generate all combinations of operation_type, estimated_tokens, brain_mode
    - Verify calculated cost matches formula: max(1, round(base_cost × (tokens/1000) × brain_multiplier))

  - [ ]* 3.9 Write unit tests for CreditManager
    - Test get_balance() cache hit and miss scenarios
    - Test estimate_cost() for all operation types and brain modes
    - Test deduct_credits() atomic behavior and race conditions
    - Test check_and_reset_if_needed() on first of month
    - Test insufficient credits error handling


- [x] 4. Model routing service
  - [x] 4.1 Create ModelRouter class with routing rule storage
    - Create `apps/credits/routing.py` with ModelRouter class
    - Implement load_routing_config() to load from BrainRoutingConfig model
    - Cache routing rules in memory with 5-minute refresh
    - _Requirements: 6.1, 6.9, 20.6_

  - [x] 4.2 Implement ModelRouter.select_model() with routing logic
    - Implement select_model() method accepting brain_mode and operation_type
    - Apply routing rules: brain+simple_response→cerebras, brain+long_response→gemini-2.5-flash, brain+summarization→mistral, brain+complex_reasoning→gemini-2.5-pro, brain+automation→gemini-2.5-pro
    - Apply brain_pro routing: all operations→gemini-3-pro
    - Apply brain_gen routing: all operations→gemini-3.1-pro
    - Return ModelSelection with primary model and fallback list
    - _Requirements: 6.2-6.6_

  - [x] 4.3 Implement ModelRouter.get_fallback_models() for failure handling
    - Implement get_fallback_models() method
    - Define fallback order: cerebras→gemini-2.5-flash→gemini-2.5-pro
    - Return list of fallback models for given primary model
    - _Requirements: 6.7_

  - [x] 4.4 Implement routing decision logging
    - Log each routing decision with selected_model, brain_mode, operation_type, selection_reason
    - Store in AIRequestLog for audit trail
    - _Requirements: 6.8_

  - [x] 4.5 Create default routing configuration seed data
    - Create management command `seed_routing_config` in `apps/credits/management/commands/`
    - Insert default BrainRoutingConfig with production routing rules
    - Set is_active=True for default config
    - _Requirements: 6.9_

  - [ ]* 4.6 Write property test for model routing rules
    - **Property 12: Model Routing Rules**
    - **Validates: Requirements 6.2-6.6**
    - Use Hypothesis to generate all combinations of brain_mode and operation_type
    - Verify ModelRouter selects correct model according to routing rules

  - [ ]* 4.7 Write unit tests for ModelRouter
    - Test select_model() for all brain_mode/operation_type combinations
    - Test fallback logic when primary model unavailable
    - Test routing config validation
    - Test cache refresh behavior

- [x] 5. Provider abstraction layer
  - [x] 5.1 Create AIProvider abstract base class
    - Create `apps/credits/providers/base.py` with AIProvider ABC
    - Define abstract methods: generate_response(), generate_embeddings(), estimate_tokens()
    - Define method signatures with type hints
    - _Requirements: 8.1_

  - [x] 5.2 Implement CerebrasService provider
    - Create `apps/credits/providers/cerebras.py` with CerebrasService class extending AIProvider
    - Implement generate_response() with Cerebras API integration
    - Use CEREBRAS_API_KEY from environment variables
    - Set base_url to "https://api.cerebras.ai/v1"
    - Set timeout to 30 seconds
    - _Requirements: 7.2-7.5, 8.2_

  - [x] 5.3 Add Cerebras error handling and retry logic
    - Implement exponential backoff for rate limit errors (429)
    - Retry up to 3 times with backoff: 1s, 2s, 4s
    - Raise CerebrasTimeoutError on timeout
    - Raise CerebrasAuthError on 401
    - Raise CerebrasAPIError on other errors
    - _Requirements: 7.6, 7.9_

  - [x] 5.4 Add Cerebras request logging
    - Log all requests with timestamp, prompt_length, response_length, latency_ms
    - Log errors with full context for debugging
    - Sanitize prompts to remove PII before logging
    - _Requirements: 7.8_

  - [x] 5.5 Implement GeminiService provider
    - Create `apps/credits/providers/gemini.py` with GeminiService class extending AIProvider
    - Use existing google-genai SDK integration
    - Support model parameter for gemini-2.5-flash, gemini-2.5-pro, gemini-3-pro, gemini-3.1-pro
    - Use GOOGLE_API_KEY from settings
    - _Requirements: 8.3, 8.4_

  - [x] 5.6 Implement MistralService provider
    - Create `apps/credits/providers/mistral.py` with MistralService class extending AIProvider
    - Implement generate_response() with Mistral API integration
    - Use MISTRAL_API_KEY from environment variables
    - Used exclusively for Brain mode (free tier) summarization operations
    - Implement exponential backoff for rate limit errors (429), max 3 retries
    - Set timeout to 30 seconds
    - Log all requests with timestamp, prompt_length, response_length, latency_ms
    - _Requirements: 8.2, 8.5, 8.6_

  - [x] 5.7 Create provider registry for dynamic lookup
    - Create `apps/credits/providers/registry.py` with ProviderRegistry class
    - Register CerebrasService, GeminiService, and MistralService instances
    - Implement get_provider(model_name) method for dynamic lookup
    - Validate provider availability on startup
    - _Requirements: 8.7, 8.8, 8.10_

  - [ ]* 5.8 Write unit tests for provider implementations
    - Test CerebrasService.generate_response() with mocked API
    - Test GeminiService.generate_response() with mocked SDK
    - Test MistralService.generate_response() with mocked API
    - Test retry logic with simulated rate limits
    - Test error handling for various failure scenarios
    - Test request logging and PII sanitization

- [x] 6. AI service orchestration
  - [x] 6.1 Create AIService class with request orchestration
    - Create `apps/credits/ai_service.py` with AIService class
    - Implement process_request() method accepting user_id, prompt, brain_mode, operation_type, context
    - Define execution flow: validate tier → check reset → estimate cost → validate credits → route → load CSM profile → execute → deduct → log
    - Load cognitive_blend from Twin record via `TwinService.get_twin(user_id)` — read `twin.cognitive_blend` and `twin.requires_confirmation`
    - Load CSM profile via `CSMService.get_profile(user_id)` when cognitive_blend > 0; build system prompt from profile tone/vocabulary/communication fields proportional to blend percentage
    - If CSM profile not found, proceed without personality overlay and log a warning
    - Store cognitive_blend_value in AIRequestLog from Twin record
    - _Requirements: 9.1, 9.2_

  - [x] 6.2 Implement AIService.validate_brain_mode_access() for tier checking
    - Implement validate_brain_mode_access() method
    - Check user's subscription_tier against BRAIN_MODE_TIER_REQUIREMENTS
    - Raise BrainModeRestrictedError if tier insufficient
    - _Requirements: 5.10, 9.2_

  - [x] 6.3 Integrate credit validation in AIService.process_request()
    - Call CreditManager.check_and_reset_if_needed() before processing
    - Call CreditManager.estimate_cost() to calculate estimated credits
    - Call CreditManager.check_sufficient_credits() to validate balance
    - Raise InsufficientCreditsError if balance insufficient
    - _Requirements: 9.2, 9.3_

  - [x] 6.4 Integrate model routing in AIService.process_request()
    - Call ModelRouter.select_model() to get primary model and fallbacks
    - Get provider instance from ProviderRegistry
    - Execute request through provider.generate_response()
    - Implement fallback logic if primary model fails
    - _Requirements: 9.4, 9.5, 9.6_

  - [x] 6.5 Implement credit deduction and logging in AIService
    - Call CreditManager.deduct_credits() with actual token usage after successful response
    - Create AIRequestLog record with request details, response metadata, execution time
    - Do NOT deduct credits if request fails
    - Log failure reason in AIRequestLog with status='failed'
    - _Requirements: 9.7, 9.8, 9.9, 9.10, 9.11_

  - [x] 6.6 Add comprehensive error handling to AIService
    - Handle InsufficientCreditsError → return 402 with remaining balance
    - Handle BrainModeRestrictedError → return 403 with required tier
    - Handle ModelUnavailableError → return 503 after exhausting fallbacks
    - Handle provider errors → log without deducting credits
    - _Requirements: 19.1-19.4_

  - [ ]* 6.7 Write integration tests for AIService
    - Test complete request flow from validation to response
    - Test insufficient credits error handling
    - Test brain mode restriction error handling
    - Test provider failure and fallback logic
    - Test credit deduction only on success


- [ ] 7. Checkpoint - Core services validation
  - Ensure all tests pass for CreditManager, ModelRouter, AIService, and providers
  - Verify database models can be created and queried
  - Test credit deduction atomicity with concurrent requests
  - Verify routing rules load correctly from database
  - Ask the user if questions arise

- [x] 8. API endpoints for credit management
  - [x] 8.1 Create CreditViewSet with balance endpoint
    - Create `apps/credits/views.py` with CreditViewSet
    - Implement GET /api/v1/credits/balance endpoint
    - Return monthly_credits, remaining_credits, used_credits, purchased_credits, last_reset_date, next_reset_date, days_until_reset, usage_percentage
    - Require JWT authentication
    - _Requirements: 1.10, 4.5_

  - [x] 8.2 Implement credit estimate endpoint
    - Add GET /api/v1/credits/estimate endpoint to CreditViewSet
    - Accept query parameters: operation_type, brain_mode, estimated_tokens (default 500)
    - Call CreditManager.estimate_cost() and return estimated_cost, sufficient_credits, remaining_credits
    - _Requirements: 4.5_

  - [x] 8.3 Implement credit usage history endpoint
    - Add GET /api/v1/credits/usage endpoint to CreditViewSet
    - Support pagination with page_size=20
    - Support filters: start_date, end_date, operation_type, brain_mode
    - Return paginated CreditUsageLog records with summary statistics
    - _Requirements: 10.3, 10.4, 10.5, 10.6_

  - [x] 8.4 Implement credit usage summary endpoint
    - Add GET /api/v1/credits/usage/summary endpoint to CreditViewSet
    - Accept query parameter: days (default 30)
    - Call CreditManager.get_usage_summary() and return aggregated data
    - Return daily breakdown, by_operation_type, by_brain_mode
    - _Requirements: 10.7, 10.8_

  - [x] 8.5 Create serializers for credit endpoints
    - Create `apps/credits/serializers.py` with CreditBalanceSerializer, CreditEstimateSerializer, CreditUsageLogSerializer, CreditUsageSummarySerializer
    - Add validation for operation_type and brain_mode enums
    - Add computed fields for next_reset_date and days_until_reset
    - _Requirements: 13.1, 13.2_

  - [x] 8.6 Add URL routing for credit endpoints
    - Create `apps/credits/urls.py` with router registration
    - Register CreditViewSet with basename='credits'
    - Include in `core/api/urls.py` v1_patterns at path 'credits/' (following existing pattern — do NOT add to neurotwin/urls.py directly)
    - _Requirements: 13.1_

  - [ ]* 8.7 Write API tests for credit endpoints
    - Test GET /api/v1/credits/balance returns correct data
    - Test GET /api/v1/credits/estimate calculates correctly
    - Test GET /api/v1/credits/usage with filters and pagination
    - Test GET /api/v1/credits/usage/summary aggregation
    - Test authentication requirement for all endpoints

- [x] 9. API endpoints for AI requests
  - [x] 9.1 Update Twin chat endpoint to use AIService
    - Add new `TwinChatView` to `apps/twin/views.py` (this endpoint does not exist yet — create from scratch)
    - Register at `path('chat', TwinChatView.as_view(), name='chat')` in `apps/twin/urls.py`
    - Accept brain_mode parameter in request body (optional, use user preference if not provided)
    - Accept operation_type parameter (default 'long_response')
    - Call AIService.process_request() — AIService will internally load CSM profile and cognitive_blend from Twin
    - Return response with metadata: brain_mode, model_used, tokens_used, credits_consumed, latency_ms, request_id
    - _Requirements: 15.1, 15.2, 9.11_

  - [x] 9.2 Add credits consumed to chat response
    - Include credits object in response: {remaining, consumed}
    - Invalidate credit cache after successful request
    - _Requirements: 9.11_

  - [x] 9.3 Handle insufficient credits error in chat endpoint
    - Catch InsufficientCreditsError from AIService
    - Return 402 Payment Required with error details
    - Include required_credits, remaining_credits, next_reset_date, upgrade_url
    - _Requirements: 4.1, 4.2, 4.3, 19.1, 19.2_

  - [x] 9.4 Handle brain mode restricted error in chat endpoint
    - Catch BrainModeRestrictedError from AIService
    - Return 403 Forbidden with error details
    - Include requested_mode, current_tier, required_tier, upgrade_url
    - _Requirements: 5.10, 19.3_

  - [x] 9.5 Create Twin generate endpoint for automation
    - Add POST /api/v1/twin/generate endpoint in `apps/twin/views.py`
    - Accept prompt, brain_mode, operation_type, max_tokens, temperature
    - Call AIService.process_request() for automation workflows
    - Return same response format as chat endpoint
    - _Requirements: 9.1-9.11_

  - [x] 9.6 Update Twin serializers for brain_mode
    - Modify `apps/twin/serializers.py` to include brain_mode field
    - Add validation for brain_mode against user's subscription tier
    - Add operation_type field with validation
    - _Requirements: 15.3, 15.4_

  - [ ]* 9.7 Write API tests for Twin endpoints with brain mode
    - Test POST /api/v1/twin/chat with brain_mode parameter
    - Test insufficient credits returns 402
    - Test brain mode restriction returns 403
    - Test credits deducted after successful request
    - Test POST /api/v1/twin/generate for automation

- [x] 10. User settings endpoints for brain mode
  - [x] 10.1 Add brain_mode to user settings model
    - Modify user settings model (or create if doesn't exist) to include brain_mode field
    - Set default to 'brain'
    - Add validation against subscription tier
    - _Requirements: 5.8, 15.7_

  - [x] 10.2 Implement GET /api/v1/users/settings endpoint
    - Create or modify `apps/authentication/views.py` settings endpoint
    - Return brain_mode, cognitive_blend, notification_preferences, subscription_tier
    - Require JWT authentication
    - _Requirements: 15.7_

  - [x] 10.3 Implement PUT /api/v1/users/settings endpoint
    - Accept brain_mode parameter in request body
    - Validate brain_mode against user's subscription tier
    - Save preference and return updated settings
    - _Requirements: 15.8, 15.9, 15.10_

  - [ ]* 10.4 Write tests for user settings endpoints
    - Test GET /api/v1/users/settings returns brain_mode
    - Test PUT /api/v1/users/settings updates brain_mode
    - Test validation rejects brain_mode not allowed for tier
    - Test default brain_mode is 'brain'


- [x] 11. Admin endpoints and monitoring
  - [x] 11.1 Create admin AI request log endpoint
    - Create `apps/credits/admin_views.py` with AdminAIRequestViewSet
    - Implement GET /api/v1/admin/ai-requests endpoint
    - Support filters: user_id, brain_mode, model_used, status, start_date, end_date
    - Support pagination
    - Return aggregates: total_requests, success_rate, average_latency_ms, total_tokens
    - Require admin authentication (is_staff=True)
    - _Requirements: 11.5, 11.6, 11.7_

  - [x] 11.2 Create admin brain config endpoint
    - Add POST /api/v1/admin/brain-config endpoint to AdminBrainConfigViewSet
    - Accept config_name and routing_rules JSON
    - Validate routing rules structure and model references
    - Create BrainRoutingConfig record with is_active=False
    - Return validation status
    - _Requirements: 6.9, 21.1-21.10_

  - [x] 11.3 Create admin brain config activation endpoint
    - Add PUT /api/v1/admin/brain-config/{id}/activate endpoint
    - Set is_active=True for specified config
    - Set is_active=False for all other configs
    - Invalidate routing cache
    - _Requirements: 6.9_

  - [x] 11.4 Implement health check endpoint
    - Create GET /api/v1/health endpoint (no authentication required)
    - Check database connectivity
    - Check Redis connectivity
    - Check provider API health (cerebras_api, gemini_api)
    - Return status: healthy/degraded/unhealthy
    - Include metrics: credit_check_p95_latency_ms, ai_request_success_rate
    - _Requirements: 23.10_

  - [x] 11.5 Add admin URL routing
    - Create `apps/credits/admin_urls.py` with admin router
    - Register AdminAIRequestViewSet and AdminBrainConfigViewSet
    - Include in `core/api/urls.py` v1_patterns at path 'admin/' (following existing pattern)
    - Add permission class requiring is_staff=True
    - _Requirements: 13.1_

  - [ ]* 11.6 Write tests for admin endpoints
    - Test admin endpoints require staff permission
    - Test AI request log filtering and aggregation
    - Test brain config creation and validation
    - Test brain config activation
    - Test health check endpoint

- [x] 12. Subscription integration
  - [x] 12.1 Create signal handler for user creation
    - Create `apps/credits/signals.py` with post_save signal for User model
    - On user creation, create UserCredits record with credits based on subscription_tier
    - Use TIER_CREDIT_ALLOCATIONS to set monthly_credits
    - Set remaining_credits = monthly_credits, used_credits = 0
    - Set last_reset_date to current date
    - _Requirements: 1.2-1.9_

  - [x] 12.2 Create signal handler for subscription tier changes
    - Add post_save signal for subscription tier updates
    - On tier upgrade, update monthly_credits and add difference to remaining_credits
    - On tier downgrade, update monthly_credits but preserve remaining_credits
    - _Requirements: 2.7_

  - [x] 12.3 Update subscription service for brain mode validation
    - Modify `apps/subscription/services.py` to add can_access_brain_mode() method
    - Check user's tier against BRAIN_MODE_TIER_REQUIREMENTS
    - Return boolean result
    - _Requirements: 5.6, 5.7, 5.10_

  - [x] 12.4 Register signal handlers in app config
    - Modify `apps/credits/apps.py` to import signals in ready() method
    - Ensure signals are registered on app startup
    - _Requirements: 1.2_

  - [ ]* 12.5 Write property test for user credit initialization
    - **Property 1: User Credit Initialization**
    - **Validates: Requirements 1.2-1.9**
    - Use Hypothesis to generate users with all subscription tiers
    - Verify UserCredits initialized with correct monthly_credits for tier
    - Verify remaining_credits = monthly_credits, used_credits = 0

  - [ ]* 12.6 Write tests for subscription integration
    - Test UserCredits created on user creation
    - Test credits updated on tier upgrade
    - Test credits preserved on tier downgrade
    - Test can_access_brain_mode() for all tier/mode combinations

- [-] 13. Qwen to Cerebras migration
  - [x] 13.1 Create data migration to update Twin model records
    - Create data migration in `apps/twin/migrations/`
    - Update all Twin records where model='qwen' to model='cerebras'
    - Make migration reversible (cerebras→qwen on rollback)
    - _Requirements: 18.1_

  - [x] 13.2 Update subscription service model access checks
    - Modify `apps/subscription/services.py` model access validation
    - Replace 'qwen' with 'cerebras' in model availability checks
    - Update free_tier_models() to include 'cerebras'
    - _Requirements: 18.6_

  - [x] 13.3 Add Cerebras and Mistral configuration to settings
    - Add CEREBRAS_API_KEY to `neurotwin/settings.py`, load from environment variable
    - Add MISTRAL_API_KEY to `neurotwin/settings.py`, load from environment variable
    - Remove Qwen-specific configuration if exists
    - _Requirements: 18.7, 18.8_

  - [-] 13.4 Update test fixtures for Cerebras
    - Replace 'qwen' with 'cerebras' in all test fixtures
    - Update factory definitions if using factory_boy
    - Update mock data in tests
    - _Requirements: 18.5_

  - [ ]* 13.5 Write tests for migration
    - Test migration updates Twin records correctly
    - Test migration is reversible
    - Test no data loss during migration

- [ ] 14. Checkpoint - Backend API validation
  - Ensure all API endpoints return correct responses
  - Test credit deduction flow end-to-end
  - Test brain mode selection and validation
  - Test error handling for all error scenarios
  - Verify admin endpoints require proper permissions
  - Ask the user if questions arise


- [x] 15. Frontend type definitions and API client
  - [x] 15.1 Create Brain mode type definitions
    - Create `neuro-frontend/src/types/brain.ts`
    - Define BrainMode type: 'brain' | 'brain_pro' | 'brain_gen'
    - Define OperationType type: 'simple_response' | 'long_response' | 'summarization' | 'complex_reasoning' | 'automation'
    - Define BrainModeInfo interface with id, title, description, requiredTier, multiplier
    - _Requirements: 5.1-5.5_

  - [x] 15.2 Create credit type definitions
    - Create `neuro-frontend/src/types/credits.ts`
    - Define CreditBalance interface with monthly_credits, remaining_credits, used_credits, purchased_credits, last_reset_date, next_reset_date, days_until_reset, usage_percentage
    - Define CreditUsageLog interface with id, timestamp, credits_consumed, operation_type, brain_mode, model_used, request_id
    - Define CreditEstimate interface with estimated_cost, operation_type, brain_mode, estimated_tokens, sufficient_credits, remaining_credits
    - _Requirements: 1.10, 4.5, 10.3_

  - [x] 15.3 Create credit API client functions
    - Create `neuro-frontend/src/lib/api/credits.ts`
    - Implement getBalance(): Promise<CreditBalance>
    - Implement estimate(params): Promise<CreditEstimate>
    - Implement getUsage(filters): Promise<PaginatedResponse<CreditUsageLog>>
    - Implement getSummary(days): Promise<CreditUsageSummary>
    - Use existing api client with JWT authentication
    - _Requirements: 1.10, 4.5, 10.3, 10.7_

  - [x] 15.4 Create brain mode API client functions
    - Create `neuro-frontend/src/lib/api/brain.ts`
    - Implement getSettings(): Promise<UserSettings>
    - Implement updateSettings(brainMode): Promise<UserSettings>
    - _Requirements: 15.7, 15.8_

  - [x] 15.5 Update Twin API client for brain mode
    - Modify `neuro-frontend/src/lib/api/twin.ts` (or create if doesn't exist)
    - Update chat() function to accept brain_mode and operation_type parameters
    - Update response type to include metadata: brain_mode, model_used, tokens_used, credits_consumed, latency_ms, request_id
    - Add credits object to response: {remaining, consumed}
    - _Requirements: 15.1, 15.2, 9.11_

- [x] 16. Frontend custom hooks
  - [x] 16.1 Create useCredits hook for balance management
    - Create `neuro-frontend/src/hooks/useCredits.ts`
    - Use React Query with queryKey: ['credits', 'balance']
    - Set refetchInterval to 60000 (1 minute)
    - Set staleTime to 30000 (30 seconds)
    - Return data, isLoading, error, refetch
    - _Requirements: 13.11_

  - [x] 16.2 Create useCreditEstimate hook
    - Create `neuro-frontend/src/hooks/useCreditEstimate.ts`
    - Accept operationType, brainMode, estimatedTokens parameters
    - Use React Query with dynamic queryKey
    - Enable query only when operationType and brainMode are provided
    - _Requirements: 4.5_

  - [x] 16.3 Create useCreditUsage hook for history
    - Create `neuro-frontend/src/hooks/useCreditUsage.ts`
    - Accept filters parameter: startDate, endDate, operationType, brainMode, page
    - Use React Query with dynamic queryKey based on filters
    - Return paginated usage logs with summary
    - _Requirements: 10.3_

  - [x] 16.4 Create useBrainMode hook for preference management
    - Create `neuro-frontend/src/hooks/useBrainMode.ts`
    - Fetch current brain_mode from user settings
    - Provide setBrainMode mutation function
    - Invalidate settings query on successful update
    - Return brainMode, setBrainMode, isLoading
    - _Requirements: 5.8, 15.8_

  - [x]* 16.5 Write tests for custom hooks
    - Test useCredits fetches and caches balance
    - Test useCreditEstimate calculates correctly
    - Test useBrainMode updates preference
    - Test query invalidation after mutations

- [x] 17. BrainSelector component
  - [x] 17.1 Create BrainModeCard subcomponent
    - Create `neuro-frontend/src/components/brain/BrainModeCard.tsx`
    - Display mode icon, title, description, cost multiplier
    - Show lock icon and tier badge for restricted modes
    - Apply glass panel styling with backdrop blur
    - Show checkmark for selected mode
    - Add hover animation (scale and glow)
    - _Requirements: 12.2, 12.5, 12.6, 12.10_

  - [x] 17.2 Create BrainModeTooltip subcomponent
    - Create `neuro-frontend/src/components/brain/BrainModeTooltip.tsx`
    - Display tier requirement explanation
    - Show upgrade call-to-action for locked modes
    - _Requirements: 12.11_

  - [x] 17.3 Create BrainSelector main component
    - Create `neuro-frontend/src/components/brain/BrainSelector.tsx`
    - Accept props: currentMode, userTier, onModeChange, disabled
    - Render three BrainModeCard components in grid layout
    - Brain card: Cerebras icon, "Balanced - Fast and efficient", 1x multiplier
    - Brain Pro card: Star icon, "Advanced - Higher reasoning quality", 1.5x multiplier, PRO badge
    - Brain Gen card: Lightning icon, "Genius - Maximum intelligence", 2x multiplier, EXECUTIVE badge
    - Disable cards for modes not available to user's tier
    - Call onModeChange when available card clicked
    - _Requirements: 12.1-12.11_

  - [x] 17.4 Add BrainSelector to dashboard settings page
    - Integrate BrainSelector into user settings or dashboard page
    - Connect to useBrainMode hook
    - Show success toast on mode change
    - _Requirements: 5.8_

  - [x]* 17.5 Write tests for BrainSelector
    - Test renders three mode cards
    - Test locks cards for restricted modes
    - Test calls onModeChange when available card clicked
    - Test shows tier badges correctly
    - Test disabled prop prevents interaction

- [x] 18. CreditDisplay component
  - [x] 18.1 Create CreditProgressBar subcomponent
    - Create `neuro-frontend/src/components/credits/CreditProgressBar.tsx`
    - Display horizontal progress bar with percentage fill
    - Use color coding: green (<50%), yellow (50-80%), red (>80%)
    - Smooth animation on value change
    - _Requirements: 13.3, 13.4, 13.5, 13.6_

  - [x] 18.2 Create CreditDisplay main component
    - Create `neuro-frontend/src/components/credits/CreditDisplay.tsx`
    - Accept props: compact (boolean), showDetails (boolean)
    - Display format: "1,234 / 2,000 credits" with comma separators
    - Show CreditProgressBar with usage percentage
    - Show warning icon and message when usage > 80%
    - Show "Credits exhausted" message when remaining = 0
    - Show days until next reset countdown
    - Use glass panel styling with backdrop blur
    - _Requirements: 13.1-13.11_

  - [x] 18.3 Add CreditDisplay to dashboard header
    - Integrate CreditDisplay into dashboard header in compact mode
    - Connect to useCredits hook
    - Auto-refresh after AI requests
    - _Requirements: 13.11_

  - [x] 18.4 Add CreditDisplay to Twin chat interface
    - Integrate CreditDisplay into chat sidebar in full mode with details
    - Show real-time credit updates after each message
    - _Requirements: 13.10, 13.11_

  - [x]* 18.5 Write tests for CreditDisplay
    - Test displays balance correctly
    - Test shows warning at 80% usage
    - Test shows exhausted message at 0 credits
    - Test color coding based on usage percentage
    - Test compact and full modes


- [x] 19. CreditUsageHistory component
  - [x] 19.1 Create CreditUsageTable subcomponent
    - Create `neuro-frontend/src/components/credits/CreditUsageTable.tsx`
    - Display table with columns: timestamp, operation, brain_mode, model, credits_consumed
    - Support pagination with 20 records per page
    - Format timestamp as human-readable date/time
    - Add loading skeleton for data fetching
    - _Requirements: 14.2, 14.3_

  - [x] 19.2 Create CreditFilters subcomponent
    - Create `neuro-frontend/src/components/credits/CreditFilters.tsx`
    - Date range filter with presets: Today, Last 7 Days, Last 30 Days, Custom
    - Operation type dropdown filter
    - Brain mode dropdown filter
    - Apply/Reset buttons
    - _Requirements: 14.4, 14.5, 14.6_

  - [x] 19.3 Create CreditUsageChart subcomponent
    - Create `neuro-frontend/src/components/credits/CreditUsageChart.tsx`
    - Display line chart showing daily credit consumption over time
    - Use chart library (recharts or similar)
    - Show tooltip with date and credits consumed
    - _Requirements: 14.8_

  - [x] 19.4 Create CreditBreakdownPie subcomponent
    - Create `neuro-frontend/src/components/credits/CreditBreakdownPie.tsx`
    - Display pie chart for breakdown by category
    - Support two modes: by operation_type and by brain_mode
    - Show legend with percentages
    - _Requirements: 14.9, 14.10_

  - [x] 19.5 Create CreditUsageHistory main component
    - Create `neuro-frontend/src/components/credits/CreditUsageHistory.tsx`
    - Create page at route /dashboard/credits
    - Display summary cards: Total Credits Used, Average per Request, Most Used Mode
    - Render CreditUsageChart and two CreditBreakdownPie charts
    - Render CreditFilters and CreditUsageTable
    - Add CSV export button
    - Connect to useCreditUsage hook with filters
    - _Requirements: 14.1-14.11_

  - [x] 19.6 Implement CSV export functionality
    - Add exportToCSV() function to download filtered usage data
    - Format as CSV with headers: Timestamp, Operation, Brain Mode, Model, Credits
    - Trigger browser download
    - _Requirements: 14.11_

  - [x] 19.7 Add navigation link to credit usage page
    - Add "Credit Usage" link to dashboard sidebar navigation
    - Show credit icon next to link
    - _Requirements: 14.1_

  - [x]* 19.8 Write tests for CreditUsageHistory
    - Test table renders usage logs correctly
    - Test filters update query parameters
    - Test pagination works correctly
    - Test charts render with data
    - Test CSV export generates correct file

- [x] 20. ChatInterface integration with Brain mode
  - [x] 20.1 Update ChatInterface to include BrainSelector
    - Modify `neuro-frontend/src/components/twin/ChatInterface.tsx` (or create if doesn't exist)
    - Add sidebar with CreditDisplay and BrainSelector
    - Connect to useBrainMode hook for current selection
    - _Requirements: 5.8, 13.11_

  - [x] 20.2 Update chat message sending to include brain_mode
    - Modify sendMessage mutation to include brain_mode parameter
    - Use current brain_mode from useBrainMode hook
    - Set operation_type to 'long_response' by default
    - _Requirements: 15.1, 15.2_

  - [x] 20.3 Handle insufficient credits error in chat
    - Catch insufficient credits error from API
    - Display toast notification with error message
    - Show required credits and remaining balance
    - Provide link to upgrade subscription
    - Disable send button when credits = 0
    - _Requirements: 4.1, 4.2, 4.3, 19.1, 19.2_

  - [x] 20.4 Handle brain mode restricted error in chat
    - Catch brain mode restricted error from API
    - Display toast notification explaining tier requirement
    - Provide link to upgrade subscription
    - _Requirements: 5.10, 19.3_

  - [x] 20.5 Invalidate credit cache after successful message
    - Call queryClient.invalidateQueries(['credits', 'balance']) after successful response
    - Update CreditDisplay to show new balance
    - _Requirements: 13.10_

  - [x] 20.6 Display credits consumed in message metadata
    - Show credits consumed for each AI response
    - Display model used and brain mode in message footer
    - _Requirements: 9.11_

  - [x]* 20.7 Write tests for ChatInterface integration
    - Test BrainSelector appears in sidebar
    - Test CreditDisplay updates after message
    - Test insufficient credits disables send button
    - Test error handling for credit and tier errors

- [x] 21. Performance optimization
  - [x] 21.1 Implement Redis caching for credit balances
    - Verify Redis configuration in settings.py
    - Implement cache.get() and cache.set() in CreditManager.get_balance()
    - Set TTL to 60 seconds
    - Implement cache invalidation on deduction
    - _Requirements: 20.1, 20.2_

  - [x] 21.2 Implement database query optimization
    - Add select_related() for UserCredits.user queries
    - Add prefetch_related() for usage log queries
    - Use only() to fetch specific fields in list views
    - Use iterator() for large querysets in admin views
    - _Requirements: 20.3_

  - [x] 21.3 Implement connection pooling
    - Verify CONN_MAX_AGE setting in database configuration
    - Set to 600 seconds (10 minutes)
    - Add connect_timeout and statement_timeout options
    - _Requirements: 20.7_

  - [x] 21.4 Implement routing rule caching
    - Cache routing rules in memory with 5-minute TTL
    - Implement cache refresh on config update
    - Use threading.Lock for thread-safe cache access
    - _Requirements: 20.6_

  - [x] 21.5 Add database indexes
    - Verify all indexes created by migrations
    - Add composite indexes for common query patterns
    - Monitor query performance with Django Debug Toolbar (dev only)
    - _Requirements: 16.3, 16.6, 16.9_

  - [ ]* 21.6 Write performance tests
    - Test credit check latency < 50ms (p95)
    - Test concurrent credit deductions (100 simultaneous)
    - Test cache hit rate > 80%
    - Test usage history query < 200ms (p95)

- [x] 22. Security implementation
  - [x] 22.1 Implement API key encryption
    - Create encryption utility in `apps/core/encryption.py`
    - Use Fernet symmetric encryption for Cerebras API key
    - Store encryption key in environment variable ENCRYPTION_KEY
    - Encrypt keys before database storage, decrypt on retrieval
    - _Requirements: 22.1, 22.2_

  - [x] 22.2 Implement PII sanitization for logging
    - Create sanitize_prompt_for_logging() function in `apps/credits/utils.py`
    - Remove email addresses, phone numbers, credit card numbers using regex
    - Apply to all prompt logging in AIRequestLog
    - _Requirements: 22.4_

  - [x] 22.3 Implement rate limiting for credit endpoints
    - Add custom throttle class CreditRateThrottle in `apps/credits/throttling.py`
    - Set rate to 100 requests per hour per user
    - Apply to all credit endpoints
    - _Requirements: 22.5_

  - [x] 22.4 Implement RBAC for admin endpoints
    - Create IsAdminUser permission class
    - Require is_staff=True for admin endpoints
    - Add permission_classes to AdminAIRequestViewSet and AdminBrainConfigViewSet
    - _Requirements: 22.8_

  - [x] 22.5 Implement input validation
    - Validate brain_mode against enum values in serializers
    - Validate operation_type against enum values
    - Validate estimated_tokens is positive integer
    - Validate date ranges for usage queries
    - _Requirements: 22.9_

  - [x]* 22.6 Write security tests
    - Test API key encryption/decryption
    - Test PII sanitization removes sensitive data
    - Test rate limiting blocks excessive requests
    - Test admin endpoints require staff permission
    - Test input validation rejects invalid values


- [x] 23. Monitoring and observability
  - [x] 23.1 Implement Prometheus metrics
    - Install prometheus_client package: `uv add prometheus-client`
    - Create `apps/credits/metrics.py` with metric definitions
    - Define Counter: credit_checks_total, credit_deductions_total, ai_requests_total
    - Define Histogram: credit_check_latency_seconds, ai_request_latency_seconds
    - Instrument CreditManager and AIService methods
    - _Requirements: 23.1, 23.2_

  - [x] 23.2 Add metrics endpoint
    - Create /metrics endpoint in urls.py
    - Expose Prometheus metrics in text format
    - Require authentication or IP whitelist for production
    - _Requirements: 23.1_

  - [x] 23.3 Implement structured logging
    - Configure Django logging in settings.py
    - Use JSON formatter for structured logs
    - Log all credit operations with user_id, operation, amount, timestamp
    - Log all AI requests with request_id, brain_mode, model_used, latency_ms, status
    - Log all provider errors with full context
    - _Requirements: 19.9, 23.9_

  - [x] 23.4 Create monitoring dashboard configuration
    - Create Grafana dashboard JSON (optional, for documentation)
    - Define panels: credit consumption rate, AI request rate, success rate, latency percentiles
    - Define alerts: credit check latency > 100ms, AI request failure rate > 5%, provider failure rate > 10%
    - _Requirements: 23.4, 23.5, 23.6, 23.7, 23.8_

  - [x] 23.5 Implement health check logic
    - Implement health check in admin_views.py
    - Check database: execute simple query
    - Check Redis: execute ping command
    - Check Cerebras API: call health endpoint or test request
    - Check Gemini API: call health endpoint or test request
    - Return status and metrics
    - _Requirements: 23.10_

  - [ ]* 23.6 Write tests for monitoring
    - Test metrics are incremented correctly
    - Test health check detects failures
    - Test structured logging includes required fields

- [ ] 24. Background tasks and scheduled jobs
  - [ ] 24.1 Create credit reset scheduled task
    - Create `apps/credits/tasks.py` with check_and_reset_credits() function
    - Iterate all active users and call CreditManager.check_and_reset_if_needed()
    - Schedule to run daily at 00:00 UTC using Django-Q2
    - _Requirements: 2.1-2.6_

  - [ ] 24.2 Create usage log aggregation task
    - Create aggregate_usage_logs() function in tasks.py
    - Aggregate daily usage for analytics dashboard
    - Schedule to run hourly
    - _Requirements: 10.7_

  - [ ] 24.3 Create provider health check task
    - Create check_provider_health() function in tasks.py
    - Check health of all providers and update cache
    - Schedule to run every 5 minutes
    - _Requirements: 23.10_

  - [ ] 24.4 Register scheduled tasks
    - Configure Django-Q2 schedule in settings.py or admin
    - Register check_and_reset_credits as daily task
    - Register aggregate_usage_logs as hourly task
    - Register check_provider_health as cron task (*/5 * * * *)
    - _Requirements: 2.6_

  - [ ]* 24.5 Write tests for background tasks
    - Test check_and_reset_credits processes all users
    - Test aggregate_usage_logs creates summaries
    - Test check_provider_health updates cache
    - Test tasks handle errors gracefully

- [ ] 25. Error handling and recovery
  - [ ] 25.1 Create custom exception classes
    - Create `apps/credits/exceptions.py`
    - Define InsufficientCreditsError with remaining_credits and required_credits attributes
    - Define BrainModeRestrictedError with requested_mode, current_tier, required_tier attributes
    - Define ModelUnavailableError with attempted_models attribute
    - Define CerebrasAPIError, CerebrasTimeoutError, CerebrasAuthError
    - _Requirements: 4.1, 5.10, 6.7, 7.9_

  - [ ] 25.2 Implement custom exception handler
    - Create custom_exception_handler() in `apps/credits/exception_handlers.py`
    - Handle InsufficientCreditsError → 402 with details
    - Handle BrainModeRestrictedError → 403 with details
    - Handle ModelUnavailableError → 503 with details
    - Handle provider errors → 502 with sanitized message
    - Handle validation errors → 400 with field-level errors
    - _Requirements: 19.1-19.7_

  - [ ] 25.3 Implement retry logic for transient errors
    - Add retry decorator to provider API calls
    - Implement exponential backoff: 1s, 2s, 4s
    - Retry on rate limits (429) and server errors (5xx)
    - Do not retry on authentication errors (401) or validation errors (400)
    - _Requirements: 7.6_

  - [ ] 25.4 Implement circuit breaker for provider failures
    - Create CircuitBreaker class in `apps/credits/circuit_breaker.py`
    - Track failure rate per provider
    - Open circuit after 5 consecutive failures
    - Half-open after 60 seconds to test recovery
    - Close circuit after successful request
    - _Requirements: 23.6_

  - [ ] 25.5 Implement graceful degradation
    - If Redis unavailable, fall back to database queries
    - If primary model unavailable, use fallback models
    - If all providers down, return 503 Service Unavailable
    - Log degraded mode operations for monitoring
    - _Requirements: 6.7_

  - [ ]* 25.6 Write tests for error handling
    - Test custom exception handler returns correct status codes
    - Test retry logic with simulated failures
    - Test circuit breaker opens after failures
    - Test graceful degradation scenarios

- [ ] 26. Documentation and deployment preparation
  - [ ] 26.1 Update environment variables documentation
    - Document CEREBRAS_API_KEY in .env.example
    - Document ENCRYPTION_KEY for API key encryption
    - Document Redis configuration variables
    - Document Django-Q2 configuration variables
    - _Requirements: 7.4, 22.2_

  - [ ] 26.2 Create database migration checklist
    - Document migration order and dependencies
    - Document data migration for Qwen→Cerebras
    - Document rollback procedures
    - _Requirements: 18.1, 18.9_

  - [ ] 26.3 Create API documentation
    - Use drf-spectacular to generate OpenAPI schema
    - Document all credit endpoints with examples
    - Document brain mode parameters
    - Document error responses
    - _Requirements: 13.1-13.6_

  - [ ] 26.4 Update user guide documentation
    - Document Brain mode selection
    - Document credit system and monthly allocations
    - Document tier requirements for Brain modes
    - Document credit usage history page
    - _Requirements: 5.1-5.10, 14.1-14.11_

  - [ ] 26.5 Create deployment runbook
    - Document deployment steps
    - Document environment variable setup
    - Document migration execution
    - Document monitoring setup
    - Document rollback procedures
    - _Requirements: 18.9_

- [ ] 27. Final integration testing
  - [ ] 27.1 End-to-end test: User signup to first AI request
    - Create new user account
    - Verify UserCredits initialized with correct allocation
    - Select Brain mode
    - Send chat message
    - Verify credits deducted
    - Verify response returned with metadata
    - _Requirements: 1.2-1.9, 5.8, 9.1-9.11_

  - [ ] 27.2 End-to-end test: Monthly credit reset
    - Create user with used credits
    - Simulate first day of month
    - Trigger reset check
    - Verify credits reset to monthly allocation
    - Verify reset logged
    - _Requirements: 2.1-2.5_

  - [ ] 27.3 End-to-end test: Tier upgrade flow
    - Create FREE tier user
    - Attempt to select Brain Pro mode
    - Verify restricted error
    - Upgrade to PRO tier
    - Verify Brain Pro mode now accessible
    - Verify credits updated
    - _Requirements: 2.7, 5.6, 5.7, 5.10_

  - [ ] 27.4 End-to-end test: Credit exhaustion and recovery
    - Create user with low credits
    - Send requests until credits exhausted
    - Verify 402 error on next request
    - Verify send button disabled in UI
    - Simulate monthly reset
    - Verify credits restored and requests work again
    - _Requirements: 4.1-4.3, 13.8, 13.9_

  - [ ] 27.5 End-to-end test: Provider fallback
    - Mock Cerebras API failure
    - Send request with Brain mode (simple_response)
    - Verify fallback to Gemini 2.5 Flash
    - Verify request succeeds
    - Verify fallback logged
    - _Requirements: 6.7, 6.8_

  - [ ]* 27.6 Write integration test suite
    - Test complete request flow with all components
    - Test error scenarios end-to-end
    - Test concurrent requests
    - Test cache behavior under load

- [ ] 28. Final checkpoint - System validation
  - Run complete test suite (unit + property + integration)
  - Verify all migrations apply cleanly
  - Verify all API endpoints return correct responses
  - Verify frontend components render correctly
  - Verify monitoring and logging working
  - Verify performance targets met (credit check < 50ms, AI request < 5s)
  - Ask the user if questions arise

## Notes

- Tasks marked with `*` are optional testing tasks and can be skipped for faster MVP
- Each task references specific requirements for traceability
- Property tests validate universal correctness properties across input space
- Unit tests validate specific examples and edge cases
- Integration tests validate end-to-end flows
- Checkpoints ensure incremental validation at key milestones
- Backend uses Python/Django with DRF, frontend uses TypeScript/Next.js
- All business logic in services, not views or serializers
- Redis caching for performance, PostgreSQL for persistence
- Comprehensive error handling with custom exceptions
- Security: API key encryption, PII sanitization, rate limiting, RBAC
- Monitoring: Prometheus metrics, structured logging, health checks
- Background tasks: Daily credit reset, hourly aggregation, provider health checks
