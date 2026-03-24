# Requirements Document

## Introduction

This document defines requirements for transforming the NeuroTwin integration system from a hardcoded enum-based architecture into a dynamic, user-installable app marketplace. The system will enable administrators to add new integration types through the admin interface without code changes, while providing users with an app store experience for discovering, installing, and managing integrations and their associated automations.

## Glossary

- **Integration_Type**: A category of third-party application that can be connected to NeuroTwin (e.g., Gmail, Slack, WhatsApp)
- **App_Marketplace**: The user interface where users browse and install available Integration_Types
- **Installation**: The process of connecting an Integration_Type to a user's account, including OAuth setup and configuration
- **Automation**: A workflow that executes actions across one or more Integrations based on triggers and conditions
- **Automation_Template**: A pre-configured Automation provided with an Integration_Type that users can enable and customize
- **Admin_Panel**: The Django admin interface where administrators manage Integration_Types
- **User**: An authenticated NeuroTwin platform user with a subscription tier
- **Admin**: A platform administrator with permissions to manage Integration_Types
- **Twin**: The AI agent that can modify user Automations based on learned patterns
- **OAuth_Configuration**: The client credentials and scopes required for an Integration_Type to authenticate with external services
- **Category**: A grouping classification for Integration_Types (e.g., "Communication", "Productivity", "CRM")

## Requirements

### Requirement 1: Dynamic Integration Type Management

**User Story:** As an Admin, I want to create and manage Integration_Types through the Admin_Panel, so that new integrations can be added without code deployments.

#### Acceptance Criteria

1. THE Admin_Panel SHALL display an interface for creating Integration_Types with fields: type identifier, display name, icon, description, category, and active status
2. WHEN an Admin creates an Integration_Type, THE System SHALL validate that the type identifier is unique and follows kebab-case naming convention
3. WHEN an Admin uploads an icon for an Integration_Type, THE System SHALL accept SVG or PNG formats with maximum file size of 500KB
4. THE Admin_Panel SHALL allow Admins to edit existing Integration_Types including all metadata fields
5. WHEN an Admin sets an Integration_Type to inactive, THE System SHALL hide it from the App_Marketplace while preserving existing user installations
6. THE System SHALL store Integration_Type records with created_at and updated_at timestamp fields
7. WHEN an Admin deletes an Integration_Type, THE System SHALL prevent deletion if any User has installed that Integration_Type

### Requirement 2: OAuth Configuration Management

**User Story:** As an Admin, I want to configure OAuth settings for each Integration_Type, so that users can authenticate with external services during installation.

#### Acceptance Criteria

1. THE Admin_Panel SHALL provide fields for OAuth_Configuration including client_id, client_secret, authorization_url, token_url, and scopes
2. WHEN an Admin saves OAuth credentials, THE System SHALL encrypt the client_secret using Fernet symmetric encryption
3. THE System SHALL validate that authorization_url and token_url are valid HTTPS URLs
4. THE Admin_Panel SHALL allow Admins to specify OAuth scopes as a comma-separated list or JSON array
5. WHEN an Integration_Type requires custom OAuth parameters, THE System SHALL store them as JSON in a flexible configuration field
6. THE System SHALL support OAuth 2.0 authorization code flow for all Integration_Types

### Requirement 3: App Marketplace Discovery Interface

**User Story:** As a User, I want to browse available Integration_Types in an App_Marketplace, so that I can discover and install new integrations.

#### Acceptance Criteria

1. THE System SHALL display an App_Marketplace interface at the route `/dashboard/apps`
2. THE App_Marketplace SHALL display Integration_Types as cards showing icon, name, category, and brief description
3. WHEN a User views the App_Marketplace, THE System SHALL show only Integration_Types where is_active equals true
4. THE App_Marketplace SHALL provide category filter buttons that filter Integration_Types by Category
5. THE App_Marketplace SHALL provide a search input that filters Integration_Types by name or description using case-insensitive matching
6. WHEN a User clicks an Integration_Type card, THE System SHALL display a detailed view with full description, required permissions, and available Automation_Templates
7. THE App_Marketplace SHALL visually distinguish between installed and not-installed Integration_Types on each card
8. WHEN a User has already installed an Integration_Type, THE System SHALL display "Installed" status instead of "Install" button

### Requirement 4: Two-Phase Installation Process

**User Story:** As a User, I want to install an Integration_Type with visual feedback, so that I understand the installation progress and can complete OAuth authentication.

#### Acceptance Criteria

1. WHEN a User clicks the install button for an Integration_Type, THE System SHALL initiate a two-phase installation process
2. THE System SHALL display Phase 1 as "Downloading" with a progress bar that animates from 0% to 100% over 2-3 seconds
3. WHEN Phase 1 completes, THE System SHALL automatically transition to Phase 2 labeled "Setting Up"
4. DURING Phase 2, THE System SHALL redirect the User to the OAuth authorization page for the Integration_Type
5. WHEN the User completes OAuth authorization, THE System SHALL receive the authorization code via callback URL
6. THE System SHALL exchange the authorization code for access_token and refresh_token using the Integration_Type's OAuth_Configuration
7. THE System SHALL encrypt and store the access_token and refresh_token using TokenEncryption
8. WHEN token storage succeeds, THE System SHALL create Integration records linking the User to the Integration_Type
9. THE System SHALL display Phase 2 progress bar completing to 100% with success message
10. IF OAuth authorization fails or is cancelled, THE System SHALL display an error message and allow retry
11. WHEN installation completes successfully, THE System SHALL create default Automation_Template instances for the User

### Requirement 5: User-Specific Integration Management

**User Story:** As a User, I want to manage my installed Integration_Types independently from other users, so that I control which integrations my Twin can access.

#### Acceptance Criteria

1. THE System SHALL maintain a many-to-many relationship between Users and Integration_Types through Integration records
2. WHEN a User installs an Integration_Type, THE System SHALL create an Integration record with user_id, integration_type_id, and encrypted tokens
3. THE System SHALL allow multiple Users to install the same Integration_Type with independent OAuth tokens
4. WHEN a User uninstalls an Integration_Type, THE System SHALL delete the Integration record and associated encrypted tokens
5. WHEN a User uninstalls an Integration_Type, THE System SHALL disable all Automations that depend on that Integration_Type
6. THE System SHALL prevent uninstallation if any enabled Automation depends solely on that Integration_Type without user confirmation
7. THE System SHALL display a list of installed Integration_Types in the User's dashboard with installation date and status

### Requirement 6: Automation Template System

**User Story:** As an Admin, I want to define Automation_Templates for each Integration_Type, so that users receive pre-configured workflows upon installation.

#### Acceptance Criteria

1. THE Admin_Panel SHALL allow Admins to create Automation_Templates associated with an Integration_Type
2. THE System SHALL store Automation_Templates with fields: name, description, trigger_type, trigger_config, steps, and is_enabled_by_default
3. WHEN a User installs an Integration_Type, THE System SHALL create Workflow instances from all associated Automation_Templates
4. THE System SHALL set the is_enabled field on created Workflows based on the Automation_Template's is_enabled_by_default value
5. THE System SHALL support trigger types including: scheduled, event-driven, and manual
6. THE System SHALL store Workflow steps as JSON array containing action_type, integration_type_id, and parameters
7. THE Automation_Template SHALL support variable substitution in steps using placeholders like {{user.email}} or {{integration.user_id}}

### Requirement 7: Automation Management Interface

**User Story:** As a User, I want to view and modify Automations for my installed Integration_Types, so that I can customize workflows to my needs.

#### Acceptance Criteria

1. THE System SHALL display an Automation management interface at the route `/dashboard/automation`
2. THE Automation interface SHALL group Workflows by Integration_Type with expandable sections
3. WHEN a User views the Automation interface, THE System SHALL display all Workflows with name, description, status, and last execution time
4. THE System SHALL provide toggle switches to enable or disable individual Workflows
5. WHEN a User clicks edit on a Workflow, THE System SHALL display a form to modify trigger_config and steps
6. THE System SHALL validate that all Integration_Types referenced in Workflow steps are installed by the User
7. THE System SHALL allow Users to create new custom Workflows by selecting trigger type and adding steps
8. WHEN a User creates a custom Workflow, THE System SHALL validate that at least one step is defined
9. THE System SHALL provide a delete button for custom Workflows but prevent deletion of Workflows created from Automation_Templates without confirmation

### Requirement 8: Twin Automation Modification

**User Story:** As a Twin, I want to modify User Automations based on learned patterns, so that workflows adapt to user behavior over time.

#### Acceptance Criteria

1. WHEN the Twin modifies a Workflow, THE System SHALL require permission_flag equals true in the request
2. THE System SHALL log all Twin-initiated Workflow modifications with timestamp, workflow_id, changes_made, and cognitive_blend_value
3. WHEN cognitive_blend exceeds 80%, THE System SHALL require explicit User confirmation before applying Twin-suggested Workflow modifications
4. THE System SHALL allow the Twin to modify trigger_config and steps fields of existing Workflows
5. THE System SHALL prevent the Twin from enabling Workflows that reference uninstalled Integration_Types
6. WHEN the Twin suggests a Workflow modification, THE System SHALL store the suggestion with reasoning explanation for User review
7. THE System SHALL maintain a change history for each Workflow showing all modifications with author (User or Twin) and timestamp

### Requirement 9: Migration from Hardcoded Enum

**User Story:** As a Developer, I want to migrate existing IntegrationType enum values to database records, so that the system maintains backward compatibility during transition.

#### Acceptance Criteria

1. THE System SHALL provide a data migration that creates Integration_Type records for all existing IntegrationType enum values
2. THE migration SHALL preserve the enum value as the type identifier and the display name as the name field
3. THE migration SHALL assign default categories to migrated Integration_Types based on their purpose
4. THE migration SHALL set is_active to true for all migrated Integration_Types
5. THE System SHALL update existing Integration records to reference the new Integration_Type model via foreign key
6. THE migration SHALL be reversible to allow rollback if needed
7. WHEN the migration completes, THE System SHALL continue to support existing Integration records without data loss

### Requirement 10: API Endpoints for App Marketplace

**User Story:** As a Frontend Developer, I want RESTful API endpoints for the App_Marketplace, so that I can build the user interface.

#### Acceptance Criteria

1. THE System SHALL provide a GET endpoint at `/api/v1/integrations/types/` that returns all active Integration_Types with pagination
2. THE endpoint SHALL support query parameters: category, search, and is_installed for filtering
3. THE System SHALL provide a GET endpoint at `/api/v1/integrations/types/{id}/` that returns detailed Integration_Type information including Automation_Templates
4. THE System SHALL provide a POST endpoint at `/api/v1/integrations/install/` that initiates the installation process for an Integration_Type
5. THE System SHALL provide a DELETE endpoint at `/api/v1/integrations/{id}/uninstall/` that removes a User's Integration
6. THE System SHALL provide a GET endpoint at `/api/v1/integrations/installed/` that returns the User's installed Integrations
7. THE System SHALL provide a GET endpoint at `/api/v1/automations/` that returns the User's Workflows grouped by Integration_Type
8. THE System SHALL provide a PATCH endpoint at `/api/v1/automations/{id}/` that updates a Workflow's configuration
9. THE System SHALL provide a POST endpoint at `/api/v1/automations/` that creates a new custom Workflow
10. ALL endpoints SHALL require JWT authentication and return 401 for unauthenticated requests
11. ALL endpoints SHALL use DRF serializers for validation and return appropriate HTTP status codes

### Requirement 11: Installation Progress Tracking

**User Story:** As a User, I want to see real-time progress during installation, so that I know the system is working and not frozen.

#### Acceptance Criteria

1. WHEN installation begins, THE System SHALL create an InstallationSession record with status "downloading"
2. THE System SHALL provide a WebSocket or polling endpoint that returns current installation progress percentage
3. THE System SHALL update the InstallationSession status to "oauth_setup" when Phase 2 begins
4. THE System SHALL update the InstallationSession status to "completed" when installation succeeds
5. IF installation fails, THE System SHALL update the InstallationSession status to "failed" with error_message
6. THE System SHALL automatically clean up InstallationSession records older than 24 hours
7. THE frontend SHALL poll the progress endpoint every 500ms during installation to update the progress bar

### Requirement 12: Permission and Safety Controls

**User Story:** As a User, I want granular permission controls for each Integration, so that I can limit what my Twin can do with each connected app.

#### Acceptance Criteria

1. THE System SHALL store permission settings as JSON in the Integration model's permissions field
2. THE System SHALL provide default permissions for each Integration_Type based on OAuth scopes
3. THE System SHALL allow Users to modify permission settings for installed Integrations through the UI
4. WHEN a Workflow attempts to execute an action, THE System SHALL verify the Integration has the required permission enabled
5. IF a required permission is disabled, THE System SHALL skip the Workflow step and log a permission_denied event
6. THE System SHALL display permission requirements in the Integration_Type detail view before installation
7. WHEN the Twin attempts to execute a Workflow, THE System SHALL check that permission_flag equals true in the Integration's permissions

### Requirement 13: Category Management

**User Story:** As an Admin, I want to organize Integration_Types into categories, so that users can easily find relevant integrations.

#### Acceptance Criteria

1. THE System SHALL support predefined categories: Communication, Productivity, CRM, Calendar, Documents, Video_Conferencing, and Other
2. THE Admin_Panel SHALL provide a dropdown to select a Category when creating or editing an Integration_Type
3. THE App_Marketplace SHALL display category filter buttons for all categories that have at least one active Integration_Type
4. WHEN a User clicks a category filter, THE System SHALL display only Integration_Types in that Category
5. THE System SHALL allow an Integration_Type to belong to exactly one Category
6. THE System SHALL display a category badge on each Integration_Type card in the App_Marketplace

### Requirement 14: Search and Discovery

**User Story:** As a User, I want to search for Integration_Types by name or description, so that I can quickly find specific integrations.

#### Acceptance Criteria

1. THE App_Marketplace SHALL provide a search input field at the top of the interface
2. WHEN a User types in the search input, THE System SHALL filter Integration_Types where name or description contains the search term (case-insensitive)
3. THE System SHALL debounce search input by 300ms to avoid excessive filtering
4. THE System SHALL display "No results found" message when search returns zero Integration_Types
5. THE System SHALL highlight matching text in Integration_Type cards when search is active
6. WHEN a User clears the search input, THE System SHALL display all active Integration_Types again

### Requirement 15: Error Handling and Recovery

**User Story:** As a User, I want clear error messages when installation fails, so that I can understand what went wrong and retry.

#### Acceptance Criteria

1. WHEN OAuth authorization fails, THE System SHALL display an error message indicating the specific failure reason
2. WHEN network errors occur during installation, THE System SHALL display "Connection failed" with a retry button
3. WHEN token exchange fails, THE System SHALL log the error details and display a user-friendly message
4. THE System SHALL provide a "Retry Installation" button that restarts the installation process from Phase 1
5. WHEN installation fails after 3 retry attempts, THE System SHALL suggest contacting support with an error reference ID
6. THE System SHALL log all installation errors with user_id, integration_type_id, error_type, and error_details for debugging
7. IF an Integration's tokens expire, THE System SHALL attempt automatic refresh using the refresh_token before marking it as disconnected

## Parser and Serializer Requirements

### Requirement 16: Automation Template Parser

**User Story:** As a Developer, I want to parse Automation_Template JSON configurations, so that Workflows can be created from templates.

#### Acceptance Criteria

1. THE System SHALL provide an Automation_Template_Parser that parses JSON template configurations into Workflow objects
2. WHEN parsing a template, THE Parser SHALL validate that all required fields (name, trigger_type, steps) are present
3. THE Parser SHALL validate that each step contains valid action_type and integration_type_id references
4. THE Parser SHALL support variable substitution by replacing placeholders with actual User and Integration data
5. THE System SHALL provide an Automation_Template_Printer that serializes Workflow objects back to JSON template format
6. FOR ALL valid Automation_Template JSON, parsing then printing then parsing SHALL produce an equivalent template structure (round-trip property)
7. WHEN parsing fails due to invalid JSON structure, THE Parser SHALL return descriptive error messages indicating the validation failure

## Non-Functional Requirements

### Requirement 17: Performance and Scalability

**User Story:** As a User, I want the App_Marketplace to load quickly, so that I can browse integrations without delays.

#### Acceptance Criteria

1. THE System SHALL load the App_Marketplace page with all Integration_Types in under 2 seconds on standard broadband connections
2. THE System SHALL use database indexing on Integration_Type fields: is_active, category, and created_at
3. THE System SHALL paginate Integration_Type listings with 20 items per page
4. THE System SHALL use select_related and prefetch_related to avoid N+1 queries when loading Workflows with Integration data
5. THE System SHALL cache Integration_Type listings for 5 minutes to reduce database load
6. WHEN a User installs an Integration_Type, THE System SHALL process OAuth token exchange asynchronously to avoid blocking the HTTP request

### Requirement 18: Security and Data Protection

**User Story:** As a User, I want my OAuth tokens stored securely, so that my connected accounts remain protected.

#### Acceptance Criteria

1. THE System SHALL encrypt all OAuth access_tokens and refresh_tokens using Fernet symmetric encryption before database storage
2. THE System SHALL store the encryption key in environment variables, never in code or database
3. THE System SHALL use HTTPS for all OAuth redirect URLs and API endpoints
4. THE System SHALL validate OAuth state parameters to prevent CSRF attacks during authorization flow
5. THE System SHALL automatically revoke tokens when a User uninstalls an Integration_Type
6. THE System SHALL log all Integration installations and uninstallations in the audit log with timestamp and user_id
7. THE System SHALL implement rate limiting on installation endpoints to prevent abuse (maximum 10 installations per User per hour)
