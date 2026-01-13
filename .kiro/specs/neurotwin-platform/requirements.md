# Requirements Document

## Introduction

NeuroTwin is a cognitive digital twin/personal assistant platform that creates a living AI replica of a user's mind. The system learns the user's language style, decision patterns, productivity rhythm, emotional markers, and delegation habits, then performs tasks autonomously across connected apps and phone calls. This document specifies the requirements for the complete NeuroTwin platform including authentication, twin creation, cognitive engine, automation hub, voice twin, and safety systems.

## Glossary

- **Twin**: The AI replica of a user's cognitive patterns and personality
- **CSM (Cognitive Signature Model)**: The structured profile storing personality, tone, habits, and decision patterns
- **Cognitive_Blend**: A 0-100% slider controlling how much human personality vs AI logic the Twin uses
- **Vector_Memory_Engine**: Long-term memory storage using embeddings for semantic retrieval
- **Automation_Hub**: The system managing integrations and automated workflows across connected apps
- **Voice_Twin**: The subsystem handling phone calls using cloned voice
- **Kill_Switch**: Emergency mechanism to halt all automated behaviors
- **Permission_Scope**: Defined boundaries for what actions the Twin can perform
- **Audit_Log**: Timestamped record of all Twin actions and decisions
- **Learning_Loop**: The cycle of User Action → Feature Extraction → Profile Update → Behavior Shift → Feedback Reinforcement

## Requirements

### Requirement 1: User Authentication

**User Story:** As a new user, I want to create an account and sign in securely, so that I can access my personal Twin and keep my cognitive data private.

#### Acceptance Criteria

1. WHEN a user submits valid email and password, THE Authentication_System SHALL create a new account and send a verification email
2. WHEN a user clicks the verification link, THE Authentication_System SHALL activate the account and allow login
3. WHEN a user attempts login with valid credentials, THE Authentication_System SHALL authenticate and return a session token
4. WHEN a user attempts login with invalid credentials, THE Authentication_System SHALL reject the request and return an error message
5. WHEN a user initiates Google OAuth, THE Authentication_System SHALL redirect to Google, handle the callback, and create or link the account
6. IF a user's session token expires, THEN THE Authentication_System SHALL require re-authentication
7. WHEN a user requests password reset, THE Authentication_System SHALL send a secure reset link valid for 24 hours

### Requirement 2: Twin Creation and Onboarding

**User Story:** As a new user, I want to create my cognitive Twin through an onboarding process, so that the system can learn my personality and communication style.

#### Acceptance Criteria

1. WHEN a user starts Twin creation, THE Onboarding_System SHALL present a cognitive questionnaire covering communication style, decision patterns, and preferences
2. WHEN a user completes the questionnaire, THE Onboarding_System SHALL generate an initial CSM profile from the responses
3. WHEN creating a Twin, THE System SHALL allow selection from available AI models: Gemini-3 Flash, Qwen, Mistral (Free tier), or Gemini-3 Pro (Paid tiers)
4. THE Onboarding_System SHALL display the Cognitive_Blend slider (0-100%) and explain its effect on Twin behavior
5. WHEN a user sets the Cognitive_Blend, THE System SHALL store the preference and apply it to all Twin responses
6. WHEN onboarding completes, THE System SHALL create the Twin with initial CSM and empty Vector_Memory_Engine

### Requirement 3: Pricing and Subscription Management

**User Story:** As a user, I want to choose a pricing tier that matches my needs, so that I can access the appropriate features and AI models.

#### Acceptance Criteria

1. THE Subscription_System SHALL support four tiers: Free, Pro, Twin+, and Executive
2. WHEN a user is on Free tier, THE System SHALL provide access to Gemini-3 Flash, Qwen, and Mistral models with chat and light memory features
3. WHEN a user is on Pro tier, THE System SHALL provide access to Gemini-3 Pro with full cognitive learning capabilities
4. WHEN a user is on Twin+ tier, THE System SHALL provide Pro features plus Voice_Twin functionality
5. WHEN a user is on Executive tier, THE System SHALL provide Twin+ features plus autonomous workflows and custom model options
6. WHEN a user upgrades or downgrades, THE Subscription_System SHALL adjust feature access immediately while preserving existing data
7. IF a user's subscription lapses, THEN THE System SHALL downgrade to Free tier and disable premium features

### Requirement 4: Cognitive Signature Model (CSM)

**User Story:** As a user, I want my Twin to accurately represent my personality and communication style, so that it can act authentically on my behalf.

#### Acceptance Criteria

1. THE CSM SHALL store structured data including: personality traits, tone preferences, vocabulary patterns, decision-making style, and communication habits
2. WHEN the Twin generates a response, THE Cognitive_Engine SHALL load the CSM profile and apply personality matching proportional to Cognitive_Blend
3. WHEN Cognitive_Blend is 0-30%, THE Twin SHALL use pure AI logic with minimal personality mimicry
4. WHEN Cognitive_Blend is 31-70%, THE Twin SHALL balance user personality with AI reasoning
5. WHEN Cognitive_Blend is 71-100%, THE Twin SHALL heavily mimic personality and require confirmation before actions
6. THE CSM SHALL be serializable to JSON for storage and retrieval
7. WHEN CSM is updated, THE System SHALL maintain change history for rollback capability

### Requirement 5: Vector Memory Engine

**User Story:** As a user, I want my Twin to remember our interactions and learn from them, so that it becomes more accurate over time.

#### Acceptance Criteria

1. THE Vector_Memory_Engine SHALL store user interactions as embeddings for semantic retrieval
2. WHEN a new interaction occurs, THE Memory_Engine SHALL asynchronously generate embeddings and store them
3. WHEN the Twin needs context, THE Memory_Engine SHALL retrieve semantically relevant memories based on the current query
4. THE Memory_Engine SHALL only reference memories that actually exist and never fabricate information
5. WHEN memory is uncertain or incomplete, THE Twin SHALL acknowledge gaps rather than guess
6. THE Memory_Engine SHALL include source timestamps with all memory reads for validation
7. WHEN retrieving memories, THE System SHALL respect recency and relevance scoring

### Requirement 6: Learning Loop

**User Story:** As a user, I want my Twin to continuously improve by learning from my actions and feedback, so that it becomes more aligned with my preferences.

#### Acceptance Criteria

1. WHEN a user performs an action, THE Learning_System SHALL extract relevant features for profile updating
2. WHEN features are extracted, THE Learning_System SHALL update the CSM profile asynchronously
3. WHEN the CSM is updated, THE Twin SHALL shift behavior to reflect the new patterns
4. WHEN a user provides feedback on Twin actions, THE Learning_System SHALL reinforce or correct the behavior
5. THE Learning_Loop SHALL process: User Action → Feature Extraction → Profile Update → Behavior Shift → Feedback Reinforcement
6. ALL profile updates SHALL be reversible through the change history

### Requirement 7: Automation Hub - Integration Management

**User Story:** As a user, I want to connect my apps to the Twin, so that it can perform tasks across my digital ecosystem.

#### Acceptance Criteria

1. THE Automation_Hub SHALL support integrations with: WhatsApp, Telegram, Slack, Gmail, Outlook, Google Calendar, Google Docs, Microsoft Office, Zoom, Google Meet, and CRM tools
2. WHEN a user connects an integration, THE System SHALL request only necessary OAuth scopes and store tokens securely
3. EACH integration SHALL have configurable steering rules defining allowed actions
4. EACH integration SHALL have permission settings that the user can modify
5. WHEN an integration token expires, THE System SHALL attempt refresh or notify the user to reconnect
6. THE Automation_Hub SHALL provide a unified interface for managing all connected integrations

### Requirement 8: Automation Hub - Workflow Execution

**User Story:** As a user, I want my Twin to execute automated workflows across my connected apps, so that routine tasks are handled without my intervention.

#### Acceptance Criteria

1. WHEN a workflow is triggered, THE Automation_Hub SHALL verify the user has granted permission for the required actions
2. WHEN executing actions on external integrations, THE Twin SHALL require explicit permission_flag=True
3. THE Automation_Hub SHALL execute workflows asynchronously to avoid blocking user interactions
4. WHEN a workflow step fails, THE System SHALL log the error and notify the user
5. WHEN Cognitive_Blend exceeds 80%, THE System SHALL require explicit user confirmation before executing external actions
6. THE System SHALL distinguish Twin-generated content from user-authored content in all integrations

### Requirement 9: Voice Twin - Phone Capabilities

**User Story:** As a Twin+ or Executive user, I want my Twin to handle phone calls using my cloned voice, so that it can communicate on my behalf.

#### Acceptance Criteria

1. WHEN a user enables Voice_Twin, THE System SHALL provision a virtual phone number via Twilio
2. THE Voice_Twin SHALL use ElevenLabs for voice cloning based on user-provided samples
3. WHEN a call is received, THE Voice_Twin SHALL answer using the cloned voice and CSM personality
4. WHEN a call is made, THE Voice_Twin SHALL use the cloned voice and follow user-defined scripts or CSM guidance
5. THE Voice_Twin SHALL generate and store transcripts for all calls
6. Voice cloning SHALL require separate explicit approval per session
7. THE Voice_Twin SHALL have an accessible Kill_Switch to immediately terminate any call

### Requirement 10: Safety - Permission System

**User Story:** As a user, I want granular control over what my Twin can do, so that I maintain authority over my digital presence.

#### Acceptance Criteria

1. THE Permission_System SHALL define scopes for each integration and action type
2. WHEN the Twin attempts an action, THE System SHALL verify the action falls within granted permission scopes
3. THE Twin SHALL NOT perform financial transactions without explicit per-transaction approval
4. THE Twin SHALL NOT perform legal actions without explicit per-action approval
5. THE Twin SHALL NOT perform irreversible actions without explicit approval
6. WHEN an action is outside permission scope, THE System SHALL request user approval before proceeding
7. THE User SHALL be able to modify permission scopes at any time through settings

### Requirement 11: Safety - Audit and Logging

**User Story:** As a user, I want complete visibility into what my Twin does, so that I can review and trust its actions.

#### Acceptance Criteria

1. THE Audit_System SHALL log every Twin action with: timestamp, action type, target integration, input data, outcome, and Cognitive_Blend value used
2. THE Audit_Log SHALL be immutable and tamper-evident
3. WHEN a user requests audit history, THE System SHALL provide filterable, searchable access to all logged actions
4. THE Audit_System SHALL retain logs according to the user's data retention preferences
5. WHEN the Twin makes a decision, THE System SHALL log the reasoning chain for transparency

### Requirement 12: Safety - Kill Switch and Rollback

**User Story:** As a user, I want emergency controls to stop my Twin and undo its actions, so that I can recover from mistakes or unwanted behavior.

#### Acceptance Criteria

1. THE Kill_Switch SHALL be accessible from all user interfaces and immediately halt all Twin automations
2. WHEN Kill_Switch is activated, THE System SHALL terminate all in-progress workflows and calls
3. WHEN Kill_Switch is activated, THE System SHALL prevent new automated actions until manually re-enabled
4. THE Rollback_System SHALL allow reverting CSM changes to any previous state in the change history
5. WHEN a rollback is requested, THE System SHALL restore the CSM to the selected state and log the rollback action
6. THE System SHALL provide undo capability for reversible Twin actions within a configurable time window

### Requirement 13: API Design

**User Story:** As a developer, I want a well-structured REST API, so that the frontend and integrations can interact with the platform reliably.

#### Acceptance Criteria

1. THE API SHALL follow REST conventions with consistent resource naming and HTTP methods
2. THE API SHALL use JSON for request and response bodies
3. THE API SHALL require authentication via JWT tokens for all protected endpoints
4. WHEN an API request fails, THE System SHALL return appropriate HTTP status codes and descriptive error messages
5. THE API SHALL implement rate limiting to prevent abuse
6. THE API SHALL version endpoints to support backward compatibility

### Requirement 14: Data Persistence

**User Story:** As a user, I want my data stored reliably, so that my Twin's knowledge and my preferences are never lost.

#### Acceptance Criteria

1. THE System SHALL store structured data (users, subscriptions, CSM profiles, permissions) in PostgreSQL
2. THE System SHALL store embeddings and semantic memory in a Vector database
3. WHEN writing to the database, THE System SHALL use transactions to ensure data integrity
4. THE System SHALL implement backup and recovery procedures for all data stores
5. Memory writes SHALL be asynchronous to avoid blocking user requests
