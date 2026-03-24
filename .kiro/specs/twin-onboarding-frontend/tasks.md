# Implementation Plan: Twin Onboarding Frontend

## Overview

This implementation plan breaks down the Twin Onboarding Frontend feature into discrete, incremental coding tasks. Each task builds on previous work, with testing integrated throughout to validate functionality early. The plan follows a bottom-up approach: building reusable components first, then composing them into step components, and finally wiring everything together in the main wizard orchestrator.

## Tasks

- [x] 1. Set up project structure and TypeScript types
  - Create `/neuro-frontend/src/types/onboarding.ts` with all interfaces
  - Create `/neuro-frontend/src/lib/api/onboarding.ts` API client module
  - Define `OnboardingState`, `QuestionnaireResponses`, `AIModel`, `Question` interfaces
  - _Requirements: 1.1, 4.1, 5.1_

- [ ] 2. Implement API integration layer
  - [x] 2.1 Create onboarding API client functions
    - Implement `onboardingApi.start()` for fetching questionnaire and saved progress
    - Implement `onboardingApi.saveProgress()` for saving partial progress
    - Implement `onboardingApi.complete()` for twin creation
    - Add error handling with typed error classes
    - _Requirements: 4.1, 8.1, 8.2, 10.1_

  - [x] 2.2 Write property test for API error handling
    - **Property 20: Error Message Display**
    - **Validates: Requirements 12.1, 12.3, 12.5**

- [x] 3. Build reusable question components
  - [x] 3.1 Implement SliderQuestion component
    - Create component with range slider (0.0-1.0)
    - Display current value and min/max labels
    - Handle onChange events
    - Add ARIA labels for accessibility
    - _Requirements: 4.4, 11.5, 11.6_

  - [x] 3.2 Implement TextQuestion component
    - Create text input with validation
    - Handle onChange events
    - Display validation errors
    - _Requirements: 4.5_

  - [x] 3.3 Implement SelectQuestion component
    - Create selectable card layout
    - Support single and multi-select modes
    - Visual selection states
    - _Requirements: 4.6_

  - [x] 3.4 Implement TextListQuestion component
    - Create dynamic list of text inputs
    - Add/remove functionality
    - Handle array of values
    - _Requirements: 4.7_

  - [] 3.5 Write property test for question type rendering
    - **Property 7: Question Type Determines Input Control**
    - **Validates: Requirements 4.3, 4.4, 4.5, 4.6, 4.7**

- [x] 4. Implement validation logic
  - [x] 4.1 Create validation functions
    - Implement `validateCommunicationStyle()`
    - Implement `validateDecisionPatterns()`
    - Implement `validatePreferences()`
    - Implement `validateModelSelection()`
    - Implement `validateBlend()`
    - _Requirements: 2.5, 4.8_

  - [x] 4.2 Write property test for validation
    - **Property 5: Validation Prevents Invalid Advancement**
    - **Validates: Requirements 2.5, 4.8**

- [x] 5. Build step components
  - [x] 5.1 Implement WelcomeStep component
    - Create hero section with Twin explanation
    - Add "Get Started" button
    - Implement navigation to next step
    - _Requirements: 3.1, 3.3, 3.5_

  - [x] 5.2 Implement QuestionnaireStep component
    - Render questions based on section
    - Use question components based on type
    - Handle form state updates
    - Implement section validation
    - _Requirements: 4.2, 4.3, 4.8_

  - [x] 5.3 Implement ModelSelectionStep component
    - Display model cards in grid layout
    - Show tier requirements and availability
    - Handle model selection
    - Implement conditional upgrade badges
    - _Requirements: 5.1, 5.2, 5.3, 5.4, 5.5_

  - [ ]* 5.4 Write property test for model tier indicators
    - **Property 8: Model Tier Availability Indicators**
    - **Validates: Requirements 5.2, 5.3, 5.4**

  - [x] 5.5 Implement CognitiveBlendStep component
    - Create blend slider (0-100)
    - Display current value and zone description
    - Show confirmation notice for high blend values
    - _Requirements: 6.1, 6.2, 6.3, 6.4, 6.5_

  - [ ]* 5.6 Write property test for blend description updates
    - **Property 9: Cognitive Blend Description Updates**
    - **Validates: Requirements 6.3**

  - [x] 5.7 Implement PaymentStep component (conditional)
    - Display PRO tier benefits
    - Create payment form with card inputs
    - Implement form validation
    - Handle subscription upgrade API call
    - Show loading and error states
    - _Requirements: 7.1, 7.2, 7.3, 7.4, 7.5, 7.6_

  - [x] 5.8 Write property test for payment validation
    - **Property 10: Payment Form Validation**
    - **Validates: Requirements 7.3**

  - [x] 5.9 Implement ReviewStep component
    - Display all selections organized by section
    - Add edit links for each section
    - Show "Create My Twin" button
    - _Requirements: 9.1, 9.2, 9.3, 9.4, 9.5, 9.6_

  - [x]* 5.10 Write property test for review data organization
    - **Property 13: Review Screen Data Organization**
    - **Validates: Requirements 9.2**

  - [x]* 5.11 Write property test for edit link navigation
    - **Property 14: Edit Links Navigate to Correct Steps**
    - **Validates: Requirements 9.5**

  - [x] 5.12 Implement CreatingStep component
    - Display loading animation
    - Show status messages
    - Call twin creation API
    - Handle success and error states
    - _Requirements: 10.1, 10.2, 10.3, 10.4_

  - [x] 5.13 Write property test for twin creation API completeness
    - **Property 15: Twin Creation API Call Completeness**
    - **Validates: Requirements 10.1**

  - [x] 5.14 Implement SuccessStep component
    - Display success message
    - Show next steps
    - Add "Go to Dashboard" button
    - _Requirements: 10.3, 10.5, 10.6_

- [ ] 6. Checkpoint - Ensure all step components render correctly
  - Ensure all tests pass, ask the user if questions arise.


- [x] 7. Implement ProgressIndicator component
  - [x] 7.1 Create progress indicator UI
    - Display step numbers with completion status
    - Show progress bar with percentage
    - Display current step label
    - _Requirements: 2.1_

  - [x] 7.2 Write property test for progress indicator accuracy
    - **Property 2: Progress Indicator Accuracy**
    - **Validates: Requirements 2.1**

- [x] 8. Implement useOnboarding custom hook
  - [x] 8.1 Create hook with state management
    - Initialize state from API on mount
    - Implement navigation handlers (goNext, goBack)
    - Implement progress saving logic
    - Handle step validation
    - Manage loading and error states
    - _Requirements: 2.4, 8.1, 8.2, 8.3, 8.4_

  - [x] 8.2 Write property test for data preservation during navigation
    - **Property 4: Data Preservation During Back Navigation**
    - **Validates: Requirements 2.4**

  - [ ]* 8.3 Write property test for progress saving
    - **Property 11: Progress Saving After Step Completion**
    - **Validates: Requirements 8.1**

  - [ ]* 8.4 Write property test for saved progress restoration
    - **Property 12: Saved Progress Restoration**
    - **Validates: Requirements 8.3, 8.4**

- [x] 9. Implement main OnboardingWizard component
  - [x] 9.1 Create wizard orchestrator
    - Use useOnboarding hook for state
    - Render ProgressIndicator
    - Render current step component
    - Implement Back/Next button logic
    - Handle conditional payment step
    - _Requirements: 2.2, 2.3, 2.4, 2.5, 7.1, 7.7_

  - [ ]* 9.2 Write property test for navigation button visibility
    - **Property 3: Navigation Button Visibility**
    - **Validates: Requirements 2.2, 2.3**

  - [ ]* 9.3 Write property test for keyboard navigation
    - **Property 6: Keyboard Navigation Support**
    - **Validates: Requirements 2.6**

- [x] 10. Implement onboarding page and routing
  - [x] 10.1 Create /app/onboarding/page.tsx
    - Set up page component
    - Integrate OnboardingWizard
    - Handle URL query parameters for step tracking
    - Implement redirect logic for existing twins
    - _Requirements: 1.1, 1.2, 1.3, 1.4_

  - [ ]* 10.2 Write property test for query parameter preservation
    - **Property 1: Query Parameter Preservation During Redirects**
    - **Validates: Requirements 1.3**

  - [x] 10.3 Add redirect logic to dashboard
    - Check twin existence on dashboard load
    - Redirect to onboarding if 404 from twin API
    - Preserve return URL for post-onboarding redirect
    - _Requirements: 1.1_

- [x] 11. Implement responsive design and styling
  - [x] 11.1 Add responsive layouts
    - Implement mobile styles (320px+)
    - Implement tablet styles (768px+)
    - Implement desktop styles (1024px+)
    - Use GlassPanel component for cards
    - Apply NeuroTwin color palette (purple-700, neutral-800, etc.)
    - _Requirements: 11.1, 11.2, 11.3_

  - [x]* 11.2 Write property test for touch target sizes
    - **Property 16: Touch Target Minimum Size**
    - **Validates: Requirements 11.4**

- [x] 12. Implement accessibility features
  - [x] 12.1 Add keyboard navigation support
    - Implement Enter key for advancement
    - Implement Escape key for going back
    - Ensure all interactive elements are keyboard accessible
    - _Requirements: 2.6, 11.5_

  - [x] 12.2 Add ARIA labels and semantic HTML
    - Add ARIA labels to all icon buttons
    - Add ARIA labels to sliders and custom controls
    - Use semantic HTML elements
    - _Requirements: 11.6_

  - [ ]* 12.3 Write property test for keyboard accessibility
    - **Property 17: Keyboard Accessibility**
    - **Validates: Requirements 11.5**

  - [ ]* 12.4 Write property test for ARIA label presence
    - **Property 18: ARIA Label Presence**
    - **Validates: Requirements 11.6**

  - [ ]* 12.5 Write property test for color contrast
    - **Property 19: Color Contrast Compliance**
    - **Validates: Requirements 11.7**

- [x] 13. Implement error handling and recovery
  - [x] 13.1 Add error handling to all API calls
    - Implement network error detection
    - Display user-friendly error messages
    - Add retry buttons for recoverable errors
    - Handle session expiration with redirect
    - _Requirements: 12.1, 12.2, 12.3, 12.4, 12.5_

  - [ ]* 13.2 Write property test for network error recovery
    - **Property 21: Network Error Recovery**
    - **Validates: Requirements 12.2**

- [x] 14. Checkpoint - Ensure all tests pass
  - Ensure all tests pass, ask the user if questions arise.

- [x] 15. Integration and final wiring
  - [x] 15.1 Wire onboarding to authentication flow
    - Ensure onboarding only accessible to authenticated users
    - Redirect unauthenticated users to login
    - Preserve onboarding state across auth redirects
    - _Requirements: 1.1, 12.4_

  - [x] 15.2 Wire onboarding to dashboard
    - Implement post-onboarding redirect to dashboard
    - Display welcome message for new twins
    - Ensure twin data is available after creation
    - _Requirements: 1.4, 10.6_

  - [x] 15.3 Test complete onboarding flow end-to-end
    - Test happy path from start to finish
    - Test progress saving and resumption
    - Test payment flow for premium models
    - Test error scenarios and recovery
    - _Requirements: All_

- [x] 16. Final checkpoint - Ensure all tests pass
  - Ensure all tests pass, ask the user if questions arise.

## Notes

- Each task references specific requirements for traceability
- Checkpoints ensure incremental validation
- Property tests validate universal correctness properties with minimum 100 iterations
- Unit tests validate specific examples and edge cases
- The wizard uses TypeScript with strict mode for type safety
- All components follow the NeuroTwin design system (GlassPanel, purple-700 primary color)
- API integration uses the existing `api` client from `lib/api.ts`
- Authentication uses the existing `useAuth` hook
- All tests are required for comprehensive validation from the start
