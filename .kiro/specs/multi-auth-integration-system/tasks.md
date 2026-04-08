# Implementation Plan: Multi-Auth Integration System

## Overview

This implementation plan refactors the NeuroTwin integration authentication system to support multiple authentication strategies (OAuth 2.0, Meta Business, API Key) through a pluggable architecture. The implementation follows the Strategy pattern with a factory for creating authentication strategies, maintains backward compatibility with existing OAuth integrations, and provides comprehensive security through encryption, rate limiting, and audit logging.

## Tasks

- [x] 1. Database schema updates and migrations
  - [x] 1.1 Create migration to add auth_type field to IntegrationTypeModel
    - Add auth_type CharField with choices (oauth, meta, api_key)
    - Set default to 'oauth' for backward compatibility
    - Add database index on auth_type field
    - _Requirements: 1.1, 1.2, 1.3_
  
  - [x] 1.2 Create migration to rename oauth_config to auth_config
    - Rename oauth_config field to auth_config in IntegrationTypeModel
    - Ensure migration is reversible for rollback capability
    - Add backward compatibility property accessor for oauth_config
    - _Requirements: 2.1, 15.1, 15.2, 15.4_
  
  - [x] 1.3 Create migration to add Meta-specific fields to Integration model
    - Add meta_business_id CharField (nullable, indexed)
    - Add meta_waba_id CharField (nullable, indexed)
    - Add meta_phone_number_id CharField (nullable)
    - Add meta_config JSONField with default dict
    - _Requirements: 10.1, 10.2, 10.3, 10.4, 10.5_
  
  - [x] 1.4 Create migration to add auth_type to InstallationSession model
    - Add auth_type CharField with default 'oauth'
    - Add index on (auth_type, status) for query performance
    - Auto-populate from integration_type in save method
    - _Requirements: 12.8_

- [x] 2. Implement core authentication strategy classes
  - [x] 2.1 Create AuthStrategy base class in apps/automation/services/auth_strategy.py
    - Define abstract methods: get_authorization_url, complete_authentication, refresh_credentials, revoke_credentials
    - Implement validate_config method with required fields checking
    - Add get_required_fields abstract method
    - Accept integration_type and auth_config in constructor
    - _Requirements: 3.1, 3.2, 3.3, 3.4, 3.5_
  
  - [x] 2.2 Implement OAuthStrategy class
    - Extend AuthStrategy base class
    - Implement get_authorization_url to build OAuth 2.0 URLs with PKCE
    - Implement complete_authentication for code-to-token exchange
    - Implement refresh_credentials using refresh_token
    - Implement revoke_credentials with provider revocation endpoint
    - Validate HTTPS URLs in validate_config
    - _Requirements: 4.1, 4.2, 4.3, 4.4, 4.5, 4.6, 4.7_
  
  - [x] 2.3 Implement MetaStrategy class
    - Extend AuthStrategy base class
    - Implement get_authorization_url for Meta Business verification flow
    - Implement complete_authentication with short-to-long-lived token exchange
    - Retrieve and store business_id, waba_id, phone_number_id
    - Implement refresh_credentials for 60-day token refresh
    - Implement revoke_credentials for Meta token revocation
    - _Requirements: 5.1, 5.2, 5.3, 5.4, 5.5, 5.6, 5.7, 5.8_
  
  - [x] 2.4 Implement APIKeyStrategy class
    - Extend AuthStrategy base class
    - Return None from get_authorization_url (no redirect needed)
    - Implement complete_authentication with API key validation
    - Make test request to api_endpoint to validate key
    - Implement refresh_credentials as no-op (keys don't expire)
    - Implement revoke_credentials as no-op (manual revocation)
    - _Requirements: 6.1, 6.2, 6.3, 6.4, 6.5, 6.6, 6.7, 6.8, 6.9_

- [x] 3. Implement factory and service layer
  - [x] 3.1 Create AuthStrategyFactory in apps/automation/services/auth_strategy_factory.py
    - Implement create_strategy method with strategy registry
    - Register OAuth, Meta, and API Key strategies
    - Raise ValidationError for unrecognized auth_type
    - Implement register_strategy for extensibility
    - _Requirements: 7.1, 7.2, 7.3, 7.4, 7.5, 7.6, 7.7, 19.3_
  
  - [x] 3.2 Refactor InstallationService to use AuthStrategyFactory
    - Update start_installation to use factory.create_strategy
    - Rename get_oauth_authorization_url to get_authorization_url
    - Handle None return from get_authorization_url for API key flow
    - Rename complete_oauth_flow to complete_authentication_flow
    - Update uninstall_integration to call strategy.revoke_credentials
    - Store auth-type-specific data (Meta fields) in Integration model
    - _Requirements: 8.1, 8.2, 8.3, 8.4, 8.5, 8.6, 8.7, 8.8_

- [x] 4. Implement HTTP client and utilities
  - [x] 4.1 Create AuthClient in apps/automation/services/auth_client.py
    - Rename from OAuthClient to AuthClient
    - Implement exchange_oauth_code with retry logic
    - Implement refresh_oauth_token with exponential backoff
    - Implement revoke_oauth_token
    - Implement exchange_meta_code for Meta short-lived tokens
    - Implement exchange_meta_long_lived_token
    - Implement get_meta_business_details
    - Implement revoke_meta_token
    - Implement validate_api_key with test request
    - Add HTTPS URL validation for all endpoints
    - Log all requests with sanitized parameters (no secrets)
    - _Requirements: 11.1, 11.2, 11.3, 11.4, 11.5, 11.6, 11.7, 11.8_
  
  - [x] 4.2 Create TokenEncryption utility in apps/automation/utils/encryption.py
    - Implement encrypt method using Fernet symmetric encryption
    - Implement decrypt method
    - Use separate encryption keys for oauth, meta, api_key from environment
    - Store keys in environment variables (OAUTH_ENCRYPTION_KEY, META_ENCRYPTION_KEY, API_KEY_ENCRYPTION_KEY)
    - _Requirements: 2.7, 16.1, 16.2, 16.3_
  
  - [x] 4.3 Create AuthConfigParser in apps/automation/services/auth_config_parser.py
    - Define dataclasses: OAuthConfig, MetaConfig, APIKeyConfig
    - Implement parse_oauth_config with field validation
    - Implement parse_meta_config with field validation
    - Implement parse_api_key_config with field validation
    - Validate URL formats for all URL fields
    - Return descriptive error messages for invalid configurations
    - _Requirements: 21.1, 21.2, 21.3, 21.4, 21.5, 21.8_
  
  - [x] 4.4 Create AuthConfigSerializer in apps/automation/services/auth_config_serializer.py
    - Implement serialize_oauth_config to convert dataclass to dict
    - Implement serialize_meta_config to convert dataclass to dict
    - Implement serialize_api_key_config to convert dataclass to dict
    - Ensure round-trip property: parse -> serialize -> parse produces equivalent config
    - _Requirements: 21.6, 21.7_

- [x] 5. Update data models
  - [x] 5.1 Update IntegrationTypeModel in apps/automation/models.py
    - Add AuthType choices enum (oauth, meta, api_key)
    - Add auth_type field with choices and default 'oauth'
    - Rename oauth_config to auth_config (via migration)
    - Update clean method to validate auth_config based on auth_type
    - Add get_required_auth_fields method
    - Add backward compatibility property for oauth_config
    - _Requirements: 1.1, 1.2, 1.3, 1.4, 1.5, 2.1, 2.2, 2.6, 15.5_
  
  - [x] 5.2 Update Integration model in apps/automation/models.py
    - Add meta_business_id, meta_waba_id, meta_phone_number_id fields
    - Add meta_config JSONField
    - Update clean method to require meta_business_id for Meta integrations
    - Add get_meta_phone_numbers method
    - Update oauth_token and refresh_token properties to use TokenEncryption
    - _Requirements: 10.1, 10.2, 10.3, 10.4, 10.6, 10.7_
  
  - [x] 5.3 Update InstallationSession model in apps/automation/models.py
    - Add auth_type field with default 'oauth'
    - Update save method to auto-populate auth_type from integration_type
    - _Requirements: 12.8_

- [x] 6. Implement API endpoints
  - [x] 6.1 Update POST /api/v1/integrations/install/ endpoint
    - Return different response structure based on auth_type
    - Include authorization_url for OAuth/Meta (requires_redirect: true)
    - Include requires_api_key: true for API key flow
    - Include auth_type in response
    - _Requirements: 12.1, 12.2, 12.3_
  
  - [x] 6.2 Create GET /api/v1/integrations/meta/callback/ endpoint
    - Accept query parameters: code, state, session_id
    - Validate state parameter against InstallationSession.oauth_state
    - Use MetaStrategy to complete authentication
    - Create Integration record with Meta-specific fields
    - Redirect to dashboard with success/error message
    - _Requirements: 9.1, 9.2, 9.3, 9.4, 9.5, 9.6, 9.7, 9.8_
  
  - [x] 6.3 Create POST /api/v1/integrations/api-key/complete/ endpoint
    - Accept session_id and api_key in request body
    - Validate session and call APIKeyStrategy.complete_authentication
    - Create Integration record with encrypted API key
    - Return success response with integration_id
    - _Requirements: 12.4, 12.5, 12.6_
  
  - [x] 6.4 Update GET /api/v1/integrations/types/{id}/ endpoint
    - Include auth_type in response
    - Include required_fields based on auth_type
    - _Requirements: 12.7_

- [x] 7. Implement webhook infrastructure
  - [x] 7.1 Create POST /api/v1/webhooks/meta/ endpoint
    - Verify Meta webhook signature using HMAC-SHA256
    - Accept webhook events: messages, message_status, account_updates
    - Route events to appropriate handlers
    - Return HTTP 200 within 20 seconds
    - Log all webhook events with timestamp and event_type
    - _Requirements: 14.1, 14.2, 14.3, 14.4, 14.5, 14.8_
  
  - [x] 7.2 Create GET /api/v1/webhooks/meta/ endpoint for verification
    - Validate verify_token parameter
    - Return challenge parameter for Meta verification
    - _Requirements: 14.6, 14.7_
  
  - [x] 7.3 Create MetaWebhookVerifier utility
    - Implement verify_signature method using HMAC-SHA256
    - Use constant-time comparison for security
    - _Requirements: 14.2, 16.8_

- [x] 8. Implement security and monitoring
  - [x] 8.1 Create AuthRateLimitMiddleware in apps/automation/middleware.py
    - Implement rate limiting for authentication endpoints
    - Limit to 10 attempts per hour per user
    - Use Django cache for tracking attempts
    - Return HTTP 429 when limit exceeded
    - _Requirements: 16.5_
  
  - [x] 8.2 Create AuthenticationAuditLog model
    - Track all authentication attempts with user, integration_type, auth_type
    - Store action (install_start, install_complete, install_failed, token_refresh, token_revoke)
    - Store success/failure status with error codes
    - Store duration_ms for performance tracking
    - Store IP address and user agent for security
    - Add indexes for efficient querying
    - _Requirements: 16.6, 23.1_
  
  - [x] 8.3 Create AuthenticationMetrics service
    - Implement log_authentication_attempt method
    - Implement get_success_rate_by_auth_type
    - Implement get_average_duration_by_auth_type
    - Implement check_failure_rate_alert (threshold: 10%)
    - _Requirements: 23.2, 23.3, 23.4, 23.5, 23.6_
  
  - [x] 8.4 Create AuthErrorHandler in apps/automation/services/error_handler.py
    - Implement handle_oauth_error with user-friendly messages
    - Implement handle_meta_error with troubleshooting steps
    - Implement handle_api_key_error with retry instructions
    - Update InstallationSession status on errors
    - Provide retry capability for recoverable errors
    - _Requirements: 17.1, 17.2, 17.3, 17.4, 17.5, 17.6_
  
  - [x] 8.5 Implement automatic token refresh for Meta integrations
    - Create background task to check token expiration
    - Attempt refresh before marking integration as disconnected
    - _Requirements: 17.7_

- [x] 9. Update admin interface
  - [x] 9.1 Update IntegrationTypeModel admin in apps/automation/admin.py
    - Display auth_type as dropdown with labels (OAuth 2.0, Meta Business, API Key)
    - Show different configuration fields based on selected auth_type
    - For OAuth: show client_id, client_secret, authorization_url, token_url, scopes
    - For Meta: show app_id, app_secret, config_id, business_verification_url
    - For API Key: show api_endpoint, authentication_header_name, api_key_format_hint
    - Validate required fields for selected auth_type
    - Auto-encrypt secrets on save
    - Add "Test Authentication" button
    - _Requirements: 18.1, 18.2, 18.3, 18.4, 18.5, 18.6, 18.7, 18.8_

- [x] 10. Frontend updates
  - [x] 10.1 Update installation flow component to handle different auth types
    - Check requires_redirect flag from API response
    - Redirect to authorization_url for OAuth/Meta
    - Show API key input form when requires_api_key is true
    - Display auth-type-specific instructions
    - _Requirements: 13.1, 13.2, 13.3_
  
  - [x] 10.2 Create API key input modal component
    - Accept API key input with validation
    - Show format hint from integration type
    - Submit to /api/v1/integrations/api-key/complete/
    - _Requirements: 13.7_
  
  - [x] 10.3 Create Meta callback handler route
    - Add /dashboard/apps/callback/meta route
    - Handle Meta callback parameters
    - _Requirements: 13.6_
  
  - [x] 10.4 Update integration type detail view
    - Display authentication method with user-friendly labels
    - Show different permission requirements based on auth_type
    - _Requirements: 13.4, 13.5_

- [x] 11. Performance optimizations
  - [x] 11.1 Create AuthConfigCache utility
    - Implement get_auth_config with 5-minute TTL
    - Implement set_auth_config for caching
    - Implement invalidate for cache clearing
    - _Requirements: 22.5_
  
  - [x] 11.2 Add database query optimizations
    - Use select_related('integration_type') in Integration queries
    - Verify indexes on auth_type, meta_business_id, meta_waba_id
    - Add composite index on (is_active, auth_type)
    - _Requirements: 22.4_
  
  - [x] 11.3 Ensure async operations for external API calls
    - Verify all AuthClient methods are async
    - Verify InstallationService methods use async/await
    - Process authentication requests asynchronously
    - _Requirements: 22.1, 22.2, 22.3, 22.6_

- [x] 12. Testing implementation
  - [x] 12.1 Write unit tests for AuthStrategy implementations
    - Test OAuthStrategy with mock OAuth provider
    - Test MetaStrategy with mock Meta API
    - Test APIKeyStrategy with mock API endpoint
    - Test error handling for network failures
    - Test token encryption/decryption
    - _Requirements: 20.1, 20.2, 20.3, 20.4_
  
  - [ ]* 12.2 Write property-based tests for authentication strategies
    - **Property 1: Invalid auth_type rejection**
    - **Validates: Requirements 1.4**
    - Test that any auth_type not in allowed values is rejected
  
  - [ ]* 12.3 Write property-based test for credential encryption
    - **Property 5: Credential encryption round-trip**
    - **Validates: Requirements 2.7, 16.1**
    - Test that encrypt(plaintext) then decrypt produces original plaintext
  
  - [ ]* 12.4 Write property-based test for configuration serialization
    - **Property 32: Configuration serialization round-trip**
    - **Validates: Requirements 21.7**
    - Test that parse -> serialize -> parse produces equivalent configuration
  
  - [ ]* 12.5 Write property-based test for state parameter validation
    - **Property 8: State parameter validation**
    - **Validates: Requirements 9.3**
    - Test that mismatched state parameters are always rejected
  
  - [ ]* 12.6 Write property-based test for HTTPS URL validation
    - **Property 11: HTTPS URL validation**
    - **Validates: Requirements 4.7, 11.7**
    - Test that non-HTTPS URLs are rejected for OAuth and Meta
  
  - [x] 12.7 Write integration tests for complete installation flows
    - Test OAuth flow end-to-end with mock provider
    - Test Meta flow end-to-end with mock Meta API
    - Test API key flow end-to-end with mock validation endpoint
    - _Requirements: 20.6_
  
  - [x] 12.8 Write backward compatibility tests
    - Test that existing OAuth integrations continue to work
    - Test oauth_config property accessor
    - Test migration rollback
    - _Requirements: 15.3, 15.5, 20.7_
  
  - [x] 12.9 Verify test coverage meets 90% threshold
    - Run coverage report for authentication-related code
    - Add tests for uncovered branches
    - _Requirements: 20.8_

- [x] 13. Documentation and migration guide
  - [x] 13.1 Create migration guide for existing OAuth integrations
    - Document oauth_config to auth_config rename
    - Provide examples of updating service layer code
    - Document backward compatibility features
    - _Requirements: 15.1, 15.5, 15.6_
  
  - [x] 13.2 Update API documentation
    - Document new endpoint responses with auth_type
    - Document Meta callback endpoint
    - Document API key completion endpoint
    - Provide examples for each auth type
  
  - [x] 13.3 Create developer guide for adding new auth types
    - Document strategy implementation template
    - Document factory registration process
    - Document admin configuration steps
    - Provide SAML example as reference
    - _Requirements: 19.1, 19.2, 19.4, 19.5, 19.6_

- [ ] 14. Checkpoint - Ensure all tests pass
  - Ensure all tests pass, ask the user if questions arise.

- [ ] 15. Final integration and deployment preparation
  - [ ] 15.1 Run full test suite including property-based tests
    - Execute all unit tests
    - Execute all property-based tests with 100 iterations
    - Execute all integration tests
    - Verify 90% code coverage achieved
  
  - [ ] 15.2 Perform manual testing of all three auth flows
    - Test OAuth installation with real provider (Gmail/Slack)
    - Test Meta installation with Meta Business account
    - Test API key installation with test integration
    - Test uninstallation and credential revocation
  
  - [ ] 15.3 Verify backward compatibility with production data
    - Test migration on copy of production database
    - Verify existing OAuth integrations still work
    - Verify no data loss during migration
    - _Requirements: 15.3, 15.7_
  
  - [ ] 15.4 Review security implementation
    - Verify all credentials are encrypted
    - Verify rate limiting is active
    - Verify audit logging captures all events
    - Verify webhook signature verification works
    - _Requirements: 16.1, 16.2, 16.4, 16.5, 16.6, 16.8_
  
  - [ ] 15.5 Performance testing
    - Test 100 concurrent authentication requests
    - Verify response times meet requirements (OAuth: 2s, Meta: 3s, API Key: 1s)
    - Verify caching reduces database queries
    - _Requirements: 22.1, 22.2, 22.3, 22.5, 22.7_

- [ ] 16. Final checkpoint - Ensure all tests pass
  - Ensure all tests pass, ask the user if questions arise.

## Notes

- Tasks marked with `*` are optional property-based tests that can be skipped for faster MVP
- Each task references specific requirements for traceability
- The implementation uses Python with Django framework
- All external API calls are async to avoid blocking
- Encryption keys must be configured in environment variables before deployment
- The system maintains backward compatibility with existing OAuth integrations
- Property-based tests use Hypothesis library with minimum 100 iterations
- Meta webhook signature verification is critical for security
- Rate limiting prevents authentication abuse
- Audit logging provides full traceability for compliance
