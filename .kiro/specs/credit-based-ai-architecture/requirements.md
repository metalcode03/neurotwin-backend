# Requirements Document

## Introduction

This document defines requirements for transforming the NeuroTwin platform into a scalable credit-based AI usage architecture with intelligent model routing through a Brain abstraction system. The feature replaces the current direct model selection approach with three Brain modes (Brain, Brain Pro, Brain Gen) that automatically route requests to appropriate AI models based on task complexity and user subscription tier. The system introduces credit tracking, consumption logic, and replaces Qwen with Cerebras while maintaining backward compatibility with existing Gemini models. This architecture provides controlled AI usage, predictable costs, and a simplified user experience that hides technical model details behind intelligent Brain modes.

## Glossary

- **Credit_System**: Backend service that tracks user credit balances, consumption, and monthly resets
- **Credit**: Unit of AI usage currency consumed per request based on operation type, token usage, and Brain level
- **Brain_Mode**: User-facing AI intelligence level abstraction (Brain, Brain Pro, Brain Gen) that replaces direct model selection
- **Brain**: Default mode using Cerebras, Gemini 2.5 Flash, Gemini 2.5 Pro - cost-efficient and fast
- **Brain_Pro**: Paid tier mode using Brain models plus Gemini 3 Pro as primary - higher reasoning quality
- **Brain_Gen**: Advanced mode using Brain Pro models plus Gemini 3.1 Pro as primary - highest intelligence
- **Model_Router**: Backend service that selects appropriate AI model based on Brain mode and task type
- **Cerebras**: High-performance AI model provider replacing Qwen in the platform
- **AI_Service**: Unified service layer that orchestrates credit validation, model routing, and request execution
- **Credit_Manager**: Service responsible for credit balance operations, deductions, and reset logic
- **Operation_Type**: Classification of AI request complexity (simple_response, long_response, summarization, complex_reasoning, automation)
- **Token_Usage**: Estimated or actual number of tokens consumed by an AI request
- **Monthly_Reset**: Automatic process that restores user credits to plan allocation on the first day of each month
- **Credit_Top_Up**: Future capability for users to purchase additional credits beyond monthly allocation
- **Subscription_Tier**: User plan level (FREE, PRO, TWIN+, EXECUTIVE) that determines credit allocation and Brain access
- **Credit_Usage_Log**: Audit record of credit consumption with timestamp, amount, operation type, and Brain mode
- **AI_Request_Log**: Audit record of AI requests with model used, tokens consumed, and response metadata
- **Provider_Abstraction**: Service layer pattern isolating AI provider implementations (Cerebras_Service, Gemini_Service)

## Requirements

### Requirement 1: Credit Balance Tracking

**User Story:** As a user, I want my AI usage tracked through credits, so that I understand my consumption and remaining capacity.

#### Acceptance Criteria

1. THE Credit_System SHALL store monthly_credits, remaining_credits, used_credits, and last_reset_date for each User
2. WHEN a User is created, THE Credit_System SHALL initialize credits based on their Subscription_Tier
3. THE Credit_System SHALL set monthly_credits to 50 for FREE tier users
4. THE Credit_System SHALL set monthly_credits to 2000 for PRO tier users
5. THE Credit_System SHALL set monthly_credits to 5000 for TWIN+ tier users
6. THE Credit_System SHALL set monthly_credits to 10000 for EXECUTIVE tier users
7. THE Credit_System SHALL initialize remaining_credits equal to monthly_credits
8. THE Credit_System SHALL initialize used_credits to 0
9. THE Credit_System SHALL set last_reset_date to the current date
10. THE Credit_System SHALL expose remaining_credits through API endpoint GET /api/v1/credits/balance

### Requirement 2: Monthly Credit Reset

**User Story:** As a user, I want my credits automatically reset each month, so that I receive my full monthly allocation.

#### Acceptance Criteria

1. THE Credit_System SHALL check if current date is first day of month and last_reset_date is in previous month
2. WHEN reset conditions are met, THE Credit_System SHALL set remaining_credits equal to monthly_credits
3. WHEN reset occurs, THE Credit_System SHALL set used_credits to 0
4. WHEN reset occurs, THE Credit_System SHALL update last_reset_date to current date
5. THE Credit_System SHALL log each reset event with user_id, previous_balance, new_balance, and timestamp
6. THE Credit_System SHALL execute reset checks before processing any AI request
7. WHEN a User upgrades Subscription_Tier mid-month, THE Credit_System SHALL update monthly_credits and add the difference to remaining_credits

### Requirement 3: Credit Consumption Logic

**User Story:** As a system, I want to calculate credit costs based on operation complexity and Brain level, so that usage is fairly metered.

#### Acceptance Criteria

1. THE Credit_Manager SHALL calculate credit cost using formula: base_cost × token_multiplier × brain_multiplier
2. THE Credit_Manager SHALL assign base_cost of 1 for simple_response operations
3. THE Credit_Manager SHALL assign base_cost of 3 for long_response operations
4. THE Credit_Manager SHALL assign base_cost of 2 for summarization operations
5. THE Credit_Manager SHALL assign base_cost of 5 for complex_reasoning operations
6. THE Credit_Manager SHALL assign base_cost of 8 for automation operations
7. THE Credit_Manager SHALL calculate token_multiplier as estimated_tokens divided by 1000
8. THE Credit_Manager SHALL apply brain_multiplier of 1.0 for Brain mode
9. THE Credit_Manager SHALL apply brain_multiplier of 1.5 for Brain_Pro mode
10. THE Credit_Manager SHALL apply brain_multiplier of 2.0 for Brain_Gen mode
11. THE Credit_Manager SHALL round final credit cost to nearest integer with minimum of 1 credit

### Requirement 4: Credit Validation and Blocking

**User Story:** As a system, I want to block AI requests when users have insufficient credits, so that usage stays within allocated limits.

#### Acceptance Criteria

1. WHEN remaining_credits equals 0, THE AI_Service SHALL reject requests with error code 402 Payment Required
2. WHEN remaining_credits is less than estimated cost, THE AI_Service SHALL reject requests with error message "Insufficient credits"
3. THE AI_Service SHALL return current remaining_credits and required credits in error response
4. THE AI_Service SHALL allow requests to proceed when remaining_credits is greater than or equal to estimated cost
5. THE Credit_System SHALL provide endpoint GET /api/v1/credits/estimate that accepts operation_type and brain_mode and returns estimated cost
6. WHEN a User reaches 80% credit usage, THE Credit_System SHALL set a warning flag visible in frontend
7. WHEN a User reaches 100% credit usage, THE Credit_System SHALL send notification about credit exhaustion

### Requirement 5: Brain Mode Abstraction

**User Story:** As a user, I want to select Brain intelligence levels instead of specific models, so that I have a simplified AI experience.

#### Acceptance Criteria

1. THE System SHALL remove all direct model selection UI from frontend
2. THE System SHALL provide Brain mode selector with three options: Brain, Brain Pro, Brain Gen
3. THE System SHALL display Brain as "Balanced - Fast and efficient" with default selection
4. THE System SHALL display Brain_Pro as "Advanced - Higher reasoning" with PRO tier badge
5. THE System SHALL display Brain_Gen as "Genius - Maximum intelligence" with EXECUTIVE tier badge
6. THE System SHALL disable Brain_Pro selection for FREE tier users
7. THE System SHALL disable Brain_Gen selection for FREE and PRO tier users
8. WHEN a User selects a Brain mode, THE System SHALL store preference in user settings
9. THE System SHALL include brain_mode parameter in all AI request payloads
10. THE System SHALL validate brain_mode against user Subscription_Tier before processing requests

### Requirement 6: Model Routing for Brain Mode

**User Story:** As a system, I want to automatically route requests to appropriate models based on Brain mode, so that users receive optimal performance.

#### Acceptance Criteria

1. THE Model_Router SHALL accept brain_mode and operation_type as input parameters
2. WHEN brain_mode is Brain and operation_type is simple_response, THE Model_Router SHALL select Cerebras
3. WHEN brain_mode is Brain and operation_type is long_response, THE Model_Router SHALL select Gemini 2.5 Flash
4. WHEN brain_mode is Brain and operation_type is summarization, THE Model_Router SHALL select Mistral
5. WHEN brain_mode is Brain and operation_type is complex_reasoning, THE Model_Router SHALL select Gemini 2.5 Pro
5. WHEN brain_mode is Brain_Pro, THE Model_Router SHALL prioritize Gemini 3 Pro for all operation types
6. WHEN brain_mode is Brain_Gen, THE Model_Router SHALL prioritize Gemini 3.1 Pro for all operation types
7. THE Model_Router SHALL implement fallback logic to secondary models when primary model fails
8. THE Model_Router SHALL log selected model, brain_mode, operation_type, and selection_reason for each routing decision
9. THE Model_Router SHALL be configurable through admin settings without code deployment
10. THE Model_Router SHALL support A/B testing by routing percentage of requests to alternative models

### Requirement 7: Cerebras Integration

**User Story:** As a system, I want to integrate Cerebras API as a model provider, so that Brain mode has access to high-performance inference.

#### Acceptance Criteria

1. THE System SHALL remove all Qwen model references from codebase
2. THE System SHALL create Cerebras_Service in provider abstraction layer
3. THE Cerebras_Service SHALL implement generate_response method accepting prompt, system_prompt, max_tokens, and temperature
4. THE Cerebras_Service SHALL use CEREBRAS_API_KEY from environment variables
5. THE Cerebras_Service SHALL handle authentication, request formatting, and response parsing
6. THE Cerebras_Service SHALL implement exponential backoff for rate limit errors
7. THE Cerebras_Service SHALL set default timeout of 30 seconds for API calls
8. THE Cerebras_Service SHALL log all requests with timestamp, prompt_length, response_length, and latency
9. WHEN Cerebras API returns error, THE Cerebras_Service SHALL raise CerebrasAPIError with error details
10. THE Cerebras_Service SHALL support async execution for non-blocking operations

### Requirement 8: Provider Abstraction Layer

**User Story:** As a developer, I want a unified interface for AI providers, so that adding or swapping models is straightforward.

#### Acceptance Criteria

1. THE System SHALL define AIProvider abstract base class with generate_response and generate_embeddings methods
2. THE System SHALL implement Cerebras_Service extending AIProvider
3. THE System SHALL implement Gemini_Service extending AIProvider
4. THE Gemini_Service SHALL support model parameter for selecting Gemini 2.5 Flash, 2.5 Pro, 3 Pro, or 3.1 Pro
5. THE AIProvider interface SHALL enforce consistent error handling across all implementations
6. THE AIProvider interface SHALL enforce consistent logging format across all implementations
7. THE Model_Router SHALL interact only with AIProvider interface, never directly with provider implementations
8. THE System SHALL register all provider implementations in a provider registry for dynamic lookup
9. THE System SHALL support provider-specific configuration through JSON settings stored in database
10. THE System SHALL validate provider availability before routing requests

### Requirement 9: AI Service Orchestration

**User Story:** As a system, I want a unified AI service that orchestrates credit validation, routing, and execution, so that all AI requests follow consistent flow.

#### Acceptance Criteria

1. THE AI_Service SHALL accept user_id, prompt, brain_mode, operation_type, and context as input
2. THE AI_Service SHALL validate User has sufficient credits before proceeding
3. THE AI_Service SHALL estimate credit cost using Credit_Manager
4. THE AI_Service SHALL call Model_Router to select appropriate model
5. THE AI_Service SHALL retrieve selected provider from provider registry
6. THE AI_Service SHALL execute request through provider's generate_response method
7. THE AI_Service SHALL deduct actual credits from User's remaining_credits after successful response
8. THE AI_Service SHALL create Credit_Usage_Log record with timestamp, amount, operation_type, brain_mode, and model_used
9. THE AI_Service SHALL create AI_Request_Log record with request details, response metadata, and execution time
10. IF request fails, THE AI_Service SHALL NOT deduct credits and SHALL log failure reason
11. THE AI_Service SHALL return response content, tokens_used, model_used, and credits_consumed

### Requirement 10: Credit Usage Logging

**User Story:** As a user, I want to view my credit usage history, so that I understand how credits are consumed.

#### Acceptance Criteria

1. THE Credit_System SHALL create Credit_Usage_Log record for every credit deduction
2. THE Credit_Usage_Log SHALL store user_id, timestamp, credits_consumed, operation_type, brain_mode, model_used, and request_id
3. THE Credit_System SHALL provide endpoint GET /api/v1/credits/usage that returns paginated usage logs
4. THE endpoint SHALL support filtering by date_range, operation_type, and brain_mode
5. THE endpoint SHALL return total credits consumed for filtered period
6. THE endpoint SHALL calculate average credits per request for filtered period
7. THE Credit_System SHALL provide endpoint GET /api/v1/credits/usage/summary that returns daily aggregated usage for last 30 days
8. THE summary SHALL include breakdown by operation_type and brain_mode
9. THE Credit_Usage_Log SHALL be indexed on user_id and timestamp for query performance
10. THE System SHALL retain Credit_Usage_Log records for minimum 12 months

### Requirement 11: AI Request Audit Logging

**User Story:** As an administrator, I want detailed logs of all AI requests, so that I can monitor system usage and debug issues.

#### Acceptance Criteria

1. THE AI_Service SHALL create AI_Request_Log record for every AI request
2. THE AI_Request_Log SHALL store user_id, timestamp, brain_mode, operation_type, model_used, prompt_length, response_length, tokens_used, credits_consumed, latency_ms, and status
3. THE AI_Request_Log SHALL store error_message and error_type when requests fail
4. THE AI_Request_Log SHALL store cognitive_blend_value when request is Twin-initiated
5. THE System SHALL provide admin endpoint GET /api/v1/admin/ai-requests that returns paginated request logs
6. THE endpoint SHALL support filtering by user_id, brain_mode, model_used, status, and date_range
7. THE endpoint SHALL calculate aggregate metrics: total requests, success rate, average latency, and total tokens
8. THE AI_Request_Log SHALL be indexed on user_id, timestamp, and status for query performance
9. THE System SHALL retain AI_Request_Log records for minimum 90 days
10. THE System SHALL implement log rotation to archive records older than 90 days

### Requirement 12: Frontend Brain Selector Component

**User Story:** As a user, I want to select my preferred Brain mode from the dashboard, so that I control AI intelligence level.

#### Acceptance Criteria

1. THE Frontend SHALL create BrainSelector component with three mode cards
2. THE BrainSelector SHALL display Brain card with Cerebras icon, "Balanced" title, and "Fast and efficient" description
3. THE BrainSelector SHALL display Brain_Pro card with star icon, "Advanced" title, and "Higher reasoning quality" description
4. THE BrainSelector SHALL display Brain_Gen card with lightning icon, "Genius" title, and "Maximum intelligence" description
5. THE BrainSelector SHALL show PRO badge on Brain_Pro card when user is FREE tier
6. THE BrainSelector SHALL show EXECUTIVE badge on Brain_Gen card when user is not EXECUTIVE tier
7. THE BrainSelector SHALL disable and gray out cards for modes not available to user's tier
8. WHEN user clicks available mode card, THE BrainSelector SHALL highlight selection and update user preference
9. THE BrainSelector SHALL call PUT /api/v1/users/settings with brain_mode parameter
10. THE BrainSelector SHALL display current selection with checkmark icon
11. THE BrainSelector SHALL show tooltip explaining tier requirements when hovering over locked modes

### Requirement 13: Frontend Credit Display

**User Story:** As a user, I want to see my remaining credits in the dashboard, so that I monitor my usage.

#### Acceptance Criteria

1. THE Frontend SHALL create CreditDisplay component showing remaining credits and monthly allocation
2. THE CreditDisplay SHALL display as "1,234 / 2,000 credits" format with comma separators
3. THE CreditDisplay SHALL show progress bar visualizing credit consumption percentage
4. THE CreditDisplay SHALL use green color when usage is below 50%
5. THE CreditDisplay SHALL use yellow color when usage is between 50% and 80%
6. THE CreditDisplay SHALL use red color when usage is above 80%
7. THE CreditDisplay SHALL display warning icon and message when usage exceeds 80%
8. THE CreditDisplay SHALL display "Credits exhausted" message when remaining_credits equals 0
9. THE CreditDisplay SHALL show days until next reset with countdown
10. THE CreditDisplay SHALL refresh credit balance after each AI request
11. THE CreditDisplay SHALL be visible in dashboard header and Twin chat interface

### Requirement 14: Frontend Credit Usage History

**User Story:** As a user, I want to view my credit usage history, so that I understand consumption patterns.

#### Acceptance Criteria

1. THE Frontend SHALL create CreditUsageHistory component at route /dashboard/credits
2. THE CreditUsageHistory SHALL display table with columns: timestamp, operation, brain_mode, model, credits_consumed
3. THE CreditUsageHistory SHALL support pagination with 20 records per page
4. THE CreditUsageHistory SHALL provide date range filter with presets: Today, Last 7 Days, Last 30 Days, Custom
5. THE CreditUsageHistory SHALL provide operation_type filter dropdown
6. THE CreditUsageHistory SHALL provide brain_mode filter dropdown
7. THE CreditUsageHistory SHALL display total credits consumed for filtered period at top
8. THE CreditUsageHistory SHALL display chart showing daily credit consumption over time
9. THE CreditUsageHistory SHALL display breakdown pie chart by operation_type
10. THE CreditUsageHistory SHALL display breakdown pie chart by brain_mode
11. THE CreditUsageHistory SHALL export filtered data as CSV when user clicks export button

### Requirement 15: API Integration for Brain Mode

**User Story:** As a frontend developer, I want API endpoints that accept brain_mode parameter, so that I can integrate Brain selection.

#### Acceptance Criteria

1. THE System SHALL modify POST /api/v1/twin/chat endpoint to accept brain_mode parameter
2. THE System SHALL modify POST /api/v1/twin/generate endpoint to accept brain_mode parameter
3. THE System SHALL validate brain_mode is one of: brain, brain_pro, brain_gen
4. THE System SHALL return 400 Bad Request when brain_mode is invalid
5. THE System SHALL return 403 Forbidden when user's tier does not allow selected brain_mode
6. THE System SHALL use user's saved brain_mode preference when parameter is not provided
7. THE System SHALL provide GET /api/v1/users/settings endpoint returning current brain_mode preference
8. THE System SHALL provide PUT /api/v1/users/settings endpoint accepting brain_mode parameter
9. THE System SHALL validate brain_mode against user's Subscription_Tier before saving preference
10. THE System SHALL return updated settings including brain_mode after successful update

### Requirement 16: Database Schema for Credits

**User Story:** As a developer, I want database models for credit tracking, so that credit data is persisted reliably.

#### Acceptance Criteria

1. THE System SHALL create UserCredits model with fields: user_id, monthly_credits, remaining_credits, used_credits, last_reset_date, created_at, updated_at
2. THE UserCredits model SHALL have one-to-one relationship with User model
3. THE UserCredits model SHALL have database index on user_id
4. THE System SHALL create CreditUsageLog model with fields: id, user_id, timestamp, credits_consumed, operation_type, brain_mode, model_used, request_id, created_at
5. THE CreditUsageLog model SHALL have foreign key to User model
6. THE CreditUsageLog model SHALL have database indexes on user_id and timestamp
7. THE System SHALL create AIRequestLog model with fields: id, user_id, timestamp, brain_mode, operation_type, model_used, prompt_length, response_length, tokens_used, credits_consumed, latency_ms, status, error_message, error_type, cognitive_blend_value, created_at
8. THE AIRequestLog model SHALL have foreign key to User model
9. THE AIRequestLog model SHALL have database indexes on user_id, timestamp, and status
10. THE System SHALL create database migration to add brain_mode field to existing Twin model

### Requirement 17: Credit Top-Up Foundation

**User Story:** As a system, I want infrastructure for future credit top-up purchases, so that users can buy additional credits.

#### Acceptance Criteria

1. THE UserCredits model SHALL include purchased_credits field initialized to 0
2. THE Credit_Manager SHALL add purchased_credits to available balance when calculating remaining_credits
3. THE Credit_Manager SHALL deduct from purchased_credits before deducting from monthly_credits
4. THE System SHALL create CreditTopUp model with fields: id, user_id, amount, price_paid, payment_method, transaction_id, status, created_at
5. THE CreditTopUp model SHALL have foreign key to User model
6. THE CreditTopUp model SHALL have status choices: pending, completed, failed, refunded
7. THE System SHALL provide placeholder endpoint POST /api/v1/credits/top-up that returns "Not implemented" with 501 status
8. THE Credit_System SHALL display purchased_credits separately from monthly_credits in balance response
9. THE System SHALL reset only monthly_credits during monthly reset, preserving purchased_credits
10. THE System SHALL log credit source (monthly or purchased) in Credit_Usage_Log

### Requirement 18: Migration from Qwen to Cerebras

**User Story:** As a developer, I want to cleanly migrate from Qwen to Cerebras, so that existing functionality is preserved.

#### Acceptance Criteria

1. THE System SHALL create database migration to update all Twin records with model='qwen' to model='cerebras'
2. THE System SHALL update AIModel enum to replace QWEN with CEREBRAS
3. THE System SHALL update all model choice lists to replace 'Qwen' with 'Cerebras'
4. THE System SHALL update TierFeatures dataclasses to replace 'qwen' with 'cerebras' in available_models
5. THE System SHALL update all test fixtures to replace 'qwen' with 'cerebras'
6. THE System SHALL update subscription service model access checks to recognize 'cerebras'
7. THE System SHALL remove Qwen-specific configuration from settings
8. THE System SHALL add Cerebras-specific configuration to settings with CEREBRAS_API_KEY
9. THE migration SHALL be reversible to allow rollback if needed
10. THE System SHALL maintain backward compatibility for any external integrations referencing model names

### Requirement 19: Error Handling for Credit Operations

**User Story:** As a user, I want clear error messages when credit operations fail, so that I understand what went wrong.

#### Acceptance Criteria

1. WHEN remaining_credits is 0, THE System SHALL return error with code "CREDITS_EXHAUSTED" and message "You have used all your credits for this month"
2. WHEN estimated cost exceeds remaining_credits, THE System SHALL return error with code "INSUFFICIENT_CREDITS" and include required and available amounts
3. WHEN brain_mode is not allowed for user's tier, THE System SHALL return error with code "BRAIN_MODE_RESTRICTED" and required tier information
4. WHEN credit deduction fails due to race condition, THE System SHALL retry operation up to 3 times
5. WHEN credit reset fails, THE System SHALL log error and send alert to administrators
6. WHEN provider API fails, THE System SHALL return error without deducting credits
7. THE System SHALL include next_reset_date in all credit-related error responses
8. THE System SHALL include upgrade_url in error responses for tier-restricted features
9. THE System SHALL log all credit operation errors with user_id, operation, error_type, and context
10. THE System SHALL provide user-friendly error messages that avoid technical jargon

### Requirement 20: Performance Optimization for Credit Checks

**User Story:** As a system, I want credit checks to be fast, so that AI requests are not delayed.

#### Acceptance Criteria

1. THE Credit_System SHALL cache user credit balance in Redis with 60 second TTL
2. THE Credit_System SHALL invalidate cache immediately after credit deduction
3. THE Credit_System SHALL use database transactions to ensure atomic credit deduction
4. THE Credit_System SHALL use SELECT FOR UPDATE to prevent race conditions during deduction
5. THE Credit_Manager SHALL pre-calculate and cache operation base costs
6. THE Model_Router SHALL cache routing rules in memory with 5 minute refresh interval
7. THE System SHALL use database connection pooling for credit operations
8. THE System SHALL implement batch credit deduction for multiple simultaneous requests from same user
9. THE System SHALL monitor credit check latency and alert when p95 exceeds 50ms
10. THE System SHALL use read replicas for credit usage history queries to reduce load on primary database

## Parser and Serializer Requirements

### Requirement 21: Brain Mode Configuration Parser

**User Story:** As a developer, I want to parse Brain mode routing configurations, so that routing rules can be updated without code changes.

#### Acceptance Criteria

1. THE System SHALL provide Brain_Config_Parser that parses JSON routing configurations into routing rule objects
2. WHEN parsing configuration, THE Parser SHALL validate that all required fields (brain_mode, operation_type, primary_model, fallback_models) are present
3. THE Parser SHALL validate that model references exist in provider registry
4. THE Parser SHALL validate that brain_mode values are valid enum members
5. THE System SHALL provide Brain_Config_Printer that serializes routing rule objects back to JSON format
6. FOR ALL valid Brain configuration JSON, parsing then printing then parsing SHALL produce an equivalent configuration structure (round-trip property)
7. WHEN parsing fails due to invalid JSON structure, THE Parser SHALL return descriptive error messages indicating the validation failure
8. THE Parser SHALL support variable substitution for environment-specific model identifiers
9. THE System SHALL validate routing configuration on application startup and fail fast if invalid
10. THE System SHALL provide admin endpoint POST /api/v1/admin/brain-config that accepts JSON configuration and validates before saving

## Non-Functional Requirements

### Requirement 22: Security and Data Protection

**User Story:** As a user, I want my AI usage data protected, so that my privacy is maintained.

#### Acceptance Criteria

1. THE System SHALL encrypt Cerebras API keys using Fernet symmetric encryption before database storage
2. THE System SHALL store encryption key in environment variables, never in code or database
3. THE System SHALL use HTTPS for all Cerebras API requests
4. THE System SHALL sanitize user prompts before logging to remove PII
5. THE System SHALL implement rate limiting on credit endpoints to prevent abuse (maximum 100 requests per minute per user)
6. THE System SHALL log all credit balance modifications in audit log with timestamp and actor
7. THE System SHALL require authentication for all credit-related endpoints
8. THE System SHALL implement RBAC for admin endpoints with separate admin role
9. THE System SHALL validate all brain_mode and operation_type inputs against allowed values
10. THE System SHALL implement CSRF protection for all credit modification endpoints

### Requirement 23: Monitoring and Alerting

**User Story:** As an administrator, I want monitoring for credit system health, so that issues are detected quickly.

#### Acceptance Criteria

1. THE System SHALL expose Prometheus metrics for credit operations: credit_checks_total, credit_deductions_total, credit_check_latency_seconds
2. THE System SHALL expose metrics for AI requests: ai_requests_total, ai_request_latency_seconds, ai_request_tokens_total
3. THE System SHALL expose metrics for model routing: model_selections_total, model_failures_total
4. THE System SHALL alert when credit check p95 latency exceeds 100ms
5. THE System SHALL alert when AI request failure rate exceeds 5% over 5 minute window
6. THE System SHALL alert when any provider has failure rate exceeding 10%
7. THE System SHALL create dashboard showing real-time credit consumption across all users
8. THE System SHALL create dashboard showing model usage distribution by Brain mode
9. THE System SHALL log all provider API errors with full context for debugging
10. THE System SHALL implement health check endpoint GET /api/v1/health that validates credit system and provider availability

### Requirement 24: Backward Compatibility

**User Story:** As a developer, I want existing API clients to continue working, so that migration is smooth.

#### Acceptance Criteria

1. THE System SHALL accept requests without brain_mode parameter and use user's saved preference
2. THE System SHALL maintain existing model field on Twin model for backward compatibility
3. THE System SHALL map legacy model values to appropriate Brain modes automatically
4. THE System SHALL continue to support existing /api/v1/twin/chat endpoint signature
5. THE System SHALL provide deprecation warnings in API responses when legacy parameters are used
6. THE System SHALL maintain existing response format while adding new brain_mode and credits_consumed fields
7. THE System SHALL support gradual rollout with feature flag to enable/disable credit system
8. THE System SHALL allow administrators to grant unlimited credits to specific users for testing
9. THE System SHALL provide migration guide documenting API changes and new parameters
10. THE System SHALL maintain API versioning with v1 supporting legacy behavior and v2 requiring brain_mode

