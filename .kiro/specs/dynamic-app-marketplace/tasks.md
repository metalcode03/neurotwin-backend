# Implementation Plan: Dynamic App Marketplace

## Overview

This implementation plan transforms NeuroTwin's integration system from a hardcoded enum-based architecture into a dynamic, user-installable app marketplace. The plan follows a 10-week phased approach with incremental validation and testing at each stage.

## Implementation Approach

- Backend: Python/Django with Django Rest Framework
- Frontend: TypeScript/React with Next.js
- Database: PostgreSQL with proper indexing
- Testing: pytest with hypothesis for property-based testing
- Deployment: Phased rollout with backward compatibility

## Tasks

### Phase 1: Foundation (Week 1-2)

- [x] 1. Create database models and encryption utilities
  - [x] 1.1 Create IntegrationType model in apps/automation/models.py
    - Add all fields: id, type, name, icon, description, brief_description, category, oauth_config, default_permissions, is_active, timestamps
    - Add validation for kebab-case type identifier
    - Add encryption methods for OAuth client secret
    - Add indexes for is_active, category, and created_at
    - _Requirements: 1.1-1.7, 2.1-2.6_
  
  - [x] 1.2 Create AutomationTemplate model in apps/automation/models.py
    - Add fields: id, integration_type FK, name, description, trigger_type, trigger_config, steps, is_enabled_by_default, is_active, timestamps
    - Add validation methods for step structure
    - Add method to get steps as list
    - _Requirements: 6.1-6.7_
  
  - [x] 1.3 Create InstallationSession model in apps/automation/models.py
    - Add fields: id, user FK, integration_type FK, status, progress, oauth_state, error_message, retry_count, timestamps
    - Add properties: is_complete, is_expired, can_retry
    - Add method to increment retry counter
    - _Requirements: 4.1-4.11, 11.1-11.7_
  
  - [x] 1.4 Create WorkflowChangeHistory model in apps/automation/models.py
    - Add fields: id, workflow FK, user FK, modified_by_twin, cognitive_blend_value, changes_made, reasoning, permission_flag, required_confirmation, created_at
    - Add indexes for workflow and user queries
    - _Requirements: 8.2, 8.6, 8.7_
  
  - [x] 1.5 Create TokenEncryption utility class in apps/automation/utils/encryption.py
    - Implement Fernet symmetric encryption for OAuth tokens
    - Add encrypt() and decrypt() methods
    - Load encryption key from environment variable
    - Add error handling for invalid keys
    - _Requirements: 2.2, 4.7, 18.1_


- [x] 2. Write and test database migrations
  - [x] 2.1 Create migration 0001_create_integration_type_model.py
    - Create IntegrationType table with all fields
    - Add indexes for performance
    - _Requirements: 9.1_
  
  - [x] 2.2 Create migration 0002_populate_integration_types.py
    - Migrate existing enum values (whatsapp, telegram, slack, gmail, outlook, google_calendar, google_docs, microsoft_office, zoom, google_meet, crm) to IntegrationType records
    - Assign appropriate categories to each type
    - Set is_active=true for all migrated types
    - Make migration reversible
    - _Requirements: 9.1-9.4_
  
  - [x] 2.3 Create migration 0003_add_integration_type_fk.py
    - Add integration_type_fk field to Integration model (nullable initially)
    - _Requirements: 9.5_
  
  - [x] 2.4 Create migration 0004_migrate_integration_data.py
    - Map existing Integration records to IntegrationType via foreign key
    - Preserve all existing data
    - Make migration reversible
    - _Requirements: 9.5, 9.7_
  
  - [x] 2.5 Create migration 0005_switch_to_foreign_key.py
    - Make integration_type_fk non-nullable
    - Rename integration_type_fk to integration_type
    - Remove old type CharField
    - Update unique_together constraint
    - _Requirements: 9.5_
  
  - [x] 2.6 Create migrations for new models
    - Create AutomationTemplate table
    - Create InstallationSession table
    - Create WorkflowChangeHistory table
    - Add indexes for all new tables
    - _Requirements: 6.1-6.7, 11.1-11.7, 8.2_

- [x] 3. Update Integration and Workflow models
  - [x] 3.1 Update Integration model to use IntegrationType foreign key
    - Update model definition to use FK instead of CharField
    - Update unique_together constraint
    - Update __str__ method to use integration_type.name
    - _Requirements: 5.1-5.7_
  
  - [x] 3.2 Enhance Workflow model with template tracking
    - Add automation_template FK field (nullable)
    - Add is_custom boolean field
    - Add last_modified_by_twin boolean field
    - Add twin_modification_count integer field
    - Add method to get integration types used in steps
    - _Requirements: 7.1-7.9, 8.1-8.7_

- [x] 4. Create service layer structure
  - [x] 4.1 Create apps/automation/services/ directory structure
    - Create __init__.py
    - Create integration_type.py
    - Create marketplace.py
    - Create installation.py
    - Create automation_template.py
    - Create workflow.py
    - _Requirements: All service requirements_

- [x] 5. Checkpoint - Ensure all tests pass
  - Run migrations on test database
  - Verify data integrity after migration
  - Ensure all model tests pass
  - Ask the user if questions arise

### Phase 2: Backend API (Week 3-4)

- [x] 6. Implement IntegrationTypeService
  - [x] 6.1 Implement create_integration_type method
    - Validate type identifier format (kebab-case)
    - Validate icon file size and format
    - Encrypt OAuth client secret
    - Invalidate marketplace cache
    - _Requirements: 1.1-1.7, 2.1-2.6_
  
  - [x] 6.2 Implement update_integration_type method
    - Allow updating all metadata fields
    - Re-encrypt client secret if changed
    - Invalidate relevant caches
    - _Requirements: 1.4_
  
  - [x] 6.3 Implement deactivate_integration_type method
    - Set is_active to false
    - Preserve existing user installations
    - Invalidate marketplace cache
    - _Requirements: 1.5_
  
  - [x] 6.4 Implement validate_type_identifier method
    - Check kebab-case format with regex
    - Check uniqueness in database
    - _Requirements: 1.2_
  
  - [ ]* 6.5 Write unit tests for IntegrationTypeService
    - Test validation logic
    - Test encryption/decryption
    - Test cache invalidation
    - Test error handling


- [x] 7. Implement AppMarketplaceService
  - [x] 7.1 Implement list_integration_types method
    - Filter by is_active=true
    - Support category filtering
    - Support search by name/description (case-insensitive)
    - Implement pagination (20 items per page)
    - Use caching (5 minute TTL)
    - _Requirements: 3.3-3.5, 10.1-10.2, 17.3_
  
  - [x] 7.2 Implement get_integration_type_detail method
    - Return full integration type info
    - Include automation templates
    - Include installation status for user
    - _Requirements: 3.6, 10.3_
  
  - [x] 7.3 Implement is_installed method
    - Check for Integration record with user_id and integration_type_id
    - Use caching (1 minute TTL)
    - _Requirements: 3.8, 5.1_
  
  - [x] 7.4 Implement get_categories_with_counts method
    - Return all categories with active integration counts
    - Use caching
    - _Requirements: 13.1-13.6_
  
  - [ ]* 7.5 Write unit tests for AppMarketplaceService
    - Test filtering and search logic
    - Test pagination
    - Test cache behavior
    - Test multi-user isolation

- [x] 8. Implement InstallationService
  - [x] 8.1 Implement start_installation method
    - Create InstallationSession with status="downloading"
    - Generate cryptographically random oauth_state
    - Validate user hasn't exceeded rate limit (10/hour)
    - _Requirements: 4.1-4.2, 11.1, 18.7_
  
  - [x] 8.2 Implement get_oauth_authorization_url method
    - Build OAuth URL with client_id, scopes, state, redirect_uri
    - Validate HTTPS URLs
    - Update session status to "oauth_setup"
    - _Requirements: 4.4, 2.3, 11.3_
  
  - [x] 8.3 Implement complete_oauth_flow method (async)
    - Validate oauth_state matches session
    - Exchange authorization code for tokens using httpx
    - Encrypt access_token and refresh_token
    - Create Integration record with encrypted tokens
    - Update session status to "completed"
    - Trigger template instantiation
    - _Requirements: 4.5-4.9, 18.4_
  
  - [x] 8.4 Implement get_installation_progress method
    - Return current session status and progress
    - Support polling endpoint
    - _Requirements: 11.2-11.5_
  
  - [x] 8.5 Implement uninstall_integration method
    - Check for dependent workflows
    - Require confirmation if workflows depend solely on this integration
    - Delete Integration record (cascades to encrypted tokens)
    - Disable dependent workflows
    - Revoke OAuth tokens with provider
    - Log uninstallation in audit log
    - _Requirements: 5.4-5.6, 18.5-18.6_
  
  - [ ]* 8.6 Write unit tests for InstallationService
    - Test OAuth state validation
    - Test token encryption round-trip
    - Test error handling and retry logic
    - Test rate limiting
    - Mock OAuth provider responses

- [x] 9. Implement AutomationTemplateService
  - [x] 9.1 Implement create_template method
    - Validate required fields (name, trigger_type, steps)
    - Validate step structure (action_type, integration_type_id)
    - Validate trigger_type is one of: scheduled, event_driven, manual
    - _Requirements: 6.1-6.6_
  
  - [x] 9.2 Implement instantiate_templates_for_user method
    - Get all active templates for integration type
    - Create Workflow instance for each template
    - Set is_enabled based on is_enabled_by_default
    - Set automation_template FK and is_custom=false
    - Parse and substitute template variables
    - _Requirements: 4.11, 6.3-6.4_
  
  - [x] 9.3 Implement parse_template_variables method
    - Replace {{user.email}}, {{user.id}}, etc. with actual user data
    - Replace {{integration.user_id}}, etc. with integration data
    - Support nested variable paths
    - _Requirements: 6.7_
  
  - [x] 9.4 Implement validate_template_structure method
    - Check all required fields present
    - Validate JSON structure
    - Return descriptive error messages
    - _Requirements: 16.2-16.3, 16.7_
  
  - [x] 9.5 Write unit tests for AutomationTemplateService
    - Test template validation
    - Test variable substitution
    - Test workflow instantiation
    - Test error messages


- [x] 10. Implement WorkflowService enhancements
  - [x] 10.1 Implement create_workflow method
    - Validate workflow has at least one step
    - Validate all integration_type_id references are installed by user
    - Set is_custom flag appropriately
    - _Requirements: 7.7-7.8_
  
  - [x] 10.2 Implement update_workflow method with Twin safety
    - Check permission_flag=true for Twin modifications
    - Check cognitive_blend value and require confirmation if >80%
    - Create WorkflowChangeHistory record
    - Log modification in audit log
    - Validate integration availability
    - _Requirements: 8.1-8.7_
  
  - [x] 10.3 Implement validate_workflow_integrations method
    - Check all integration_type_id in steps exist in user's installations
    - Return validation result with list of missing integrations
    - _Requirements: 7.6, 8.5_
  
  - [x] 10.4 Implement disable_workflows_for_integration method
    - Find all workflows using the integration type
    - Set is_enabled=false for each
    - Return count of disabled workflows
    - _Requirements: 5.5_
  
  - [ ]* 10.5 Write unit tests for WorkflowService
    - Test Twin permission checks
    - Test cognitive blend validation
    - Test change history creation
    - Test integration validation

- [x] 11. Create DRF serializers
  - [x] 11.1 Create IntegrationTypeSerializer in apps/automation/serializers/integration_type.py
    - Include all fields except encrypted secrets
    - Add custom validation for type identifier (kebab-case)
    - Add custom validation for icon file (size, format)
    - Add custom validation for OAuth URLs (HTTPS only)
    - _Requirements: 1.2-1.3, 2.3_
  
  - [x] 11.2 Create IntegrationSerializer in apps/automation/serializers/integration.py
    - Include user, integration_type, scopes, permissions, is_active, timestamps
    - Exclude encrypted token fields
    - Add nested integration_type data
    - _Requirements: 5.1-5.7_
  
  - [x] 11.3 Create AutomationTemplateSerializer in apps/automation/serializers/automation_template.py
    - Include all fields
    - Validate step structure
    - _Requirements: 6.1-6.7_
  
  - [x] 11.4 Create WorkflowSerializer in apps/automation/serializers/workflow.py
    - Include all fields
    - Add nested automation_template data
    - Add computed field for integration_types_used
    - _Requirements: 7.1-7.9_
  
  - [x] 11.5 Create InstallationSessionSerializer in apps/automation/serializers/installation.py
    - Include status, progress, error_message
    - Exclude oauth_state (security)
    - _Requirements: 11.1-11.7_

- [x] 12. Create API viewsets and endpoints
  - [x] 12.1 Create IntegrationTypeViewSet in apps/automation/views/marketplace.py
    - Implement list action with filtering (category, search)
    - Implement retrieve action with templates
    - Add pagination (20 items per page)
    - Require JWT authentication
    - Admin-only for create/update/delete
    - _Requirements: 10.1-10.3_
  
  - [x] 12.2 Create InstallationViewSet in apps/automation/views/installation.py
    - Implement install action (POST /api/v1/integrations/install/)
    - Implement progress action (GET /api/v1/integrations/install/{id}/progress/)
    - Implement oauth_callback action (GET /api/v1/integrations/oauth/callback/)
    - Implement uninstall action (DELETE /api/v1/integrations/{id}/uninstall/)
    - Implement installed list action (GET /api/v1/integrations/installed/)
    - Add rate limiting (10 installs/hour)
    - _Requirements: 10.4-10.6, 18.7_
  
  - [x] 12.3 Create WorkflowViewSet in apps/automation/views/automation.py
    - Implement list action with grouping by integration type
    - Implement create action with validation
    - Implement update action (PATCH)
    - Implement delete action with confirmation for template workflows
    - Add filtering by integration_type_id and is_enabled
    - _Requirements: 10.7-10.9_
  
  - [x] 12.4 Configure URL routing in apps/automation/urls.py
    - Register all viewsets with router
    - Configure nested routes
    - _Requirements: 10.1-10.11_
  
  - [ ]* 12.5 Write API integration tests
    - Test authentication requirements (401 for unauthenticated)
    - Test authorization (403 for non-admin)
    - Test request/response serialization
    - Test filtering and pagination
    - Test error responses

- [x] 13. Configure Django admin interface
  - [x] 13.1 Create IntegrationTypeAdmin in apps/automation/admin.py
    - Add list display with type, name, category, is_active
    - Add filters for category and is_active
    - Add search by name and description
    - Add custom form for OAuth configuration
    - Show installation count
    - Prevent deletion if installations exist
    - _Requirements: 1.1-1.7_
  
  - [x] 13.2 Create AutomationTemplateAdmin in apps/automation/admin.py
    - Add list display with integration_type, name, trigger_type
    - Add filters for integration_type and is_active
    - Add inline editing for steps JSON
    - _Requirements: 6.1-6.7_
  
  - [x] 13.3 Update IntegrationAdmin to show new foreign key
    - Display integration_type.name instead of enum
    - Add filter by integration_type
    - _Requirements: 5.1-5.7_

- [ ] 14. Checkpoint - Ensure all tests pass
  - Run all unit tests and verify 90%+ coverage
  - Test API endpoints with Postman or curl
  - Verify admin interface works correctly
  - Ask the user if questions arise


### Phase 3: OAuth Integration (Week 5)

- [x] 15. Implement OAuth flow components
  - [x] 15.1 Create OAuthClient utility in apps/automation/utils/oauth_client.py
    - Implement build_authorization_url method
    - Implement exchange_code_for_tokens method (async with httpx)
    - Implement refresh_token method (async)
    - Add error handling for OAuth provider errors
    - _Requirements: 4.4-4.6, 15.7_
  
  - [x] 15.2 Implement OAuth state generation and validation
    - Generate cryptographically random state (32 bytes)
    - Store state in InstallationSession with 10-minute expiry
    - Validate state on callback to prevent CSRF
    - _Requirements: 18.4_
  
  - [x] 15.3 Implement token refresh service
    - Create TokenRefreshService in apps/automation/services/token_refresh.py
    - Implement refresh_if_expired method
    - Check token_expires_at before workflow execution
    - Attempt refresh before marking integration as disconnected
    - Log refresh attempts and failures
    - _Requirements: 15.7_
  
  - [x] 15.4 Implement OAuth callback handler
    - Validate state parameter matches session
    - Extract authorization code from query params
    - Call InstallationService.complete_oauth_flow
    - Handle success: redirect to dashboard with success message
    - Handle errors: redirect with error message and retry option
    - _Requirements: 4.5-4.10_
  
  - [ ]* 15.5 Write OAuth integration tests
    - Mock OAuth provider responses
    - Test successful authorization flow
    - Test authorization cancellation
    - Test invalid state (CSRF attempt)
    - Test token exchange failures
    - Test token refresh logic

- [x] 16. Implement error handling and recovery
  - [x] 16.1 Create InstallationRecovery utility in apps/automation/utils/recovery.py
    - Implement handle_oauth_failure method
    - Implement handle_token_exchange_failure method
    - Update session status and error messages
    - Support retry up to 3 attempts
    - Generate support reference ID after 3 failures
    - _Requirements: 15.1-15.6_
  
  - [x] 16.2 Add structured error logging
    - Log all OAuth errors with user_id, integration_type_id, error_type
    - Log installation failures with retry_count
    - Log token refresh failures
    - Use structured logging format for monitoring
    - _Requirements: 15.6_
  
  - [x] 16.3 Implement rate limiting
    - Add InstallationRateThrottle class (10/hour per user)
    - Add APIRateThrottle class (1000/hour per user)
    - Return HTTP 429 with Retry-After header
    - Log rate limit violations
    - _Requirements: 18.7_

- [x] 17. Add caching layer
  - [x] 17.1 Implement cache for integration type listings
    - Cache active integration types for 5 minutes
    - Invalidate on IntegrationType save/delete
    - Use cache key: 'marketplace:active_types'
    - _Requirements: 17.5_
  
  - [x] 17.2 Implement cache for user installations
    - Cache user's installed integration type IDs for 1 minute
    - Invalidate on Integration save/delete
    - Use cache key: 'user:{user_id}:installed_types'
    - _Requirements: 17.5_
  
  - [x] 17.3 Implement cache for OAuth configurations
    - Cache OAuth config for 10 minutes
    - Invalidate on IntegrationType save
    - Use cache key: 'oauth_config:{integration_type_id}'
    - _Requirements: 17.5_
  
  - [x] 17.4 Add cache invalidation signals
    - Create post_save signal handler for IntegrationType
    - Create post_save/post_delete signal handlers for Integration
    - Invalidate appropriate cache keys
    - _Requirements: 17.5_

- [x] 18. Test with real OAuth providers
  - [x] 18.1 Set up test OAuth apps for Gmail
    - Create OAuth app in Google Cloud Console
    - Configure redirect URI
    - Test full installation flow
    - _Requirements: 2.1-2.6, 4.1-4.11_
  
  - [x] 18.2 Set up test OAuth apps for Slack
    - Create OAuth app in Slack
    - Configure scopes and redirect URI
    - Test full installation flow
    - _Requirements: 2.1-2.6, 4.1-4.11_
  
  - [ ]* 18.3 Document OAuth setup process
    - Create documentation for adding new OAuth providers
    - Include required fields and configuration
    - Add troubleshooting guide

- [x] 19. Checkpoint - Ensure OAuth flow works end-to-end
  - Test complete installation flow with real OAuth providers
  - Verify token encryption and storage
  - Test error handling and retry logic
  - Verify rate limiting works
  - Ask the user if questions arise

### Phase 4: Frontend (Week 6-7)

- [x] 20. Create App Marketplace page and components
  - [x] 20.1 Create AppMarketplace page at neuro-frontend/src/app/dashboard/apps/page.tsx
    - Fetch integration types from API
    - Implement search with 300ms debounce
    - Implement category filtering
    - Display integration types in grid layout
    - Show loading states
    - Handle errors gracefully
    - _Requirements: 3.1-3.8_
  
  - [x] 20.2 Create AppCard component in neuro-frontend/src/components/marketplace/AppCard.tsx
    - Display icon, name, category badge, brief description
    - Show "Install" button or "Installed" badge
    - Handle click to view details
    - Use GlassPanel styling for consistency
    - _Requirements: 3.7-3.8_
  
  - [x] 20.3 Create AppDetailModal component in neuro-frontend/src/components/marketplace/AppDetailModal.tsx
    - Display full description
    - Show required permissions
    - List automation templates
    - Show install button or installed status
    - Handle modal open/close
    - _Requirements: 3.6_
  
  - [x] 20.4 Create search and filter UI
    - Add search input with debounce
    - Add category filter buttons
    - Highlight active filters
    - Show result count
    - Display "No results found" message
    - _Requirements: 3.4-3.5, 14.1-14.5_


- [x] 21. Create installation flow components
  - [x] 21.1 Create InstallationProgress component in neuro-frontend/src/components/marketplace/InstallationProgress.tsx
    - Display two-phase progress (Downloading → Setting Up)
    - Show animated progress bar
    - Poll progress endpoint every 500ms
    - Handle OAuth redirect in Phase 2
    - Display success/error messages
    - Support retry on failure
    - _Requirements: 4.1-4.11, 11.1-11.7_
  
  - [x] 21.2 Implement installation API calls in neuro-frontend/src/lib/api/marketplace.ts
    - Create installIntegration function
    - Create getInstallationProgress function
    - Create uninstallIntegration function
    - Add error handling and retry logic
    - _Requirements: 10.4-10.6_
  
  - [x] 21.3 Handle OAuth callback in frontend
    - Create callback page to handle OAuth redirect
    - Extract session_id from state
    - Continue polling installation progress
    - Redirect to marketplace on completion
    - _Requirements: 4.5_

- [x] 22. Create Automation Dashboard page and components
  - [x] 22.1 Create AutomationDashboard page at neuro-frontend/src/app/dashboard/automation/page.tsx
    - Fetch workflows grouped by integration type
    - Display expandable sections per integration
    - Show workflow count per integration
    - Handle loading and error states
    - _Requirements: 7.1-7.3_
  
  - [x] 22.2 Create WorkflowList component in neuro-frontend/src/components/automation/WorkflowList.tsx
    - Display workflows for an integration type
    - Show workflow name, description, status, last execution
    - Add enable/disable toggle
    - Add edit and delete buttons
    - Distinguish custom vs template workflows
    - _Requirements: 7.3-7.5_
  
  - [x] 22.3 Create WorkflowCard component in neuro-frontend/src/components/automation/WorkflowCard.tsx
    - Display workflow details
    - Show step count
    - Show enabled/disabled status
    - Handle toggle, edit, delete actions
    - _Requirements: 7.3-7.5_
  
  - [x] 22.4 Create WorkflowEditor component in neuro-frontend/src/components/automation/WorkflowEditor.tsx
    - Edit workflow name and description
    - Configure trigger settings
    - Add/remove/reorder steps
    - Validate integration availability
    - Save/cancel actions
    - Show validation errors
    - _Requirements: 7.6-7.8_
  
  - [x] 22.5 Implement automation API calls in neuro-frontend/src/lib/api/automation.ts
    - Create getWorkflows function
    - Create createWorkflow function
    - Create updateWorkflow function
    - Create deleteWorkflow function
    - Add error handling
    - _Requirements: 10.7-10.9_

- [x] 23. Add TypeScript types and interfaces
  - [x] 23.1 Create integration types in neuro-frontend/src/types/integration.ts
    - Define IntegrationType interface
    - Define Integration interface
    - Define InstallationSession interface
    - Define InstallationStatus enum
    - _Requirements: All frontend requirements_
  
  - [x] 23.2 Create workflow types in neuro-frontend/src/types/workflow.ts
    - Define Workflow interface
    - Define WorkflowStep interface
    - Define AutomationTemplate interface
    - Define TriggerType enum
    - _Requirements: All frontend requirements_

- [x] 24. Implement UI polish and accessibility
  - [x] 24.1 Add loading skeletons for marketplace
    - Create skeleton cards for loading state
    - Animate skeleton shimmer effect
    - _Requirements: 17.1_
  
  - [x] 24.2 Add error boundaries and error states
    - Wrap components in error boundaries
    - Display user-friendly error messages
    - Add retry buttons
    - _Requirements: 15.1-15.5_
  
  - [x] 24.3 Add accessibility features
    - Ensure keyboard navigation works
    - Add ARIA labels and roles
    - Test with screen readers
    - Ensure color contrast meets WCAG standards
    - _Requirements: General accessibility_
  
  - [x] 24.4 Write frontend component tests
    - Test AppMarketplace rendering and filtering
    - Test InstallationProgress state transitions
    - Test WorkflowEditor validation
    - Test API error handling

- [x] 25. Checkpoint - Ensure frontend works end-to-end
  - Test marketplace browsing and search
  - Test complete installation flow
  - Test automation dashboard
  - Test workflow editing
  - Verify responsive design
  - Ask the user if questions arise

### Phase 5: Twin Integration (Week 8)

- [x] 26. Implement Twin workflow modification
  - [x] 26.1 Add Twin permission checking to WorkflowService
    - Verify permission_flag=true in request
    - Reject modifications without permission
    - Log rejection attempts
    - _Requirements: 8.1, 12.7_
  
  - [x] 26.2 Implement cognitive blend validation
    - Check cognitive_blend value from user profile
    - Require explicit confirmation if blend > 80%
    - Store blend value in WorkflowChangeHistory
    - _Requirements: 8.3_
  
  - [x] 26.3 Create Twin suggestion storage
    - Store suggested modifications with reasoning
    - Create API endpoint for user to review suggestions
    - Allow user to approve/reject suggestions
    - _Requirements: 8.6_
  
  - [x] 26.4 Implement change history tracking
    - Create WorkflowChangeHistory record on every modification
    - Store before/after values in changes_made JSON
    - Store reasoning for Twin modifications
    - Track permission_flag and required_confirmation
    - _Requirements: 8.7_

- [x] 27. Add audit logging for Twin actions
  - [x] 27.1 Create AuditLog model in apps/twin/models.py
    - Add fields: timestamp, event_type, user_id, resource_type, resource_id, action, result, details
    - Add indexes for querying
    - _Requirements: 8.2, 18.6_
  
  - [x] 27.2 Implement audit logging service
    - Create log_twin_action method
    - Create log_installation method
    - Create log_uninstallation method
    - Create log_permission_denied method
    - Use structured logging format
    - _Requirements: 8.2, 18.6_
  
  - [x] 27.3 Add audit log viewing in admin
    - Create AuditLogAdmin with filters
    - Add search by user, event_type, resource
    - Display in chronological order
    - _Requirements: 8.2_


- [x] 28. Implement Twin safety controls
  - [x] 28.1 Create permission validation middleware
    - Check permission_flag for all Twin-initiated requests
    - Return 403 Forbidden if permission not granted
    - Log permission denials
    - _Requirements: 8.1, 12.7_
  
  - [x] 28.2 Implement integration permission checking
    - Verify Integration.permissions contains required permission
    - Skip workflow steps if permission disabled
    - Log permission_denied events
    - _Requirements: 12.4-12.5_
  
  - [x] 28.3 Add kill-switch functionality
    - Create endpoint to disable all Twin automations
    - Set global flag to prevent Twin actions
    - Notify user of kill-switch activation
    - _Requirements: Safety principles_
  
  - [ ]* 28.4 Write Twin safety tests
    - Test permission_flag requirement
    - Test cognitive blend validation
    - Test audit logging
    - Test kill-switch functionality

- [x] 29. Create Twin workflow modification UI
  - [x] 29.1 Create TwinSuggestions component in neuro-frontend/src/components/automation/TwinSuggestions.tsx
    - Display pending Twin suggestions
    - Show reasoning for each suggestion
    - Show before/after comparison
    - Add approve/reject buttons
    - _Requirements: 8.6_
  
  - [x] 29.2 Create ChangeHistory component in neuro-frontend/src/components/automation/ChangeHistory.tsx
    - Display workflow change history
    - Show author (User or Twin)
    - Show timestamp and changes made
    - Show cognitive blend value for Twin changes
    - _Requirements: 8.7_
  
  - [x] 29.3 Add Twin modification confirmation modal
    - Show when cognitive blend > 80%
    - Display warning about high blend
    - Require explicit user confirmation
    - _Requirements: 8.3_

- [ ] 30. Checkpoint - Ensure Twin integration works safely
  - Test Twin workflow modifications with permission
  - Test rejection without permission
  - Test cognitive blend validation
  - Verify audit logs are complete
  - Test kill-switch functionality
  - Ask the user if questions arise

### Phase 6: Testing and Quality (Week 9)

- [ ] 31. Write property-based tests
  - [ ]* 31.1 Write property test for type identifier validation
    - **Property 1: Type Identifier Validation**
    - **Validates: Requirements 1.2**
    - Use hypothesis to generate kebab-case and invalid strings
    - Verify validation accepts valid and rejects invalid
  
  - [ ]* 31.2 Write property test for icon file validation
    - **Property 2: Icon File Validation**
    - **Validates: Requirements 1.3**
    - Generate files of various sizes and formats
    - Verify size and format validation
  
  - [ ]* 31.3 Write property test for token encryption round-trip
    - **Property 6: Token Encryption Round-Trip**
    - **Validates: Requirements 2.2, 4.7, 18.1**
    - Generate random token strings
    - Verify encrypt then decrypt produces original
  
  - [ ]* 31.4 Write property test for OAuth scope parsing
    - **Property 8: OAuth Scope Format Parsing**
    - **Validates: Requirements 2.4**
    - Generate scopes as comma-separated and JSON array
    - Verify both formats parse to same list
  
  - [ ]* 31.5 Write property test for search and filter correctness
    - **Property 11: Search and Filter Correctness**
    - **Validates: Requirements 3.4, 3.5, 10.2, 13.4, 14.2**
    - Generate random search terms and categories
    - Verify results match all filter criteria
  
  - [ ]* 31.6 Write property test for installation state machine
    - **Property 13: Installation State Machine**
    - **Validates: Requirements 4.3, 11.1, 11.3, 11.4, 11.5**
    - Use hypothesis stateful testing
    - Verify valid state transitions only
    - Verify progress is 0-100 and monotonic
  
  - [ ]* 31.7 Write property test for template instantiation
    - **Property 15: Template Instantiation**
    - **Validates: Requirements 4.11, 6.3, 6.4**
    - Generate integration types with N templates
    - Verify exactly N workflows created
  
  - [ ]* 31.8 Write property test for multi-user installation independence
    - **Property 16: Multi-User Installation Independence**
    - **Validates: Requirements 5.3**
    - Generate multiple users installing same type
    - Verify independent Integration records
  
  - [ ]* 31.9 Write property test for workflow integration validation
    - **Property 22: Workflow Integration Validation**
    - **Validates: Requirements 7.6, 8.5**
    - Generate workflows with various integration references
    - Verify validation catches uninstalled integrations
  
  - [ ]* 31.10 Write property test for template parser round-trip
    - **Property 39: Template Parser Round-Trip**
    - **Validates: Requirements 16.6**
    - Generate valid template JSON
    - Verify parse → serialize → parse produces equivalent structure

- [ ] 32. Write comprehensive unit tests
  - [ ]* 32.1 Write model tests
    - Test all model field validations
    - Test model methods and properties
    - Test model constraints (unique_together, foreign keys)
    - Test encryption/decryption methods
    - Target 95% coverage
  
  - [ ]* 32.2 Write service tests
    - Test all service methods
    - Mock external dependencies
    - Test error handling
    - Test transaction rollback on failures
    - Target 90% coverage
  
  - [ ]* 32.3 Write API tests
    - Test authentication requirements
    - Test authorization checks
    - Test request/response serialization
    - Test filtering and pagination
    - Test error responses
    - Target 85% coverage
  
  - [ ]* 32.4 Write migration tests
    - Test data migration correctness
    - Test migration reversibility
    - Test data preservation
    - Test constraint enforcement
    - Target 100% coverage


- [ ] 33. Perform integration testing
  - [ ]* 33.1 Test complete installation flow
    - Test user browses marketplace
    - Test user installs integration
    - Test OAuth authorization
    - Test token storage
    - Test template instantiation
    - Verify workflows created
  
  - [ ]* 33.2 Test workflow execution with integrations
    - Test workflow triggers correctly
    - Test steps execute in order
    - Test integration permissions checked
    - Test error handling
  
  - [ ]* 33.3 Test Twin modification workflow
    - Test Twin suggests modification
    - Test user reviews and approves
    - Test change history recorded
    - Test audit log created
  
  - [ ]* 33.4 Test uninstallation cascade
    - Test uninstall with dependent workflows
    - Test confirmation required
    - Test workflows disabled
    - Test Integration deleted
    - Test tokens removed

- [ ] 34. Perform security testing
  - [ ] 34.1 Test authentication and authorization
    - Verify all endpoints require JWT
    - Verify 401 for unauthenticated requests
    - Verify 403 for unauthorized actions
    - Test admin-only endpoints
  
  - [ ] 34.2 Test OAuth security
    - Verify state parameter validation (CSRF protection)
    - Verify tokens are encrypted at rest
    - Verify tokens never exposed in responses
    - Test token refresh security
  
  - [ ] 34.3 Test input validation
    - Test SQL injection prevention
    - Test XSS prevention
    - Test file upload validation
    - Test JSON schema validation
  
  - [ ] 34.4 Test rate limiting
    - Verify installation rate limit (10/hour)
    - Verify API rate limit (1000/hour)
    - Verify 429 responses with Retry-After
  
  - [ ] 34.5 Test data isolation
    - Verify users can only access their own data
    - Test cross-user data leakage prevention
    - Verify integration tokens isolated per user

- [ ] 35. Perform performance testing
  - [ ] 35.1 Test marketplace page load time
    - Measure page load with 50+ integration types
    - Verify < 2 seconds on standard connection
    - Test with caching enabled
  
  - [ ] 35.2 Test API response times
    - Measure p50, p95, p99 for all endpoints
    - Verify < 200ms p95 response time
    - Test with database load
  
  - [ ] 35.3 Test database query performance
    - Verify no N+1 queries
    - Verify indexes are used
    - Measure query times (< 50ms p95)
  
  - [ ] 35.4 Test cache effectiveness
    - Measure cache hit rates
    - Verify > 80% hit rate for integration types
    - Test cache invalidation works correctly

- [ ] 36. Checkpoint - Ensure all tests pass
  - Run full test suite and verify coverage targets met
  - Fix any failing tests
  - Review test coverage report
  - Ask the user if questions arise

### Phase 7: Documentation and Deployment (Week 10)

- [ ] 37. Write technical documentation
  - [ ] 37.1 Document API endpoints
    - Create OpenAPI/Swagger specification
    - Document all request/response schemas
    - Include authentication requirements
    - Add example requests and responses
  
  - [ ] 37.2 Document OAuth setup process
    - Create guide for adding new OAuth providers
    - Document required OAuth configuration fields
    - Include troubleshooting section
    - Add examples for common providers
  
  - [ ] 37.3 Document database schema
    - Create ER diagram for new models
    - Document relationships and constraints
    - Document migration strategy
    - Include rollback procedures
  
  - [ ] 37.4 Document service layer architecture
    - Document service responsibilities
    - Document service dependencies
    - Include code examples
    - Document error handling patterns

- [ ] 38. Write user documentation
  - [ ] 38.1 Create marketplace user guide
    - How to browse integrations
    - How to install integrations
    - How to manage installed integrations
    - Troubleshooting common issues
  
  - [ ] 38.2 Create automation user guide
    - How to view workflows
    - How to enable/disable workflows
    - How to edit workflows
    - How to create custom workflows
  
  - [ ] 38.3 Create Twin automation guide
    - How Twin modifies workflows
    - How to review Twin suggestions
    - How to set cognitive blend
    - How to use kill-switch

- [ ] 39. Prepare deployment
  - [ ] 39.1 Update environment variables
    - Add TOKEN_ENCRYPTION_KEY to .env.example
    - Add OAUTH_CALLBACK_BASE_URL
    - Add rate limiting settings
    - Add cache TTL settings
    - Document all new environment variables
  
  - [ ] 39.2 Create deployment checklist
    - Database migration steps
    - Environment variable setup
    - Cache configuration
    - OAuth app setup
    - Monitoring setup
  
  - [ ] 39.3 Set up monitoring and alerts
    - Add metrics for installation success rate
    - Add metrics for API response times
    - Add alerts for error rates
    - Add alerts for rate limit violations
  
  - [ ] 39.4 Create rollback plan
    - Document rollback steps for each migration
    - Test rollback procedure
    - Document data recovery process

- [ ] 40. Deploy to staging
  - [ ] 40.1 Run database migrations on staging
    - Backup staging database
    - Run migrations in order
    - Verify data integrity
    - Test rollback if needed
  
  - [ ] 40.2 Deploy backend code to staging
    - Deploy new service classes
    - Deploy API endpoints
    - Verify all endpoints accessible
  
  - [ ] 40.3 Deploy frontend code to staging
    - Build and deploy frontend
    - Verify marketplace page loads
    - Verify automation dashboard loads
  
  - [ ] 40.4 Configure OAuth apps for staging
    - Set up test OAuth apps
    - Configure redirect URIs for staging
    - Test OAuth flows

- [ ] 41. Perform user acceptance testing
  - [ ] 41.1 Test marketplace functionality
    - Browse and search integrations
    - Filter by category
    - View integration details
    - Verify UI/UX is intuitive
  
  - [ ] 41.2 Test installation flow
    - Install multiple integrations
    - Test OAuth with real providers
    - Verify templates instantiated
    - Test error scenarios
  
  - [ ] 41.3 Test automation management
    - View workflows
    - Enable/disable workflows
    - Edit workflow configuration
    - Create custom workflow
    - Delete workflow
  
  - [ ] 41.4 Test Twin integration
    - Test Twin workflow modification
    - Test cognitive blend validation
    - Review change history
    - Test kill-switch
  
  - [ ] 41.5 Gather user feedback
    - Collect feedback on usability
    - Identify pain points
    - Document improvement suggestions


- [ ] 42. Deploy to production
  - [ ] 42.1 Final pre-deployment checks
    - Verify all tests pass
    - Verify security audit complete
    - Verify performance targets met
    - Verify documentation complete
    - Get stakeholder approval
  
  - [ ] 42.2 Backup production database
    - Create full database backup
    - Verify backup integrity
    - Store backup securely
    - Document restore procedure
  
  - [ ] 42.3 Run database migrations on production
    - Schedule maintenance window
    - Run migrations in order
    - Verify data integrity
    - Monitor for errors
  
  - [ ] 42.4 Deploy backend code to production
    - Deploy new service classes
    - Deploy API endpoints
    - Verify all endpoints accessible
    - Monitor error rates
  
  - [ ] 42.5 Deploy frontend code to production
    - Build and deploy frontend
    - Verify marketplace page loads
    - Verify automation dashboard loads
    - Test on multiple browsers
  
  - [ ] 42.6 Configure OAuth apps for production
    - Set up production OAuth apps
    - Configure redirect URIs for production
    - Test OAuth flows
    - Verify token encryption
  
  - [ ] 42.7 Enable monitoring and alerts
    - Verify metrics collection working
    - Verify alerts configured
    - Monitor initial traffic
    - Watch for errors

- [ ] 43. Post-deployment validation
  - [ ] 43.1 Smoke test critical paths
    - Test marketplace browsing
    - Test integration installation
    - Test workflow management
    - Test Twin modifications
  
  - [ ] 43.2 Monitor performance metrics
    - Check API response times
    - Check database query performance
    - Check cache hit rates
    - Check error rates
  
  - [ ] 43.3 Monitor user adoption
    - Track integration installations
    - Track workflow creation
    - Track error reports
    - Gather user feedback
  
  - [ ] 43.4 Address any issues
    - Triage and fix critical bugs
    - Optimize performance bottlenecks
    - Improve error messages
    - Update documentation

- [ ] 44. Final checkpoint - Feature complete
  - Verify all requirements implemented
  - Verify all tests passing
  - Verify documentation complete
  - Verify feature live in production
  - Celebrate successful launch!

## Notes

- Tasks marked with `*` are optional testing tasks and can be skipped for faster MVP delivery
- Each task references specific requirements for traceability
- Checkpoints ensure incremental validation at key milestones
- Property tests validate universal correctness properties across all inputs
- Unit tests validate specific examples and edge cases
- The implementation follows a phased approach with clear dependencies
- Backend must be complete before frontend can be fully implemented
- OAuth integration must be tested with real providers before production deployment
- Twin integration includes critical safety controls that must be thoroughly tested
- All migrations are reversible to support rollback if needed

## Success Metrics

After deployment, monitor these metrics to validate success:

- Installation success rate > 95%
- Marketplace page load < 2 seconds
- API response time < 200ms (p95)
- Zero token exposure incidents
- 100% audit trail coverage for Twin actions
- User satisfaction score > 4.0/5.0
- Integration adoption rate > 30% of active users within first month

## Dependencies

### Backend Dependencies
```bash
uv add cryptography  # For Fernet encryption
uv add hypothesis  # For property-based testing
uv add celery  # For async tasks
uv add redis  # For caching and Celery broker
uv add httpx  # For async HTTP requests
uv add django-redis  # Django cache backend
```

### Frontend Dependencies
```bash
npm install lodash  # For debounce
npm install @tanstack/react-query  # For data fetching
```

### Environment Variables
Add to `.env`:
```bash
# Token encryption
TOKEN_ENCRYPTION_KEY=your-32-byte-base64-encoded-key

# OAuth settings
OAUTH_CALLBACK_BASE_URL=https://neurotwin.com

# Rate limiting
INSTALLATION_RATE_LIMIT=10/hour
API_RATE_LIMIT=1000/hour

# Caching
CACHE_INTEGRATION_TYPES_TTL=300
CACHE_USER_INSTALLATIONS_TTL=60
CACHE_OAUTH_CONFIG_TTL=600

# Session cleanup
INSTALLATION_SESSION_CLEANUP_HOURS=24

# Redis (for caching and Celery)
REDIS_URL=redis://localhost:6379/0
```

## Risk Mitigation

### High-Risk Areas

1. **Data Migration**: Migrating from enum to foreign key requires careful testing
   - Mitigation: Reversible migrations, thorough testing, database backups

2. **OAuth Token Security**: Tokens must be encrypted and never exposed
   - Mitigation: Encryption at rest, HTTPS only, security audit, no logging of tokens

3. **Twin Safety**: Twin modifications must respect permissions and cognitive blend
   - Mitigation: Permission checks, audit logging, kill-switch, confirmation for high blend

4. **Performance**: Marketplace must load quickly with many integrations
   - Mitigation: Caching, database indexing, pagination, performance testing

5. **OAuth Provider Compatibility**: Different providers have different OAuth implementations
   - Mitigation: Flexible OAuth configuration, thorough testing with real providers, error handling

### Rollback Strategy

If critical issues arise post-deployment:

1. Disable new marketplace UI (feature flag)
2. Revert API endpoints to previous version
3. Run reverse migrations if database changes cause issues
4. Restore from backup if data corruption occurs
5. Communicate with users about temporary service disruption

## Future Enhancements

After initial launch, consider these enhancements:

- WebSocket support for real-time installation progress (instead of polling)
- Integration health monitoring and automatic token refresh
- Integration usage analytics and recommendations
- Bulk workflow operations (enable/disable multiple workflows)
- Workflow templates marketplace (user-created templates)
- Integration testing sandbox (test workflows without real execution)
- Advanced workflow editor with visual flow builder
- Integration permissions management UI
- Workflow scheduling and execution history
- Integration-specific settings and configuration
