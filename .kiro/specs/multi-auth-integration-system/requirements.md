# Requirements Document

## Introduction

This document defines requirements for refactoring the NeuroTwin integration authentication system to support multiple authentication strategies beyond OAuth 2.0. The system currently assumes all integrations use OAuth, but platforms like Meta (WhatsApp/Instagram) require different authentication flows, and some integrations use simple API keys. This refactoring enables the platform to support OAuth, Meta Business authentication, API key authentication, and future authentication methods while maintaining backward compatibility with existing OAuth integrations.

## Glossary

- **Integration_Type_Model**: The database model representing a type of integration (e.g., Gmail, WhatsApp, Slack)
- **Auth_Strategy**: An authentication method used by an integration (oauth, meta, api_key)
- **OAuth_Strategy**: Authentication strategy using OAuth 2.0 authorization code flow
- **Meta_Strategy**: Authentication strategy for Meta platforms (WhatsApp, Instagram) using Meta Business API
- **API_Key_Strategy**: Authentication strategy using simple API key credentials
- **Auth_Config**: Flexible JSON configuration storing authentication parameters specific to each Auth_Strategy
- **Auth_Client**: Generalized client interface for handling authentication flows
- **Auth_Strategy_Factory**: Factory pattern implementation that creates appropriate Auth_Strategy instances
- **Meta_Business_ID**: Unique identifier for a Meta Business account
- **Meta_Phone_Number_ID**: Unique identifier for a WhatsApp Business phone number
- **Meta_WABA_ID**: WhatsApp Business Account ID in Meta's system
- **Installation_Flow**: The process of connecting an Integration_Type to a user's account
- **Callback_Endpoint**: HTTP endpoint that receives authentication responses from external providers
- **System**: The NeuroTwin platform
- **Admin**: Platform administrator managing Integration_Type configurations
- **User**: Authenticated NeuroTwin user installing integrations

## Requirements

### Requirement 1: Add Authentication Type Field

**User Story:** As an Admin, I want to specify the authentication type for each Integration_Type, so that the system uses the correct authentication flow during installation.

#### Acceptance Criteria

1. THE Integration_Type_Model SHALL include an auth_type field with choices: oauth, meta, api_key
2. THE auth_type field SHALL be indexed for query performance
3. THE auth_type field SHALL default to oauth for backward compatibility
4. WHEN an Admin creates an Integration_Type, THE System SHALL validate that auth_type is one of the allowed values
5. THE System SHALL display the auth_type in the admin interface with clear labels: "OAuth 2.0", "Meta Business", "API Key"

### Requirement 2: Refactor Authentication Configuration

**User Story:** As an Admin, I want flexible authentication configuration storage, so that different authentication strategies can store their specific parameters.

#### Acceptance Criteria

1. THE Integration_Type_Model SHALL rename oauth_config field to auth_config
2. THE auth_config field SHALL store authentication parameters as JSON with flexible structure
3. WHEN auth_type equals oauth, THE auth_config SHALL contain: client_id, client_secret_encrypted, authorization_url, token_url, scopes
4. WHEN auth_type equals meta, THE auth_config SHALL contain: app_id, app_secret_encrypted, config_id, business_verification_url
5. WHEN auth_type equals api_key, THE auth_config SHALL contain: api_key_encrypted, api_endpoint, authentication_header_name
6. THE System SHALL validate that required fields for the specified auth_type are present in auth_config
7. THE System SHALL encrypt sensitive credentials (client_secret, app_secret, api_key) using Fernet encryption before storage

### Requirement 3: Create Authentication Strategy Base Class

**User Story:** As a Developer, I want a base authentication strategy interface, so that all authentication methods implement consistent behavior.

#### Acceptance Criteria

1. THE System SHALL provide an AuthStrategy base class with abstract methods: get_authorization_url, complete_authentication, refresh_credentials, revoke_credentials
2. THE AuthStrategy base class SHALL define a validate_config method that validates auth_config structure
3. THE AuthStrategy base class SHALL define a get_required_fields method that returns required auth_config fields
4. WHEN a concrete strategy is instantiated, THE System SHALL validate that all required configuration fields are present
5. THE AuthStrategy SHALL accept integration_type and auth_config as constructor parameters

### Requirement 4: Implement OAuth Authentication Strategy

**User Story:** As a Developer, I want an OAuth-specific authentication strategy, so that existing OAuth integrations continue to work without changes.

#### Acceptance Criteria

1. THE System SHALL provide an OAuthStrategy class that extends AuthStrategy
2. THE OAuthStrategy SHALL implement get_authorization_url to build OAuth 2.0 authorization URLs
3. THE OAuthStrategy SHALL implement complete_authentication to exchange authorization codes for access tokens
4. THE OAuthStrategy SHALL implement refresh_credentials to refresh expired OAuth tokens using refresh_token
5. THE OAuthStrategy SHALL implement revoke_credentials to revoke OAuth tokens with the provider
6. THE OAuthStrategy SHALL validate that auth_config contains: client_id, client_secret_encrypted, authorization_url, token_url, scopes
7. THE OAuthStrategy SHALL use HTTPS for all OAuth URLs and validate URL schemes

### Requirement 5: Implement Meta Authentication Strategy

**User Story:** As a Developer, I want a Meta-specific authentication strategy, so that WhatsApp and Instagram integrations can be installed using Meta Business authentication.

#### Acceptance Criteria

1. THE System SHALL provide a MetaStrategy class that extends AuthStrategy
2. THE MetaStrategy SHALL implement get_authorization_url to redirect users to Meta Business verification flow
3. THE MetaStrategy SHALL implement complete_authentication to exchange Meta authorization code for long-lived access token
4. THE MetaStrategy SHALL validate that auth_config contains: app_id, app_secret_encrypted, config_id
5. THE MetaStrategy SHALL store meta_business_id, meta_waba_id, meta_phone_number_id in Integration model
6. THE MetaStrategy SHALL implement refresh_credentials to exchange short-lived tokens for long-lived tokens (60-day expiry)
7. THE MetaStrategy SHALL implement revoke_credentials to revoke Meta access tokens
8. WHEN Meta authentication completes, THE System SHALL retrieve and store business account details including phone_number_id and waba_id

### Requirement 6: Implement API Key Authentication Strategy

**User Story:** As a Developer, I want an API key authentication strategy, so that simple API-based integrations can be added without OAuth complexity.

#### Acceptance Criteria

1. THE System SHALL provide an APIKeyStrategy class that extends AuthStrategy
2. THE APIKeyStrategy SHALL implement get_authorization_url to return None (no redirect needed)
3. THE APIKeyStrategy SHALL implement complete_authentication to validate and store encrypted API key
4. THE APIKeyStrategy SHALL validate that auth_config contains: api_endpoint, authentication_header_name
5. THE APIKeyStrategy SHALL accept api_key as a parameter during installation
6. THE APIKeyStrategy SHALL encrypt the api_key using TokenEncryption before storage
7. THE APIKeyStrategy SHALL implement refresh_credentials as a no-op (API keys don't expire)
8. THE APIKeyStrategy SHALL implement revoke_credentials as a no-op (API keys are manually revoked)
9. WHEN API key authentication is used, THE System SHALL validate the key by making a test request to api_endpoint

### Requirement 7: Create Authentication Strategy Factory

**User Story:** As a Developer, I want a factory to create authentication strategies, so that the installation flow automatically uses the correct strategy.

#### Acceptance Criteria

1. THE System SHALL provide an AuthStrategyFactory class with a create_strategy method
2. THE create_strategy method SHALL accept integration_type as a parameter
3. WHEN auth_type equals oauth, THE Factory SHALL return an OAuthStrategy instance
4. WHEN auth_type equals meta, THE Factory SHALL return a MetaStrategy instance
5. WHEN auth_type equals api_key, THE Factory SHALL return an APIKeyStrategy instance
6. WHEN auth_type is unrecognized, THE Factory SHALL raise a ValidationError with descriptive message
7. THE Factory SHALL pass integration_type.auth_config to the strategy constructor

### Requirement 8: Update Installation Service

**User Story:** As a Developer, I want the installation service to use authentication strategies, so that all authentication types are handled uniformly.

#### Acceptance Criteria

1. THE InstallationService.start_installation method SHALL use AuthStrategyFactory to create the appropriate strategy
2. THE InstallationService.get_oauth_authorization_url method SHALL be renamed to get_authorization_url
3. THE get_authorization_url method SHALL call strategy.get_authorization_url
4. WHEN strategy.get_authorization_url returns None, THE System SHALL skip the redirect phase and proceed directly to credential storage
5. THE InstallationService.complete_oauth_flow method SHALL be renamed to complete_authentication_flow
6. THE complete_authentication_flow method SHALL call strategy.complete_authentication
7. THE InstallationService SHALL store strategy-specific data in Integration model's auth_config field
8. THE InstallationService.uninstall_integration method SHALL call strategy.revoke_credentials before deletion

### Requirement 9: Add Meta Callback Endpoint

**User Story:** As a User, I want to complete Meta authentication via callback, so that WhatsApp and Instagram integrations can be installed.

#### Acceptance Criteria

1. THE System SHALL provide a GET endpoint at /api/v1/integrations/meta/callback/
2. THE endpoint SHALL accept query parameters: code, state, session_id
3. THE endpoint SHALL validate the state parameter matches the InstallationSession.oauth_state
4. THE endpoint SHALL use MetaStrategy to exchange the code for access tokens
5. THE endpoint SHALL retrieve Meta business account details including business_id, waba_id, phone_number_id
6. THE endpoint SHALL create an Integration record with encrypted tokens and Meta-specific fields
7. THE endpoint SHALL redirect to the dashboard with success message on completion
8. IF Meta authentication fails, THE endpoint SHALL redirect with error message and retry option

### Requirement 10: Extend Integration Model for Meta Fields

**User Story:** As a Developer, I want to store Meta-specific identifiers, so that WhatsApp and Instagram integrations can make API calls.

#### Acceptance Criteria

1. THE Integration model SHALL add a meta_business_id field (nullable CharField, max 255)
2. THE Integration model SHALL add a meta_waba_id field (nullable CharField, max 255)
3. THE Integration model SHALL add a meta_phone_number_id field (nullable CharField, max 255)
4. THE Integration model SHALL add a meta_config field (JSONField, default dict)
5. THE System SHALL index meta_business_id and meta_waba_id for query performance
6. WHEN auth_type equals meta, THE System SHALL require meta_business_id to be non-null
7. THE Integration model SHALL provide a get_meta_phone_numbers method that returns list of phone numbers from meta_config

### Requirement 11: Generalize OAuth Client to Auth Client

**User Story:** As a Developer, I want a generalized authentication client, so that HTTP requests for all authentication types are handled consistently.

#### Acceptance Criteria

1. THE System SHALL rename OAuthClient to AuthClient
2. THE AuthClient SHALL support OAuth 2.0 token exchange
3. THE AuthClient SHALL support Meta token exchange with Meta-specific endpoints
4. THE AuthClient SHALL support API key validation requests
5. THE AuthClient SHALL use async HTTP requests with httpx
6. THE AuthClient SHALL implement retry logic with exponential backoff for network failures
7. THE AuthClient SHALL validate HTTPS URLs for OAuth and Meta endpoints
8. THE AuthClient SHALL log all authentication requests with sanitized parameters (no secrets)

### Requirement 12: Update API Endpoints for All Auth Types

**User Story:** As a Frontend Developer, I want API endpoints that work with all authentication types, so that the UI can handle different installation flows.

#### Acceptance Criteria

1. THE POST /api/v1/integrations/install/ endpoint SHALL return different responses based on auth_type
2. WHEN auth_type equals oauth or meta, THE response SHALL include: session_id, authorization_url, requires_redirect: true
3. WHEN auth_type equals api_key, THE response SHALL include: session_id, requires_redirect: false, requires_api_key: true
4. THE System SHALL provide a POST /api/v1/integrations/api-key/complete/ endpoint for API key installation
5. THE api-key/complete endpoint SHALL accept: session_id, api_key
6. THE api-key/complete endpoint SHALL validate the API key and create the Integration record
7. THE GET /api/v1/integrations/types/{id}/ endpoint SHALL include auth_type and required_fields in the response
8. THE System SHALL update InstallationSession to track auth_type for proper progress display

### Requirement 13: Frontend Adjustments for Auth Types

**User Story:** As a User, I want appropriate installation UI for each authentication type, so that I can complete installation regardless of the auth method.

#### Acceptance Criteria

1. WHEN auth_type equals oauth or meta, THE frontend SHALL display two-phase progress and redirect to authorization_url
2. WHEN auth_type equals api_key, THE frontend SHALL display a form to enter the API key
3. THE frontend SHALL display auth_type-specific instructions during installation
4. THE frontend SHALL show different permission requirements based on auth_type
5. THE Integration_Type detail view SHALL display authentication method with user-friendly labels
6. THE frontend SHALL handle Meta callback at /dashboard/apps/callback/meta route
7. THE frontend SHALL validate API key format before submission based on integration-specific rules

### Requirement 14: Webhook Preparation for Meta

**User Story:** As a Developer, I want webhook infrastructure for Meta integrations, so that WhatsApp messages can be received.

#### Acceptance Criteria

1. THE System SHALL provide a POST endpoint at /api/v1/webhooks/meta/
2. THE endpoint SHALL verify Meta webhook signatures using app_secret
3. THE endpoint SHALL accept webhook events for: messages, message_status, account_updates
4. THE endpoint SHALL route webhook events to appropriate handlers based on event type
5. THE endpoint SHALL return HTTP 200 within 20 seconds to prevent Meta retries
6. THE System SHALL provide a GET endpoint at /api/v1/webhooks/meta/ for Meta verification challenge
7. THE verification endpoint SHALL validate verify_token and return the challenge parameter
8. THE System SHALL log all webhook events with timestamp, event_type, and business_id

### Requirement 15: Migration Plan for Backward Compatibility

**User Story:** As a Developer, I want seamless migration from oauth_config to auth_config, so that existing integrations continue to work without data loss.

#### Acceptance Criteria

1. THE System SHALL provide a data migration that renames oauth_config to auth_config in Integration_Type_Model
2. THE migration SHALL set auth_type to oauth for all existing Integration_Type records
3. THE migration SHALL preserve all existing auth_config data without modification
4. THE migration SHALL be reversible to allow rollback
5. THE System SHALL maintain backward compatibility by supporting both oauth_config and auth_config property names during transition
6. THE System SHALL update all service layer code to use auth_config instead of oauth_config
7. THE migration SHALL run successfully on production database without downtime

### Requirement 16: Security and Credential Management

**User Story:** As a Security Administrator, I want all authentication credentials encrypted, so that sensitive data is protected at rest.

#### Acceptance Criteria

1. THE System SHALL encrypt all secrets (client_secret, app_secret, api_key) using Fernet symmetric encryption
2. THE System SHALL store encryption keys in environment variables, never in code or database
3. THE System SHALL use different encryption keys for different credential types
4. THE System SHALL validate that all HTTPS URLs use TLS 1.2 or higher
5. THE System SHALL implement rate limiting on authentication endpoints (10 attempts per hour per user)
6. THE System SHALL log all authentication attempts with timestamp, user_id, integration_type_id, auth_type, and result
7. THE System SHALL automatically revoke credentials when an Integration is uninstalled
8. THE System SHALL validate Meta webhook signatures to prevent unauthorized webhook calls

### Requirement 17: Error Handling and Recovery

**User Story:** As a User, I want clear error messages when authentication fails, so that I can understand what went wrong and retry.

#### Acceptance Criteria

1. WHEN OAuth authorization fails, THE System SHALL display the specific OAuth error code and description
2. WHEN Meta authentication fails, THE System SHALL display Meta-specific error messages with troubleshooting steps
3. WHEN API key validation fails, THE System SHALL display "Invalid API key" with instructions to verify the key
4. THE System SHALL provide a retry button that restarts the installation process from Phase 1
5. WHEN authentication fails after 3 retry attempts, THE System SHALL suggest contacting support with error reference ID
6. THE System SHALL log all authentication errors with full error details for debugging
7. IF Meta tokens expire, THE System SHALL attempt automatic refresh before marking integration as disconnected

### Requirement 18: Admin Interface Updates

**User Story:** As an Admin, I want to configure authentication settings for each Integration_Type, so that new authentication methods can be added through the admin panel.

#### Acceptance Criteria

1. THE Integration_Type admin interface SHALL display auth_type as a dropdown with choices: OAuth 2.0, Meta Business, API Key
2. THE admin interface SHALL show different configuration fields based on selected auth_type
3. WHEN auth_type equals oauth, THE admin SHALL display fields: client_id, client_secret, authorization_url, token_url, scopes
4. WHEN auth_type equals meta, THE admin SHALL display fields: app_id, app_secret, config_id, business_verification_url
5. WHEN auth_type equals api_key, THE admin SHALL display fields: api_endpoint, authentication_header_name, api_key_format_hint
6. THE admin interface SHALL validate that required fields for the selected auth_type are filled
7. THE admin interface SHALL encrypt secrets automatically on save
8. THE admin interface SHALL display a "Test Authentication" button that validates the configuration

### Requirement 19: Extensibility for Future Auth Types

**User Story:** As a Developer, I want the authentication system designed for extensibility, so that new authentication methods can be added without refactoring.

#### Acceptance Criteria

1. THE AuthStrategy base class SHALL be designed to support future authentication methods (JWT, SAML, custom)
2. THE auth_type field SHALL support adding new choices without database migration
3. THE AuthStrategyFactory SHALL use a registry pattern to allow dynamic strategy registration
4. THE System SHALL provide documentation for implementing new authentication strategies
5. THE System SHALL provide a template strategy class with all required methods
6. WHEN a new auth_type is added, THE System SHALL only require: strategy implementation, factory registration, admin field configuration
7. THE auth_config JSON structure SHALL support arbitrary fields for future authentication methods

### Requirement 20: Testing and Validation

**User Story:** As a Developer, I want comprehensive tests for all authentication strategies, so that authentication flows are reliable.

#### Acceptance Criteria

1. THE System SHALL provide unit tests for each authentication strategy (OAuth, Meta, API Key)
2. THE tests SHALL mock external API calls to OAuth providers, Meta API, and API key endpoints
3. THE tests SHALL validate token encryption and decryption for all credential types
4. THE tests SHALL validate error handling for network failures, invalid credentials, and expired tokens
5. THE tests SHALL validate the factory pattern creates correct strategy instances
6. THE System SHALL provide integration tests for complete installation flows for each auth_type
7. THE tests SHALL validate backward compatibility with existing OAuth integrations
8. THE tests SHALL achieve minimum 90% code coverage for authentication-related code

## Parser and Serializer Requirements

### Requirement 21: Authentication Configuration Parser

**User Story:** As a Developer, I want to parse and validate authentication configurations, so that invalid configurations are caught before installation.

#### Acceptance Criteria

1. THE System SHALL provide an AuthConfigParser that parses auth_config JSON into typed objects
2. WHEN parsing OAuth config, THE Parser SHALL validate that all required OAuth fields are present and valid
3. WHEN parsing Meta config, THE Parser SHALL validate that all required Meta fields are present and valid
4. WHEN parsing API Key config, THE Parser SHALL validate that all required API Key fields are present and valid
5. THE Parser SHALL validate URL formats for authorization_url, token_url, api_endpoint
6. THE System SHALL provide an AuthConfigSerializer that serializes auth_config objects back to JSON
7. FOR ALL valid auth_config JSON, parsing then serializing then parsing SHALL produce an equivalent configuration (round-trip property)
8. WHEN parsing fails due to invalid structure, THE Parser SHALL return descriptive error messages indicating which fields are invalid

## Non-Functional Requirements

### Requirement 22: Performance and Scalability

**User Story:** As a User, I want authentication flows to complete quickly, so that I can start using integrations without delays.

#### Acceptance Criteria

1. THE System SHALL complete OAuth authorization code exchange within 2 seconds on standard network connections
2. THE System SHALL complete Meta token exchange within 3 seconds on standard network connections
3. THE System SHALL complete API key validation within 1 second on standard network connections
4. THE System SHALL use database indexing on auth_type field for query performance
5. THE System SHALL cache auth_config for active integrations with 5-minute TTL
6. THE System SHALL process authentication requests asynchronously to avoid blocking HTTP requests
7. THE System SHALL handle 100 concurrent authentication requests without degradation

### Requirement 23: Monitoring and Observability

**User Story:** As a Platform Administrator, I want visibility into authentication flows, so that I can troubleshoot issues and monitor success rates.

#### Acceptance Criteria

1. THE System SHALL log all authentication attempts with: timestamp, user_id, integration_type_id, auth_type, duration, result
2. THE System SHALL track authentication success rate by auth_type
3. THE System SHALL alert when authentication failure rate exceeds 10% for any auth_type
4. THE System SHALL provide metrics for: total authentications, authentications by type, average duration, failure reasons
5. THE System SHALL log all credential refresh attempts with success/failure status
6. THE System SHALL provide a dashboard showing authentication health by integration type
7. THE System SHALL retain authentication logs for 90 days for audit purposes

