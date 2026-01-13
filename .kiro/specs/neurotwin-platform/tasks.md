# Implementation Plan: NeuroTwin Platform

## Overview

This implementation plan breaks down the NeuroTwin platform into incremental coding tasks. Each task builds on previous work, ensuring no orphaned code. The plan follows Django 6.0+ with Django Rest Framework, using Hypothesis for property-based testing.

## Tasks

- [x] 1. Project setup and core infrastructure
  - [x] 1.1 Initialize Django project structure with apps directory
    - Create `neurotwin/` Django project
    - Create `apps/` directory for Django applications
    - Create `core/` directory for shared utilities
    - Configure `settings.py` with environment variables from `.env`
    - _Requirements: 14.1_

  - [x] 1.2 Set up database configuration
    - Configure PostgreSQL connection in settings
    - Set up database migrations infrastructure
    - _Requirements: 14.1, 14.3_

  - [x] 1.3 Set up testing infrastructure
    - Install pytest-django and hypothesis
    - Configure pytest settings
    - Create test directory structure
    - _Requirements: Testing Strategy_

- [x] 2. Authentication app implementation
  - [x] 2.1 Create auth app and user model
    - Create `apps/auth/` Django app
    - Define custom User model with email, password_hash, oauth fields
    - Define Session model for JWT tokens
    - Create database migrations
    - _Requirements: 1.1, 1.2, 1.3_

  - [x] 2.2 Implement AuthService registration and verification
    - Implement `register()` method with email validation
    - Implement verification email sending (queue for async)
    - Implement `verify_email()` method
    - _Requirements: 1.1, 1.2_

  - [x] 2.3 Implement AuthService login and token management
    - Implement `login()` method with credential validation
    - Implement JWT token generation and validation
    - Implement `validate_token()` method
    - _Requirements: 1.3, 1.4, 1.6_

  - [x] 2.4 Implement password reset flow
    - Implement `request_password_reset()` with 24-hour token
    - Implement `reset_password()` method
    - _Requirements: 1.7_

  - [x] 2.5 Write property tests for authentication
    - **Property 1: Registration creates account**
    - **Property 3: Valid credentials authenticate**
    - **Property 4: Invalid credentials reject**
    - **Property 5: Expired tokens require re-authentication**
    - **Validates: Requirements 1.1, 1.3, 1.4, 1.6**

- [x] 3. Checkpoint - Authentication complete
  - Ensure all auth tests pass, ask the user if questions arise.

- [x] 4. Subscription app implementation
  - [x] 4.1 Create subscription app and models
    - Create `apps/subscription/` Django app
    - Define Subscription model with tier enum
    - Define TierFeatures dataclass
    - Create database migrations
    - _Requirements: 3.1_

  - [x] 4.2 Implement SubscriptionService
    - Implement `get_subscription()` and `get_tier_features()`
    - Implement `upgrade()` and `downgrade()` with immediate feature access
    - Implement `check_feature_access()` method
    - Implement `handle_lapsed_subscription()` for auto-downgrade
    - _Requirements: 3.2, 3.3, 3.4, 3.5, 3.6, 3.7_

  - [x] 4.3 Write property tests for subscriptions
    - **Property 18: Tier feature access**
    - **Property 19: Tier change preserves data**
    - **Property 20: Lapsed subscription downgrade**
    - **Validates: Requirements 3.2-3.7**

- [x] 5. CSM app implementation
  - [x] 5.1 Create CSM app and models
    - Create `apps/csm/` Django app
    - Define CSMProfile model with JSONB profile_data
    - Define dataclasses: PersonalityTraits, TonePreferences, CommunicationHabits, DecisionStyle
    - Create database migrations with version tracking
    - _Requirements: 4.1_

  - [x] 5.2 Implement CSM serialization
    - Implement `to_json()` method on CSMProfile
    - Implement `from_json()` class method
    - Ensure all nested dataclasses serialize correctly
    - _Requirements: 4.6_

  - [x] 5.3 Write property test for CSM serialization round-trip
    - **Property 10: CSM JSON serialization round-trip**
    - **Validates: Requirements 4.6**

  - [x] 5.4 Implement CSMService
    - Implement `create_from_questionnaire()` to generate initial CSM
    - Implement `get_profile()` and `update_profile()` with versioning
    - Implement `get_version_history()` and `rollback_to_version()`
    - Implement `apply_blend()` for cognitive blend application
    - _Requirements: 4.2, 4.3, 4.4, 4.5, 4.7_

  - [x] 5.5 Write property tests for CSM versioning
    - **Property 11: CSM version history and rollback**
    - **Validates: Requirements 4.7, 6.6, 12.4, 12.5**

- [x] 6. Twin app implementation
  - [x] 6.1 Create twin app and models
    - Create `apps/twin/` Django app
    - Define Twin model with user_id, model, cognitive_blend, csm_id
    - Define AIModel enum and QuestionnaireResponse dataclass
    - Create database migrations
    - _Requirements: 2.1, 2.3_

  - [x] 6.2 Implement TwinService
    - Implement `start_onboarding()` returning questionnaire
    - Implement `complete_onboarding()` creating Twin with CSM
    - Implement `update_cognitive_blend()` with validation (0-100)
    - Implement `get_twin()` and `deactivate_twin()`
    - _Requirements: 2.1, 2.2, 2.4, 2.5, 2.6_

  - [x] 6.3 Write property tests for Twin creation
    - **Property 7: Questionnaire generates CSM**
    - **Property 8: Cognitive blend storage and application**
    - **Validates: Requirements 2.2, 2.5, 4.1, 4.2**

- [x] 7. Checkpoint - Core Twin functionality complete
  - Ensure all tests pass, ask the user if questions arise.

- [x] 8. Memory app implementation
  - [x] 8.1 Create memory app and models
    - Create `apps/memory/` Django app
    - Define Memory dataclass with embedding field
    - Define MemoryQuery dataclass for retrieval parameters
    - Set up vector database client configuration
    - _Requirements: 5.1_

  - [x] 8.2 Implement VectorMemoryEngine
    - Implement async `store_memory()` with embedding generation
    - Implement `retrieve_relevant()` with relevance/recency scoring
    - Implement `validate_memory_exists()` for fabrication prevention
    - Implement `get_memory_with_source()` including timestamps
    - _Requirements: 5.1, 5.2, 5.3, 5.4, 5.6, 5.7_

  - [x] 8.3 Write property tests for memory
    - **Property 12: Interaction embedding storage**
    - **Property 13: Memory retrieval relevance**
    - **Property 14: Memory existence validation**
    - **Property 15: Memory timestamp inclusion**
    - **Validates: Requirements 5.1-5.4, 5.6, 5.7**

- [x] 9. Learning app implementation
  - [x] 9.1 Create learning app and models
    - Create `apps/learning/` Django app
    - Define LearningEvent model
    - Define ExtractedFeatures and FeedbackType
    - Create database migrations
    - _Requirements: 6.1_

  - [x] 9.2 Implement LearningService
    - Implement async `process_user_action()` for feature extraction
    - Implement async `update_profile()` for CSM updates
    - Implement `apply_feedback()` for reinforcement/correction
    - Implement `get_learning_history()` for transparency
    - _Requirements: 6.1, 6.2, 6.3, 6.4, 6.5_

  - [x] 9.3 Write property tests for learning loop
    - **Property 16: Learning loop processing**
    - **Property 17: Feedback reinforcement**
    - **Validates: Requirements 6.1-6.5**

- [x] 10. Safety app - Permissions implementation
  - [x] 10.1 Create safety app and permission models
    - Create `apps/safety/` Django app
    - Define PermissionScope model with integration, action_type, is_granted
    - Define ActionType enum
    - Create database migrations
    - _Requirements: 10.1_

  - [x] 10.2 Implement PermissionService
    - Implement `get_permissions()` and `update_permission()`
    - Implement `check_permission()` returning (allowed, needs_approval)
    - Implement `is_high_risk_action()` for financial/legal/irreversible
    - _Requirements: 10.1, 10.2, 10.3, 10.4, 10.5, 10.6, 10.7_

  - [x] 10.3 Write property tests for permissions
    - **Property 21: Permission verification before action**
    - **Property 34: Permission scope definition**
    - **Property 35: High-risk action approval**
    - **Property 36: Out-of-scope action handling**
    - **Property 37: Permission modifiability**
    - **Validates: Requirements 10.1-10.7**

- [x] 11. Safety app - Audit logging implementation
  - [x] 11.1 Create audit models
    - Define AuditEntry model with checksum field
    - Create append-only table with tamper detection
    - Create database migrations
    - _Requirements: 11.1, 11.2_

  - [x] 11.2 Implement AuditService
    - Implement `log_action()` with full context and checksum
    - Implement `get_audit_history()` with filtering
    - Implement `verify_log_integrity()` for tamper detection
    - _Requirements: 11.1, 11.2, 11.3, 11.4, 11.5_

  - [x] 11.3 Write property tests for audit logging
    - **Property 38: Comprehensive audit logging**
    - **Property 39: Audit log immutability**
    - **Property 40: Audit log filterability**
    - **Validates: Requirements 11.1-11.5**

- [x] 12. Safety app - Kill switch implementation
  - [x] 12.1 Implement KillSwitchService
    - Implement `activate_kill_switch()` to halt all automations
    - Implement `is_kill_switch_active()` check
    - Implement `deactivate_kill_switch()` to re-enable
    - Implement `get_undo_window()` and `undo_action()`
    - _Requirements: 12.1, 12.2, 12.3, 12.6_

  - [x] 12.2 Write property tests for kill switch
    - **Property 41: Kill switch behavior**
    - **Property 42: Reversible action undo**
    - **Validates: Requirements 12.1-12.3, 12.6**

- [x] 13. Checkpoint - Safety systems complete
  - Ensure all safety tests pass, ask the user if questions arise.

- [x] 14. Automation app - Integration management
  - [x] 14.1 Create automation app and integration models
    - Create `apps/automation/` Django app
    - Define Integration model with encrypted tokens
    - Define IntegrationType enum
    - Create database migrations
    - _Requirements: 7.1_

  - [x] 14.2 Implement IntegrationService
    - Implement `connect_integration()` with minimal OAuth scopes
    - Implement `get_integrations()` and `update_permissions()`
    - Implement `refresh_token()` for expired tokens
    - Implement `disconnect()` for removal
    - _Requirements: 7.2, 7.3, 7.4, 7.5_

  - [x] 14.3 Write property tests for integrations
    - **Property 27: Minimal OAuth scopes**
    - **Property 28: Integration configurability**
    - **Property 29: Token refresh handling**
    - **Validates: Requirements 7.2-7.5**

- [x] 15. Automation app - Workflow execution
  - [x] 15.1 Create workflow models
    - Define Workflow model with trigger and steps
    - Define WorkflowStep and WorkflowResult dataclasses
    - Create database migrations
    - _Requirements: 8.1_

  - [x] 15.2 Implement WorkflowEngine
    - Implement async `execute_workflow()` with permission checks
    - Implement `verify_permissions()` before execution
    - Implement `requires_confirmation()` for blend > 80%
    - Integrate with AuditService for logging
    - _Requirements: 8.1, 8.2, 8.3, 8.4, 8.5, 8.6_

  - [x] 15.3 Write property tests for workflows
    - **Property 22: External action permission flag**
    - **Property 23: Workflow async execution**
    - **Property 24: Workflow error logging**
    - **Property 25: High blend confirmation requirement**
    - **Property 26: Content origin tracking**
    - **Validates: Requirements 8.1-8.6**

- [x] 16. Voice app implementation
  - [x] 16.1 Create voice app and models
    - Create `apps/voice/` Django app
    - Define VoiceProfile model with phone_number, voice_clone_id
    - Define CallRecord model for transcripts
    - Create database migrations
    - _Requirements: 9.1, 9.5_

  - [x] 16.2 Implement VoiceTwinService
    - Implement `provision_phone_number()` via Twilio
    - Implement `create_voice_clone()` via ElevenLabs
    - Implement `approve_voice_session()` with expiry
    - Implement `handle_inbound_call()` and `make_outbound_call()` (sync)
    - Implement `terminate_call()` kill switch
    - Implement `get_call_transcript()`
    - _Requirements: 9.1, 9.2, 9.3, 9.4, 9.5, 9.6, 9.7_

  - [x] 16.3 Write property tests for voice
    - **Property 30: Phone number provisioning**
    - **Property 31: Call transcript storage**
    - **Property 32: Voice session approval requirement**
    - **Property 33: Voice kill switch availability**
    - **Validates: Requirements 9.1, 9.5, 9.6, 9.7**

- [x] 17. Checkpoint - All apps implemented
  - Ensure all tests pass, ask the user if questions arise.

- [x] 18. AI Service implementation
  - [x] 18.1 Create core AI service
    - Create `core/ai/` module
    - Implement `generate_response()` with CSM and blend application
    - Implement `extract_features()` for learning
    - Implement `generate_embeddings()` for memory
    - Configure model selection (Gemini, Qwen, Mistral)
    - _Requirements: 2.3, 4.2, 5.2, 6.1_

  - [x] 18.2 Write property tests for cognitive blend behavior
    - **Property 9: Cognitive blend behavior ranges**
    - **Validates: Requirements 4.3, 4.4, 4.5**

- [x] 19. REST API implementation
  - [x] 19.1 Set up Django Rest Framework
    - Install and configure DRF
    - Set up JWT authentication middleware
    - Configure rate limiting
    - Set up API versioning
    - _Requirements: 13.1, 13.3, 13.5, 13.6_

  - [x] 19.2 Implement auth API endpoints
    - POST /api/v1/auth/register
    - POST /api/v1/auth/verify
    - POST /api/v1/auth/login
    - POST /api/v1/auth/password-reset
    - GET /api/v1/auth/oauth/{provider}
    - _Requirements: 1.1-1.7, 13.1_

  - [x] 19.3 Implement twin API endpoints
    - POST /api/v1/twin/onboarding/start
    - POST /api/v1/twin/onboarding/complete
    - GET /api/v1/twin
    - PATCH /api/v1/twin/blend
    - _Requirements: 2.1-2.6, 13.1_

  - [x] 19.4 Implement CSM API endpoints
    - GET /api/v1/csm/profile
    - PATCH /api/v1/csm/profile
    - GET /api/v1/csm/history
    - POST /api/v1/csm/rollback
    - _Requirements: 4.1-4.7, 13.1_

  - [x] 19.5 Implement subscription API endpoints
    - GET /api/v1/subscription
    - POST /api/v1/subscription/upgrade
    - POST /api/v1/subscription/downgrade
    - _Requirements: 3.1-3.7, 13.1_

  - [x] 19.6 Implement automation API endpoints
    - GET /api/v1/integrations
    - POST /api/v1/integrations/{type}/connect
    - DELETE /api/v1/integrations/{id}
    - PATCH /api/v1/integrations/{id}/permissions
    - GET /api/v1/workflows
    - POST /api/v1/workflows
    - POST /api/v1/workflows/{id}/execute
    - _Requirements: 7.1-7.6, 8.1-8.6, 13.1_

  - [x] 19.7 Implement voice API endpoints
    - POST /api/v1/voice/enable
    - POST /api/v1/voice/approve-session
    - POST /api/v1/voice/call
    - DELETE /api/v1/voice/call/{id}
    - GET /api/v1/voice/calls
    - GET /api/v1/voice/calls/{id}/transcript
    - _Requirements: 9.1-9.7, 13.1_

  - [x] 19.8 Implement safety API endpoints
    - GET /api/v1/permissions
    - PATCH /api/v1/permissions
    - GET /api/v1/audit
    - POST /api/v1/kill-switch/activate
    - POST /api/v1/kill-switch/deactivate
    - POST /api/v1/actions/{id}/undo
    - _Requirements: 10.1-10.7, 11.1-11.5, 12.1-12.6, 13.1_

  - [x] 19.9 Write property tests for API
    - **Property 43: JSON response format** ✅ PASSED
    - **Property 44: JWT authentication enforcement** ✅ PASSED
    - **Property 45: Error response format** ✅ PASSED
    - **Property 46: Rate limiting enforcement** ✅ PASSED
    - **Validates: Requirements 13.2-13.5**

- [x] 20. Data layer finalization
  - [x] 20.1 Implement transaction handling
    - Add transaction decorators to all write operations
    - Ensure atomic operations across related tables
    - _Requirements: 14.3_

  - [x] 20.2 Implement async task queue
    - Set up Celery or Django-Q for background tasks
    - Configure async memory writes
    - Configure async embedding generation
    - _Requirements: 14.5_

  - [x] 20.3 Write property tests for data layer
    - **Property 47: Transaction integrity** ✅ PASSED
    - **Property 48: Async memory writes** ✅ PASSED
    - **Validates: Requirements 14.3, 14.5**

- [x] 21. Final checkpoint - All systems integrated
  - Ensure all tests pass, ask the user if questions arise.
  - Verify all 48 correctness properties are covered by tests.

## Notes

- All tasks including property tests are required for comprehensive coverage
- Each task references specific requirements for traceability
- Checkpoints ensure incremental validation
- Property tests validate universal correctness properties
- Unit tests validate specific examples and edge cases
- Use Hypothesis for all property-based tests with minimum 100 iterations
