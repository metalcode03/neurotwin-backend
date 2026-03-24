# Requirements Document: Twin Onboarding Frontend

## Introduction

The Twin Onboarding Frontend provides a guided, multi-step wizard interface that helps new users create their cognitive digital twin. When a signed-in user has no twin (backend returns 404), they are redirected to this onboarding flow where they answer personality questions, select an AI model, configure cognitive blend settings, and optionally upgrade their subscription for premium models. The feature ensures a smooth, user-friendly experience with progress saving, clear explanations, and seamless integration with payment flows.

## Glossary

- **Twin**: A cognitive digital twin - an AI replica of the user's mind that learns their communication style, decision patterns, and personality
- **Onboarding_Wizard**: The multi-step UI flow that guides users through twin creation
- **Questionnaire**: A structured set of personality and preference questions organized into three sections
- **Cognitive_Blend**: A 0-100 scale controlling how much human personality vs AI logic the twin uses
- **CSM**: Cognitive Signature Model - stores personality, tone, habits, and decision patterns
- **Subscription_Tier**: User's plan level (FREE, PRO, TWIN_PLUS, EXECUTIVE)
- **AI_Model**: The underlying language model powering the twin (gemini-3-flash, gemini-3-pro, qwen, mistral)
- **Progress_State**: Saved partial completion data allowing users to resume onboarding later
- **Payment_Flow**: The subscription upgrade process for accessing premium AI models

## Requirements

### Requirement 1: Onboarding Trigger and Redirect

**User Story:** As a signed-in user without a twin, I want to be automatically redirected to onboarding, so that I can create my twin without confusion.

#### Acceptance Criteria

1. WHEN the Frontend queries GET /api/v1/twin/ and receives a 404 response, THEN the System SHALL redirect the user to the onboarding wizard
2. WHEN a user is on the onboarding wizard and already has a twin, THEN the System SHALL redirect them to the dashboard
3. WHEN the redirect occurs, THEN the System SHALL preserve any query parameters or state needed for navigation
4. WHEN the user completes onboarding, THEN the System SHALL redirect them to the dashboard with a success indicator

### Requirement 2: Multi-Step Wizard Navigation

**User Story:** As a user, I want to navigate through onboarding steps with clear progress indication, so that I understand where I am in the process.

#### Acceptance Criteria

1. THE Onboarding_Wizard SHALL display a progress indicator showing current step and total steps
2. WHEN a user is on any step except the first, THEN the System SHALL display a "Back" button to return to the previous step
3. WHEN a user is on any step except the last, THEN the System SHALL display a "Next Step" button to advance
4. WHEN a user clicks "Back", THEN the System SHALL navigate to the previous step without losing entered data
5. WHEN a user attempts to advance without completing required fields, THEN the System SHALL display validation errors and prevent advancement
6. THE Onboarding_Wizard SHALL support keyboard navigation (Enter to advance, Escape to go back)

### Requirement 3: Welcome and Education Screen

**User Story:** As a new user, I want to understand what a Twin is and what it can do, so that I can make an informed decision about creating one.

#### Acceptance Criteria

1. THE Onboarding_Wizard SHALL display a welcome screen as the first step
2. THE Welcome_Screen SHALL explain what a cognitive digital twin is in clear, non-technical language
3. THE Welcome_Screen SHALL list key capabilities of the twin (communication handling, task automation, personality mimicry)
4. THE Welcome_Screen SHALL display visual elements (icons, illustrations) to enhance understanding
5. WHEN a user clicks "Get Started" or "Next Step", THEN the System SHALL advance to the questionnaire

### Requirement 4: Personality Questionnaire Collection

**User Story:** As a user, I want to answer personality questions in an intuitive interface, so that my Twin learns my communication style and preferences.

#### Acceptance Criteria

1. WHEN the Onboarding_Wizard loads the questionnaire, THEN the System SHALL fetch questions from POST /api/v1/twin/onboarding/start
2. THE Onboarding_Wizard SHALL display questionnaire sections across three separate steps (Communication Style, Decision Making, Personal Preferences)
3. FOR EACH question, THE System SHALL display the question text, question type, and appropriate input control (slider, text field, select dropdown, multi-text input)
4. WHEN a question type is "slider", THEN the System SHALL display a range slider with values 0.0 to 1.0 and visual labels
5. WHEN a question type is "text", THEN the System SHALL display a text input field with appropriate validation
6. WHEN a question type is "select", THEN the System SHALL display selectable options as cards or dropdown
7. WHEN a question type is "text_list", THEN the System SHALL allow users to add multiple text entries
8. WHEN a user completes a questionnaire section, THEN the System SHALL validate all required fields before allowing advancement

### Requirement 5: AI Model Selection

**User Story:** As a user, I want to choose an AI model that fits my needs and budget, so that my Twin uses the right technology for my use case.

#### Acceptance Criteria

1. THE Onboarding_Wizard SHALL display available AI models with their names, descriptions, and tier requirements
2. WHEN displaying models, THEN the System SHALL clearly indicate which models are available on the user's current subscription tier
3. WHEN displaying models, THEN the System SHALL show which models require a subscription upgrade
4. WHEN a user selects a model available on their tier, THEN the System SHALL mark it as selected and allow advancement
5. WHEN a user on FREE tier selects gemini-3-pro, THEN the System SHALL mark it as selected and indicate an upgrade is required
6. THE Model_Selection_Screen SHALL display model capabilities and performance characteristics to aid decision-making

### Requirement 6: Cognitive Blend Configuration

**User Story:** As a user, I want to set how much personality vs AI logic my Twin uses, so that I can control its behavior style.

#### Acceptance Criteria

1. THE Onboarding_Wizard SHALL display a cognitive blend slider with range 0-100
2. THE Cognitive_Blend_Screen SHALL display explanations for different blend ranges (0-30%: Pure AI logic, 31-70%: Balanced, 71-100%: Heavy personality mimicry)
3. WHEN a user adjusts the slider, THEN the System SHALL update the visual indicator and display the corresponding behavior description
4. THE Cognitive_Blend_Screen SHALL set a default value of 50 if the user does not adjust it
5. WHEN a user sets blend above 70%, THEN the System SHALL display a notice about confirmation requirements for actions

### Requirement 7: Subscription Upgrade Flow

**User Story:** As a free user wanting a pro model, I want to upgrade my subscription seamlessly within onboarding, so that I can access premium features.

#### Acceptance Criteria

1. WHEN a FREE tier user selects gemini-3-pro and advances past model selection, THEN the System SHALL display a payment step
2. THE Payment_Step SHALL display the PRO tier benefits and pricing
3. THE Payment_Step SHALL provide a card details input form with validation
4. WHEN a user submits valid payment details, THEN the System SHALL call POST /api/v1/subscription/upgrade with the PRO tier
5. WHEN the upgrade succeeds, THEN the System SHALL update the user's session to reflect the new tier and advance to the next step
6. WHEN the upgrade fails, THEN the System SHALL display an error message and allow retry
7. WHEN a user on PRO or higher tier selects gemini-3-pro, THEN the System SHALL skip the payment step

### Requirement 8: Progress Saving and Resumption

**User Story:** As a user, I want my onboarding progress to be saved automatically, so that I can complete it later if interrupted.

#### Acceptance Criteria

1. WHEN a user completes any step in the onboarding wizard, THEN the System SHALL call PATCH /api/v1/twin/onboarding/progress with the current state
2. WHEN a user returns to the onboarding wizard, THEN the System SHALL fetch saved progress from POST /api/v1/twin/onboarding/start
3. WHEN saved progress exists, THEN the System SHALL pre-populate all previously answered questions and selections
4. WHEN saved progress exists, THEN the System SHALL navigate the user to the last incomplete step
5. WHEN progress saving fails, THEN the System SHALL display a warning but allow the user to continue

### Requirement 9: Review and Confirmation

**User Story:** As a user, I want to review all my selections before creating my Twin, so that I can verify everything is correct.

#### Acceptance Criteria

1. THE Onboarding_Wizard SHALL display a review step showing all user selections before twin creation
2. THE Review_Screen SHALL display questionnaire answers organized by section
3. THE Review_Screen SHALL display selected AI model and subscription tier
4. THE Review_Screen SHALL display cognitive blend setting with description
5. WHEN a user identifies an error, THEN the System SHALL provide "Edit" links to return to specific steps
6. WHEN a user clicks "Create My Twin", THEN the System SHALL advance to the creation step

### Requirement 10: Twin Creation and Success

**User Story:** As a user, I want clear feedback when my Twin is being created, so that I know the process is working.

#### Acceptance Criteria

1. WHEN a user confirms twin creation, THEN the System SHALL call POST /api/v1/twin/onboarding/complete with all collected data
2. WHILE the twin is being created, THE System SHALL display a loading state with progress indication
3. WHEN twin creation succeeds, THEN the System SHALL display a success screen with next steps
4. WHEN twin creation fails, THEN the System SHALL display an error message with retry option
5. THE Success_Screen SHALL provide a clear call-to-action to navigate to the dashboard
6. WHEN a user navigates to the dashboard after success, THEN the System SHALL display a welcome message for the new twin

### Requirement 11: Responsive Design and Accessibility

**User Story:** As a user on any device, I want the onboarding wizard to work smoothly, so that I can create my Twin from mobile or desktop.

#### Acceptance Criteria

1. THE Onboarding_Wizard SHALL render correctly on mobile devices (320px width and above)
2. THE Onboarding_Wizard SHALL render correctly on tablet devices (768px width and above)
3. THE Onboarding_Wizard SHALL render correctly on desktop devices (1024px width and above)
4. THE Onboarding_Wizard SHALL use touch-friendly controls on mobile devices (minimum 44px touch targets)
5. THE Onboarding_Wizard SHALL support keyboard navigation for all interactive elements
6. THE Onboarding_Wizard SHALL provide appropriate ARIA labels for screen readers
7. THE Onboarding_Wizard SHALL maintain sufficient color contrast ratios (WCAG AA standard)

### Requirement 12: Error Handling and Recovery

**User Story:** As a user, I want clear error messages and recovery options when something goes wrong, so that I can complete onboarding successfully.

#### Acceptance Criteria

1. WHEN any API call fails, THEN the System SHALL display a user-friendly error message
2. WHEN a network error occurs, THEN the System SHALL provide a retry option
3. WHEN validation fails, THEN the System SHALL highlight the specific fields with errors and display helpful messages
4. WHEN the user's session expires during onboarding, THEN the System SHALL redirect to login and preserve progress
5. WHEN an unexpected error occurs, THEN the System SHALL log the error details and display a generic error message with support contact information
