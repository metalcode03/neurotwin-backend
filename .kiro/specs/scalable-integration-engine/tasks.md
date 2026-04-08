# Implementation Plan: Scalable Integration Engine

## Overview

This implementation plan breaks down the Scalable Integration Engine into discrete coding tasks. The system refactors the NeuroTwin backend integration architecture to support multiple authentication strategies (OAuth, Meta, API Key), queue-based message processing with Celery, Redis-based rate limiting, and fault-tolerant operations. Implementation follows Django/DRF patterns with business logic in services, validation in serializers, and async processing for external operations.

## Tasks

- [x] 1. Set up Django app structure and core models
  - Create `apps/automation` Django app if not exists
  - Define model choices and enums (AuthType, IntegrationCategory, MessageDirection, MessageStatus)
  - Create base model structure with created_at/updated_at fields
  - _Requirements: 1.1, 2.1, 15.1, 22.1_

- [x] 2. Implement database models
  - [x] 2.1 Create IntegrationTypeModel with multi-auth support
    - Add fields: type, name, description, auth_type, auth_config, rate_limit_config, category, is_active
    - Add database indexes on auth_type, category, is_active
    - Add Meta class with db_table and composite indexes
    - _Requirements: 1.1-1.7, 26.1-26.7_

  - [x] 2.2 Create Integration model with encrypted credentials
    - Add fields: user, integration_type, access_token_encrypted, refresh_token_encrypted, api_key_encrypted
    - Add Meta-specific fields: waba_id, phone_number_id, business_id
    - Add fields: token_expires_at, user_config, status, health_status, consecutive_failures
    - Add database indexes and unique_together constraint
    - _Requirements: 2.1-2.7, 23.1-23.7_

  - [x] 2.3 Create InstallationSession model
    - Add fields: user, integration_type, oauth_state, status, progress, error_message, expires_at
    - Override save() to set expires_at to 15 minutes from creation
    - Add database indexes on oauth_state, status, expires_at
    - _Requirements: 3.1-3.7_

  - [x] 2.4 Create Conversation model
    - Add fields: integration, external_contact_id, external_contact_name, status, last_message_at
    - Add unique_together constraint on integration and external_contact_id
    - Add database indexes for query optimization
    - _Requirements: 15.1-15.2, 20.1-20.3_

  - [x] 2.5 Create Message model
    - Add fields: conversation, direction, content, status, external_message_id, retry_count, last_retry_at, metadata
    - Add database indexes on conversation, status, external_message_id, created_at
    - _Requirements: 15.3-15.7, 21.1-21.7_

  - [x] 2.6 Create WebhookEvent model
    - Add fields: integration_type, integration, payload, signature, status, error_message, processed_at
    - Add database indexes on status and created_at
    - _Requirements: 10.4, 22.1-22.7_


- [x] 3. Implement security and encryption layer
  - [x] 3.1 Create TokenEncryption utility class
    - Implement encrypt() method using Fernet symmetric encryption
    - Implement decrypt() method with auth_type parameter
    - Implement _get_encryption_key() to retrieve keys from environment variables
    - Support separate keys for oauth, meta, api_key auth types
    - _Requirements: 17.1-17.4_

  - [x] 3.2 Write property test for credential encryption round-trip
    - **Property 1: Credential Encryption Round-Trip**
    - **Validates: Requirements 2.6, 17.1**
    - Generate random credentials and verify encrypt/decrypt returns original value
    - Test with all auth_types (oauth, meta, api_key)

  - [x] 3.3 Create WebhookVerifier utility class
    - Implement verify_meta_signature() for Meta webhook signature verification
    - Use HMAC SHA256 for signature computation
    - Use constant-time comparison to prevent timing attacks
    - _Requirements: 10.2, 17.6_

  - [ ]* 3.4 Write property test for webhook signature verification
    - **Property 6: Webhook Signature Verification**
    - **Validates: Requirements 10.2**
    - Generate random payloads and compute signatures
    - Verify correct signatures pass and tampered signatures fail

  - [ ]* 3.5 Write property test for encryption key separation
    - **Property 14: Encryption Key Separation**
    - **Validates: Requirements 17.4**
    - Verify different auth_types use different encryption keys
    - Ensure credentials encrypted with one key cannot be decrypted with another

- [x] 4. Implement authentication strategy layer
  - [x] 4.1 Create BaseAuthStrategy abstract class
    - Define abstract methods: get_authorization_url, complete_authentication, refresh_credentials, revoke_credentials
    - Implement validate_config() and get_required_fields() methods
    - Add _validate_config() called in __init__ to enforce validation
    - Define AuthorizationResult and AuthenticationResult dataclasses
    - _Requirements: 4.1-4.6_

  - [ ]* 4.2 Write property test for strategy instantiation validation
    - **Property 3: Strategy Instantiation Validation**
    - **Validates: Requirements 4.4**
    - Generate auth_configs with missing required fields
    - Verify ValidationError is raised with descriptive messages

  - [x] 4.3 Implement OAuthStrategy class
    - Implement get_authorization_url() with PKCE support
    - Implement complete_authentication() to exchange code for tokens
    - Implement refresh_credentials() using refresh_token
    - Implement revoke_credentials() to revoke OAuth tokens
    - Validate HTTPS URLs in authorization_url and token_url
    - _Requirements: 5.1-5.7_

  - [ ]* 4.4 Write property test for OAuth HTTPS enforcement
    - **Property 4: OAuth HTTPS Enforcement**
    - **Validates: Requirements 5.6**
    - Generate OAuth configs with non-HTTPS URLs
    - Verify validation fails with appropriate error message

  - [x] 4.5 Implement MetaAuthStrategy class
    - Implement get_authorization_url() for Meta Business verification
    - Implement complete_authentication() to exchange code for 60-day token
    - Implement _fetch_business_details() to retrieve waba_id, phone_number_id, business_id
    - Implement refresh_credentials() for token refresh before 60-day expiry
    - Implement revoke_credentials() to revoke Meta tokens
    - _Requirements: 6.1-6.7_

  - [x] 4.6 Implement APIKeyStrategy class
    - Implement get_authorization_url() returning None (no redirect)
    - Implement complete_authentication() to validate API key with test request
    - Implement _validate_api_key() making test request to api_endpoint
    - Implement refresh_credentials() as no-op (API keys don't expire)
    - Implement revoke_credentials() as no-op (manual revocation)
    - _Requirements: 7.1-7.7_

  - [x] 4.7 Implement AuthStrategyFactory class
    - Create registry mapping auth_types to strategy classes
    - Implement create_strategy() method with validation
    - Implement register_strategy() for dynamic extension
    - Raise ValidationError for unrecognized auth_types
    - _Requirements: 8.1-8.7_

  - [ ]* 4.8 Write property test for unrecognized auth type factory error
    - **Property 5: Unrecognized Auth Type Factory Error**
    - **Validates: Requirements 8.5**
    - Generate random invalid auth_type values
    - Verify ValidationError is raised with list of supported types


- [x] 5. Implement rate limiting layer
  - [x] 5.1 Create RateLimiter class with Redis sliding window
    - Implement check_rate_limit() with per-integration and global limits
    - Implement _check_sliding_window() using Redis sorted sets
    - Implement _record_request() to track requests in window
    - Implement get_rate_limit_status() returning current usage
    - Use Redis ZREMRANGEBYSCORE to remove old entries
    - _Requirements: 12.1-12.7_

  - [ ]* 5.2 Write property test for rate limit message preservation
    - **Property 7: Rate Limit Message Preservation**
    - **Validates: Requirements 12.4**
    - Generate messages exceeding rate limit
    - Verify messages are queued (status='pending') not dropped
    - Verify messages eventually sent when quota available

  - [ ]* 5.3 Write unit tests for rate limiter
    - Test sliding window algorithm with time-based scenarios
    - Test per-integration limit enforcement
    - Test global limit enforcement
    - Test rate limit status reporting
    - _Requirements: 12.1-12.7, 34.1_

- [x] 6. Implement retry system with exponential backoff
  - [x] 6.1 Create RetryableTask base class extending Celery Task
    - Configure autoretry_for with transient exceptions
    - Set retry_kwargs with max_retries=5 and exponential backoff
    - Implement should_retry() to classify errors as transient or permanent
    - Implement on_retry() to log retry attempts
    - _Requirements: 13.1-13.7_

  - [ ]* 6.2 Write property test for transient error retry
    - **Property 8: Transient Error Retry**
    - **Validates: Requirements 13.5**
    - Simulate transient errors (timeout, network, 429, 5xx)
    - Verify retry system attempts resend with exponential backoff
    - Verify retry count increments correctly

  - [ ]* 6.3 Write property test for permanent error no retry
    - **Property 9: Permanent Error No Retry**
    - **Validates: Requirements 13.6**
    - Simulate permanent errors (401, 403, 400)
    - Verify message marked as failed without retry attempts
    - Verify retry count remains at 0

- [x] 7. Implement Celery tasks for message processing
  - [x] 7.1 Create process_incoming_message Celery task
    - Parse webhook payload to extract message data
    - Create or get Conversation record
    - Create Message record with status='received'
    - Update conversation last_message_at timestamp
    - Mark WebhookEvent as processed
    - Trigger AI response if needed
    - _Requirements: 11.2, 16.1-16.3_

  - [x] 7.2 Create send_outgoing_message Celery task
    - Check rate limit before sending
    - Call MessageDeliveryService to send message
    - Update message status to 'sent' on success
    - Increment retry_count on failure
    - Mark as 'failed' after max retries
    - Use RetryableTask base class for automatic retry
    - _Requirements: 11.3, 16.6, 21.5_

  - [x] 7.3 Create trigger_ai_response Celery task
    - Fetch conversation history (last 10 messages)
    - Call TwinResponseService to generate AI response
    - Create outgoing Message with status='pending'
    - Enqueue send_outgoing_message task
    - _Requirements: 16.4_

  - [x] 7.4 Create refresh_expiring_tokens background task
    - Query integrations with tokens expiring within 24 hours
    - Use IntegrationRefreshService to refresh each integration
    - Log success and failures
    - _Requirements: 5.3, 6.5_

  - [ ]* 7.5 Write integration tests for message processing pipeline
    - Test webhook → process → AI trigger → send flow
    - Test rate limiting during message sending
    - Test retry behavior on failures
    - Mock external API calls
    - _Requirements: 16.1-16.7, 34.3_


- [x] 8. Implement installation API endpoints
  - [x] 8.1 Create InstallIntegrationView (POST /api/v1/integrations/install/)
    - Accept integration_type_id and redirect_uri parameters
    - Create InstallationSession with oauth_state
    - Use AuthStrategyFactory to create appropriate strategy
    - Return authorization_url for OAuth/Meta or requires_api_key flag
    - _Requirements: 19.1-19.7_

  - [x] 8.2 Create OAuthCallbackView (GET /api/v1/integrations/oauth/callback/)
    - Accept code and state query parameters
    - Validate InstallationSession with oauth_state
    - Use strategy.complete_authentication() to exchange code for tokens
    - Create or update Integration with encrypted tokens
    - Store Meta metadata (waba_id, phone_number_id, business_id) if applicable
    - Update InstallationSession status to 'completed'
    - _Requirements: 5.2, 9.1-9.7_

  - [x] 8.3 Create MetaCallbackView (GET /api/v1/integrations/meta/callback/)
    - Similar to OAuthCallbackView but Meta-specific
    - Fetch business account details via Meta Graph API
    - Store waba_id, phone_number_id, business_id in Integration
    - _Requirements: 9.1-9.7_

  - [x] 8.4 Create APIKeyCompleteView (POST /api/v1/integrations/api-key/complete/)
    - Accept session_id and api_key parameters
    - Use strategy.complete_authentication() to validate API key
    - Create Integration with encrypted api_key
    - Update InstallationSession status to 'completed'
    - _Requirements: 7.2, 7.4_

  - [ ]* 8.5 Write property test for expired session completion prevention
    - **Property 10: Expired Session Completion Prevention**
    - **Validates: Requirements 3.5**
    - Create InstallationSession with expires_at in the past
    - Attempt to complete installation
    - Verify error indicating session expired

  - [ ]* 8.6 Write integration tests for installation flows
    - Test complete OAuth flow from initiation to callback
    - Test complete Meta flow with business account fetching
    - Test API key installation flow
    - Mock external OAuth/Meta API calls
    - _Requirements: 34.2_

- [x] 9. Implement webhook API endpoints
  - [x] 9.1 Create MetaWebhookView (POST /api/v1/webhooks/meta/)
    - Verify webhook signature using WebhookVerifier
    - Extract waba_id from payload to find Integration
    - Create WebhookEvent record with status='pending'
    - Enqueue process_incoming_message task
    - Return HTTP 200 within 5 seconds
    - _Requirements: 10.1-10.5_

  - [x] 9.2 Add Meta webhook verification endpoint (GET /api/v1/webhooks/meta/)
    - Accept hub.mode, hub.verify_token, hub.challenge query parameters
    - Validate verify_token matches META_WEBHOOK_VERIFY_TOKEN
    - Return challenge parameter for successful verification
    - _Requirements: 10.6-10.7_

  - [ ]* 9.3 Write property test for webhook idempotency
    - **Property 13: Webhook Idempotency**
    - **Validates: Requirements 32.6**
    - Process same webhook event multiple times with same external_message_id
    - Verify only one Message record created
    - Verify idempotent processing behavior

  - [ ]* 9.4 Write unit tests for webhook signature verification
    - Test valid Meta signatures pass verification
    - Test invalid signatures fail verification
    - Test tampered payloads fail verification
    - _Requirements: 10.2, 34.1_


- [x] 10. Implement conversation and message API endpoints
  - [x] 10.1 Create ConversationListView (GET /api/v1/integrations/{id}/conversations/)
    - Verify user owns the Integration
    - Query conversations with select_related to avoid N+1
    - Order by last_message_at descending
    - Use PageNumberPagination for pagination
    - Return conversation fields: id, external_contact_name, last_message_at, unread_count
    - _Requirements: 20.1-20.7_

  - [x] 10.2 Create MessageListView (GET /api/v1/conversations/{id}/messages/)
    - Verify user owns the Integration via conversation
    - Query messages with select_related for optimization
    - Order by created_at ascending
    - Use PageNumberPagination for pagination
    - Return message fields: id, direction, content, status, created_at
    - _Requirements: 20.4-20.7_

  - [x] 10.3 Create SendMessageView (POST /api/v1/conversations/{id}/messages/)
    - Verify user owns the Integration via conversation
    - Accept content and metadata parameters
    - Check rate limit using RateLimiter
    - Create Message with status='pending'
    - Enqueue send_outgoing_message task
    - Return created Message immediately
    - _Requirements: 21.1-21.7_

  - [x] 10.4 Create IntegrationHealthView (GET /api/v1/integrations/{id}/health/)
    - Return health_status, last_successful_sync_at, recent_error_count
    - Return rate_limit_status from RateLimiter
    - _Requirements: 23.6_

  - [ ]* 10.5 Write unit tests for conversation and message endpoints
    - Test conversation listing with pagination
    - Test message listing with pagination
    - Test message sending with rate limiting
    - Test ownership verification
    - _Requirements: 20.1-20.7, 21.1-21.7, 34.1_

- [x] 11. Implement integration management endpoints
  - [x] 11.1 Create IntegrationListView (GET /api/v1/integrations/)
    - List user's integrations with select_related
    - Include integration_type details
    - Filter by status if provided
    - _Requirements: 20.1-20.3_

  - [x] 11.2 Create IntegrationDetailView (GET /api/v1/integrations/{id}/)
    - Return integration details including health status
    - Verify user ownership
    - _Requirements: 23.1-23.7_

  - [x] 11.3 Create IntegrationDeleteView (DELETE /api/v1/integrations/{id}/)
    - Verify user ownership
    - Call strategy.revoke_credentials() before deletion
    - Delete associated Conversation, Message, WebhookEvent records
    - Log uninstallation event
    - Continue deletion even if revocation fails
    - _Requirements: 28.1-28.7_

  - [ ]* 11.4 Write integration tests for integration management
    - Test listing integrations
    - Test retrieving integration details
    - Test deleting integration with cascade
    - Test credential revocation during deletion
    - _Requirements: 28.1-28.7, 34.2_

- [x] 12. Implement service layer classes
  - [x] 12.1 Create MessageDeliveryService
    - Implement send_message() for different integration types
    - Handle Meta WhatsApp API message sending
    - Handle OAuth-based platform message sending
    - Handle API key-based platform message sending
    - Return external_message_id on success
    - _Requirements: 16.6, 21.5_

  - [x] 12.2 Create IntegrationRefreshService
    - Implement refresh_integration() using appropriate strategy
    - Update Integration with new tokens and expiry
    - Handle refresh failures gracefully
    - _Requirements: 5.3, 6.5_

  - [x] 12.3 Create AuthConfigParser service
    - Implement parse() to convert JSON to typed objects
    - Implement serialize() to convert typed objects to JSON
    - Validate OAuth, Meta, and API Key configurations
    - Validate URL formats
    - _Requirements: 25.1-25.6_

  - [ ]* 12.4 Write property test for auth config round-trip
    - **Property 11: Auth Config Round-Trip**
    - **Validates: Requirements 25.7**
    - Generate valid auth_config JSON objects
    - Parse → serialize → parse and verify equivalence
    - Test with OAuth, Meta, and API Key configs


- [x] 13. Implement serializers for API validation
  - [x] 13.1 Create IntegrationTypeSerializer
    - Validate auth_type choices
    - Validate auth_config structure based on auth_type
    - Serialize for API responses
    - _Requirements: 1.1-1.7_

  - [ ]* 13.2 Write property test for invalid auth type rejection
    - **Property 2: Invalid Auth Type Rejection**
    - **Validates: Requirements 1.6**
    - Generate random strings not in {oauth, meta, api_key}
    - Attempt to create IntegrationTypeModel
    - Verify ValidationError is raised

  - [x] 13.3 Create IntegrationSerializer
    - Exclude encrypted fields from serialization
    - Include integration_type details
    - Include health_status and last_successful_sync_at
    - _Requirements: 2.1-2.7, 23.1-23.7_

  - [x] 13.4 Create InstallationSessionSerializer
    - Serialize session status and progress
    - Include error_message if failed
    - _Requirements: 3.1-3.7_

  - [x] 13.5 Create ConversationSerializer
    - Include integration details
    - Calculate unread_count
    - _Requirements: 15.1-15.2, 20.3_

  - [x] 13.6 Create MessageSerializer
    - Serialize all message fields
    - Include retry information
    - _Requirements: 15.3-15.7_

  - [ ]* 13.7 Write unit tests for serializers
    - Test validation logic for each serializer
    - Test field exclusions (encrypted fields)
    - Test nested serialization
    - _Requirements: 34.1_

- [x] 14. Implement database migrations
  - [x] 14.1 Create migration for IntegrationTypeModel
    - Add auth_type field with default='oauth'
    - Rename oauth_config to auth_config
    - Add rate_limit_config field
    - Add indexes on auth_type
    - _Requirements: 18.1-18.7_

  - [x] 14.2 Create migration for Integration model
    - Add Meta-specific fields: waba_id, phone_number_id, business_id
    - Add api_key_encrypted field
    - Add health monitoring fields: health_status, consecutive_failures
    - Add indexes on waba_id, business_id, health_status
    - _Requirements: 18.5_

  - [x] 14.3 Create migration for new models
    - Create InstallationSession table
    - Create Conversation table
    - Create Message table
    - Create WebhookEvent table
    - Add all indexes and constraints
    - _Requirements: 3.1-3.7, 15.1-15.7, 22.1-22.7_

  - [x] 14.4 Create data migration for backward compatibility
    - Set auth_type='oauth' for existing IntegrationTypeModel records
    - Preserve all existing auth_config data
    - Verify migration is reversible
    - _Requirements: 18.1-18.4_

  - [ ]* 14.5 Write property test for backward compatibility property access
    - **Property 12: Backward Compatibility Property Access**
    - **Validates: Requirements 18.6**
    - Create IntegrationTypeModel instances
    - Verify auth_config and oauth_config return same value
    - Test with various auth_config structures


- [x] 15. Configure Celery and Redis integration
  - [x] 15.1 Create celery.py configuration file
    - Configure Celery app with Django settings
    - Set up task routes for different queues (incoming_messages, outgoing_messages, high_priority)
    - Configure task time limits and retry settings
    - Enable task acknowledgment and result backend
    - _Requirements: 11.1-11.7_

  - [x] 15.2 Update Django settings for Celery
    - Add CELERY_BROKER_URL and CELERY_RESULT_BACKEND settings
    - Configure task serialization and compression
    - Set up queue-specific settings
    - _Requirements: 11.1-11.7_

  - [x] 15.3 Add Celery to pyproject.toml dependencies
    - Add celery package
    - Add redis package for broker
    - Verify compatibility with Python 3.13+
    - _Requirements: 11.1_

  - [x] 15.4 Create management command to start Celery workers
    - Create command to start worker with specific queues
    - Add logging configuration
    - Document worker startup in README
    - _Requirements: 11.1-11.7_

- [x] 16. Implement health monitoring and observability
  - [x] 16.1 Create HealthCheckView (GET /api/v1/health/)
    - Check database connectivity
    - Check Redis connectivity
    - Check Celery worker status
    - Return overall health status (healthy, degraded, unhealthy)
    - _Requirements: 31.1-31.7_

  - [x] 16.2 Implement integration health monitoring logic
    - Update consecutive_failures on operation failures
    - Mark health_status as 'degraded' after 3 failures
    - Mark health_status as 'disconnected' after 10 failures
    - Reset consecutive_failures on successful operation
    - _Requirements: 23.1-23.5_

  - [x] 16.3 Add structured logging for integration events
    - Log authentication attempts with auth_type and result
    - Log webhook events with integration_type and processing_status
    - Log message sends with integration_id, status, and duration
    - Log rate limit violations with integration_id and attempted_rate
    - Use JSON formatter for structured logs
    - _Requirements: 30.1-30.7_

  - [x] 16.4 Create Prometheus metrics collectors
    - Add auth_attempts_total counter
    - Add messages_processed_total counter
    - Add message_processing_duration histogram
    - Add rate_limit_violations_total counter
    - Add celery_queue_length gauge
    - _Requirements: 30.6_

  - [ ]* 16.5 Write unit tests for health monitoring
    - Test health check endpoint with various component states
    - Test integration health status transitions
    - Test consecutive failure tracking
    - _Requirements: 23.1-23.7, 34.1_

- [x] 17. Implement admin interface customizations
  - [x] 17.1 Create IntegrationTypeAdmin
    - Display auth_type as dropdown with readable choices
    - Show different configuration fields based on auth_type
    - Add validation for required fields per auth_type
    - Encrypt secrets automatically on save
    - _Requirements: 24.1-24.7_

  - [x] 17.2 Create IntegrationAdmin
    - Display integration status and health_status
    - Show token expiration information
    - Add action to manually refresh tokens
    - Exclude encrypted fields from display
    - _Requirements: 23.1-23.7_

  - [x] 17.3 Create WebhookEventAdmin
    - Display webhook status and processing time
    - Add action to retry failed webhooks
    - Show payload in formatted JSON
    - _Requirements: 22.1-22.7_

  - [x] 17.4 Create MessageAdmin
    - Display message direction, status, and retry count
    - Add action to retry failed messages
    - Show conversation context
    - _Requirements: 15.3-15.7_


- [x] 18. Configure environment variables and settings
  - [x] 18.1 Add encryption key settings to Django settings
    - Add OAUTH_ENCRYPTION_KEY, META_ENCRYPTION_KEY, API_KEY_ENCRYPTION_KEY
    - Add validation to ensure keys are set in production
    - Document key generation command in README
    - _Requirements: 17.3_

  - [x] 18.2 Add Meta webhook settings
    - Add META_APP_SECRET for webhook signature verification
    - Add META_WEBHOOK_VERIFY_TOKEN for webhook verification
    - _Requirements: 10.2, 10.7_

  - [x] 18.3 Add Redis configuration settings
    - Configure Redis for rate limiting
    - Configure Redis for Celery broker
    - Add connection pooling settings
    - _Requirements: 31.5_

  - [x] 18.4 Update .env.example with new variables
    - Add all encryption keys
    - Add Meta configuration
    - Add Celery configuration
    - Add Redis configuration
    - _Requirements: 17.1-17.7_

- [x] 19. Implement URL routing
  - [x] 19.1 Create apps/automation/urls.py
    - Add installation endpoints
    - Add webhook endpoints
    - Add conversation and message endpoints
    - Add integration management endpoints
    - Add health check endpoint
    - _Requirements: 9.1-9.7, 10.1-10.7, 20.1-20.7, 21.1-21.7_

  - [x] 19.2 Include automation URLs in main neurotwin/urls.py
    - Add path for /api/v1/integrations/
    - Add path for /api/v1/webhooks/
    - Add path for /api/v1/conversations/
    - _Requirements: 9.1-9.7, 10.1-10.7, 20.1-20.7_

- [x] 20. Implement error handling and user feedback
  - [x] 20.1 Create custom exception classes
    - Create AuthenticationFailedException
    - Create RateLimitExceededException
    - Create WebhookSignatureInvalidException
    - Create IntegrationNotFoundException
    - _Requirements: 29.1-29.7_

  - [x] 20.2 Create custom exception handler
    - Format error responses consistently
    - Include error_code and details fields
    - Map exceptions to appropriate HTTP status codes
    - Log all errors with context
    - _Requirements: 29.1-29.7_

  - [x] 20.3 Implement user-friendly error messages
    - OAuth authorization failure messages
    - Meta authentication failure messages with troubleshooting
    - API key validation failure messages
    - Rate limit exceeded messages with retry-after
    - Message sending failure messages with retry option
    - _Requirements: 29.1-29.7_

  - [ ]* 20.4 Write unit tests for error handling
    - Test exception handler formatting
    - Test error message generation
    - Test HTTP status code mapping
    - _Requirements: 29.1-29.7, 34.1_

- [x] 21. Checkpoint - Ensure all tests pass
  - Run all unit tests and verify passing
  - Run all property-based tests and verify passing
  - Run all integration tests and verify passing
  - Check code coverage meets 85% minimum
  - Ask the user if questions arise


- [x] 22. Implement circuit breaker pattern
  - [x] 22.1 Create CircuitBreaker class
    - Implement call() method with circuit breaker logic
    - Track failure count and last failure time
    - Implement state transitions: closed → open → half_open
    - Configure failure_threshold and timeout parameters
    - _Requirements: 32.3-32.4_

  - [x] 22.2 Integrate circuit breaker with external API calls
    - Wrap Meta API calls with circuit breaker
    - Wrap OAuth provider calls with circuit breaker
    - Wrap API key validation calls with circuit breaker
    - _Requirements: 32.3-32.4_

  - [ ]* 22.3 Write unit tests for circuit breaker
    - Test state transitions on failures
    - Test timeout and recovery to half_open
    - Test successful calls reset failure count
    - _Requirements: 32.3-32.4, 34.1_

- [x] 23. Implement background task for token refresh
  - [x] 23.1 Create scheduled Celery task for token refresh
    - Query integrations with tokens expiring within 24 hours
    - Call refresh_expiring_tokens task
    - Schedule to run every hour
    - _Requirements: 5.3, 6.5_

  - [x] 23.2 Configure Celery Beat for scheduled tasks
    - Add celery beat configuration to settings
    - Schedule refresh_expiring_tokens task
    - _Requirements: 5.3, 6.5_

  - [ ]* 23.3 Write integration tests for token refresh
    - Test automatic refresh before expiry
    - Test refresh failure handling
    - Test integration status updates on refresh
    - _Requirements: 5.3, 6.5, 34.2_

- [x] 24. Implement rate limit configuration per integration type
  - [x] 24.1 Add default rate limits to IntegrationTypeModel
    - Set default messages_per_minute=20
    - Set default requests_per_minute=100
    - Set default burst_limit=5
    - _Requirements: 26.1-26.5_

  - [x] 24.2 Update RateLimiter to use integration type config
    - Read rate_limit_config from IntegrationTypeModel
    - Fall back to defaults if not configured
    - _Requirements: 26.3_

  - [x] 24.3 Add admin interface for rate limit configuration
    - Allow editing rate_limit_config in IntegrationTypeAdmin
    - Validate rate limit values
    - _Requirements: 26.6_

  - [ ]* 24.4 Write unit tests for configurable rate limits
    - Test rate limits from integration type config
    - Test fallback to defaults
    - Test rate limit changes apply immediately
    - _Requirements: 26.1-26.7, 34.1_

- [x] 25. Implement Meta onboarding rate protection
  - [x] 25.1 Create MetaInstallationRateLimiter
    - Implement global rate limit of 5 Meta installations per minute
    - Use Redis to track installation attempts
    - Exempt admin users from rate limit
    - _Requirements: 14.1-14.7_

  - [x] 25.2 Integrate Meta rate limiter in installation endpoint
    - Check rate limit before creating InstallationSession
    - Return HTTP 429 with retry-after header if exceeded
    - Display user-friendly message
    - _Requirements: 14.3-14.4_

  - [ ]* 25.3 Write unit tests for Meta onboarding rate protection
    - Test global rate limit enforcement
    - Test admin user exemption
    - Test retry-after header calculation
    - _Requirements: 14.1-14.7, 34.1_


- [x] 26. Implement notification system for integration failures
  - [x] 26.1 Create notify_message_failure Celery task
    - Send notification to user when message fails after max retries
    - Include error details and retry option
    - _Requirements: 13.4_

  - [x] 26.2 Create notify_integration_disconnected task
    - Send notification when integration health_status becomes 'disconnected'
    - Include reconnection instructions
    - _Requirements: 23.7_

  - [x] 26.3 Integrate notifications in failure handlers
    - Call notify_message_failure from send_outgoing_message
    - Call notify_integration_disconnected from health monitoring
    - _Requirements: 13.4, 23.7_

- [x] 27. Implement GDPR compliance features
  - [x] 27.1 Create data export endpoint (GET /api/v1/integrations/export/)
    - Export all user integration data as JSON
    - Include conversations and messages
    - Include webhook events
    - _Requirements: 33.7_

  - [x] 27.2 Create data deletion endpoint (DELETE /api/v1/integrations/delete-all/)
    - Delete all user integrations
    - Delete all associated conversations, messages, webhook events
    - Revoke all credentials with providers
    - Log deletion for audit
    - _Requirements: 33.7_

  - [ ]* 27.3 Write integration tests for GDPR features
    - Test data export completeness
    - Test data deletion cascade
    - Test credential revocation during deletion
    - _Requirements: 33.7, 34.2_

- [x] 28. Implement security features
  - [x] 28.1 Add CSRF protection to state-changing endpoints
    - Verify CSRF tokens on POST, PUT, DELETE requests
    - _Requirements: 33.4_

  - [x] 28.2 Add input sanitization
    - Sanitize all user input before storage
    - Sanitize output before display
    - _Requirements: 33.3_

  - [x] 28.3 Add authentication endpoint rate limiting
    - Limit authentication attempts to prevent brute force
    - Use DRF throttling classes
    - _Requirements: 33.5_

  - [x] 28.4 Add security event logging
    - Log all authentication attempts
    - Log all webhook signature verification failures
    - Log all rate limit violations
    - Log all integration deletions
    - _Requirements: 33.6_

  - [ ]* 28.5 Write security tests
    - Test CSRF protection
    - Test input sanitization
    - Test rate limiting on auth endpoints
    - Test security event logging
    - _Requirements: 33.1-33.7, 34.1_

- [x] 29. Implement performance optimizations
  - [x] 29.1 Add database connection pooling
    - Configure max 50 database connections
    - Set connection timeout and statement timeout
    - _Requirements: 31.4_

  - [x] 29.2 Add Redis connection pooling
    - Configure max 100 Redis connections
    - Set socket timeout and retry settings
    - _Requirements: 31.5_

  - [x] 29.3 Add caching for Integration and IntegrationTypeModel
    - Cache with 5-minute TTL
    - Invalidate cache on updates
    - _Requirements: 31.6_

  - [x] 29.4 Add database indexes for frequently queried fields
    - Verify all indexes from model definitions are created
    - Add composite indexes for common query patterns
    - _Requirements: 31.7_

  - [ ]* 29.5 Write performance tests
    - Test webhook processing throughput (target: 1000 concurrent)
    - Test message processing rate (target: 10,000/minute)
    - Test database connection pooling under load
    - Test Redis connection pooling under load
    - _Requirements: 31.1-31.7, 34.7_


- [x] 30. Implement monitoring and alerting
  - [x] 30.1 Create Celery task monitoring endpoint (GET /api/v1/admin/tasks/stats/)
    - Return task statistics grouped by task name
    - Include total_tasks, successful_tasks, failed_tasks, average_duration
    - Group by time period (hour, day, week)
    - _Requirements: 27.1-27.7_

  - [x] 30.2 Configure alert rules
    - Alert on high rate limit violations (>100/hour)
    - Alert on message delivery failures (>5%)
    - Alert on token refresh failures
    - Alert on webhook processing delays (>10 seconds)
    - Alert on Celery queue backlog (>1000 messages)
    - Alert on integration health degradation
    - _Requirements: 27.1-27.7_

  - [x] 30.3 Add log retention policies
    - Configure 90-day retention for integration logs
    - Configure 30-day retention for webhook events
    - Configure 7-day retention for Celery task results
    - _Requirements: 22.6, 27.7, 30.7_

- [x] 31. Write comprehensive documentation
  - [x] 31.1 Create API documentation
    - Document all endpoints with request/response examples
    - Document authentication requirements
    - Document rate limits
    - Document error codes and responses
    - Use drf-spectacular for OpenAPI schema generation

  - [x] 31.2 Create integration guide for developers
    - Document how to add new authentication strategies
    - Document how to add new integration types
    - Document how to extend the factory pattern
    - Document testing requirements

  - [x] 31.3 Create deployment guide
    - Document environment variable setup
    - Document encryption key generation
    - Document Celery worker setup
    - Document Redis configuration
    - Document database migration process

  - [x] 31.4 Create troubleshooting guide
    - Document common errors and solutions
    - Document webhook debugging
    - Document rate limit issues
    - Document token refresh failures
    - Document Celery worker issues

  - [x] 31.5 Update README.md
    - Add overview of integration engine
    - Add setup instructions
    - Add development workflow
    - Add testing instructions

- [ ] 32. Final checkpoint - Ensure all tests pass
  - Run complete test suite with pytest
  - Verify all 14 property-based tests pass with 100 iterations
  - Verify code coverage meets 85% minimum for integration code
  - Run Django system checks (python manage.py check)
  - Run migration checks (python manage.py makemigrations --check --dry-run)
  - Verify all Celery tasks are registered
  - Test webhook endpoints with Meta sandbox
  - Test complete OAuth flow with test provider
  - Ask the user if questions arise

## Notes

- Tasks marked with `*` are optional testing tasks and can be skipped for faster MVP
- Each task references specific requirements for traceability
- Property-based tests use Hypothesis library with minimum 100 iterations
- All business logic belongs in services, not views or serializers
- All external API calls must be async or use Celery tasks
- All credentials must be encrypted at rest using Fernet
- All webhook signatures must be verified before processing
- All rate limits must be enforced before operations
- All errors must be logged with structured context
- Database queries must use select_related/prefetch_related to avoid N+1
- Celery tasks must use RetryableTask base class for automatic retry
- Integration health monitoring must track consecutive failures
- Token refresh must happen automatically before expiry
- GDPR compliance requires data export and deletion endpoints
- Security requires CSRF protection, input sanitization, and rate limiting
- Performance requires connection pooling, caching, and proper indexing

## Property-Based Test Summary

1. **Property 1**: Credential encryption round-trip (Requirements 2.6, 17.1)
2. **Property 2**: Invalid auth type rejection (Requirements 1.6)
3. **Property 3**: Strategy instantiation validation (Requirements 4.4)
4. **Property 4**: OAuth HTTPS enforcement (Requirements 5.6)
5. **Property 5**: Unrecognized auth type factory error (Requirements 8.5)
6. **Property 6**: Webhook signature verification (Requirements 10.2)
7. **Property 7**: Rate limit message preservation (Requirements 12.4)
8. **Property 8**: Transient error retry (Requirements 13.5)
9. **Property 9**: Permanent error no retry (Requirements 13.6)
10. **Property 10**: Expired session completion prevention (Requirements 3.5)
11. **Property 11**: Auth config round-trip (Requirements 25.7)
12. **Property 12**: Backward compatibility property access (Requirements 18.6)
13. **Property 13**: Webhook idempotency (Requirements 32.6)
14. **Property 14**: Encryption key separation (Requirements 17.4)

## Implementation Order Rationale

The tasks are ordered to build incrementally:

1. **Foundation (Tasks 1-3)**: Models, encryption, security primitives
2. **Authentication (Task 4)**: Strategy pattern and all auth implementations
3. **Processing (Tasks 5-7)**: Rate limiting, retry, and Celery tasks
4. **API Layer (Tasks 8-11)**: All REST endpoints for installation, webhooks, messages
5. **Services (Task 12)**: Business logic layer
6. **Validation (Task 13)**: Serializers for API validation
7. **Data Layer (Task 14)**: Migrations for database schema
8. **Infrastructure (Tasks 15-16)**: Celery, Redis, monitoring
9. **Admin (Task 17)**: Django admin customizations
10. **Configuration (Tasks 18-19)**: Settings and URL routing
11. **Error Handling (Task 20)**: Consistent error responses
12. **Advanced Features (Tasks 22-28)**: Circuit breaker, GDPR, security, performance
13. **Observability (Task 30)**: Monitoring and alerting
14. **Documentation (Task 31)**: Comprehensive guides
15. **Validation (Tasks 21, 32)**: Checkpoints to ensure quality

Each checkpoint ensures incremental validation and allows for user feedback before proceeding.
