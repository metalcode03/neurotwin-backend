# Implementation Plan: NeuroTwin Dashboard Frontend

## Overview

This implementation plan breaks down the NeuroTwin Dashboard Frontend into incremental coding tasks. Each task builds on previous work, ensuring no orphaned code. The plan uses Next.js 14+ with App Router, TailwindCSS, Framer Motion, and React Query. Property-based tests use fast-check.

## Tasks

- [x] 1. Project setup and configuration
  - [x] 1.1 Configure Tailwind with NeuroTwin color palette
    - Update tailwind.config.ts with purple and neutral color tokens
    - Add glass morphism utilities to globals.css
    - Add btn-primary and btn-outline utility classes
    - _Requirements: 12.1, 12.2, 12.3, 12.4_

  - [x] 1.2 Install and configure dependencies
    - Install react-icons, framer-motion, @tanstack/react-query
    - Configure React Query provider
    - Set up TypeScript strict mode
    - _Requirements: 13.1_

  - [x] 1.3 Create TypeScript type definitions
    - Create types/twin.ts, types/apps.ts, types/activity.ts
    - Create types/memory.ts, types/voice.ts, types/security.ts
    - Create types/api.ts for API response types
    - _Requirements: 13.2_

  - [x] 1.4 Set up testing infrastructure
    - Install Jest, React Testing Library, fast-check, jest-axe
    - Configure Jest for Next.js
    - Create test directory structure
    - _Requirements: Testing Strategy_

- [x] 2. Core UI components
  - [x] 2.1 Create GlassPanel component
    - Implement glass morphism styling with backdrop blur
    - Add Framer Motion animation support
    - Ensure rounded-xl border radius
    - _Requirements: 2.8, 12.5_

  - [x] 2.2 Create Button component
    - Implement primary, outline, danger, ghost variants
    - Add size variants (sm, md, lg)
    - Ensure rounded-lg border radius and focus states
    - _Requirements: 12.3, 12.4, 12.6, 14.6_

  - [x] 2.3 Create Slider component
    - Implement range input with custom styling
    - Add label and value display options
    - Ensure keyboard accessibility
    - _Requirements: 2.2, 14.1_

  - [x] 2.4 Create Toggle component
    - Implement on/off toggle with label and description
    - Ensure keyboard accessibility and ARIA attributes
    - _Requirements: 6.3, 14.1, 14.2_

  - [x] 2.5 Create Badge component
    - Implement success, default, warning variants
    - Apply appropriate color coding
    - _Requirements: 4.6_

  - [-] 2.6 Write property tests for UI components


    - **Property 28: Consistent border radius**
    - **Validates: Requirements 12.5, 12.6**

- [x] 3. Layout components
  - [x] 3.1 Create Sidebar component
    - Implement fixed sidebar with navigation items
    - Add react-icons for each menu item
    - Apply bg-neutral-800 with white text
    - Implement active state highlighting with purple-700
    - _Requirements: 1.1, 1.2, 1.4, 1.6_

  - [x] 3.2 Create Dashboard layout
    - Implement layout with Sidebar and main content area
    - Apply bg-neutral-200 to main content
    - Set up React Query and Auth providers
    - _Requirements: 1.5_

  - [ ]* 3.3 Write property tests for navigation
    - **Property 1: Client-side navigation**
    - **Property 2: Active menu highlighting**
    - **Validates: Requirements 1.3, 1.6**

- [x] 4. Checkpoint - Core infrastructure complete
  - Ensure all tests pass, ask the user if questions arise.

- [x] 5. API client and hooks
  - [x] 5.1 Create API client
    - Implement centralized API client in lib/api.ts
    - Add JWT token handling in Authorization header
    - Implement 401 redirect to login
    - Add typed endpoints for all API calls
    - _Requirements: 13.2, 13.5, 13.6_

  - [x] 5.2 Create useTwin hook
    - Implement twin data fetching with React Query
    - Add updateBlend mutation with optimistic updates
    - Add kill switch activate/deactivate mutations
    - _Requirements: 2.3, 13.4_

  - [x] 5.3 Create useApps hook
    - Implement apps list fetching
    - Add install, configure, disconnect mutations
    - _Requirements: 4.3_

  - [x] 5.4 Create useActivity hook
    - Implement activity list fetching with pagination
    - Add approve/reject mutations
    - _Requirements: 3.6_

  - [x] 5.5 Write property tests for API client

    - **Property 22: JWT token inclusion**
    - **Property 23: Token expiration redirect**
    - **Validates: Requirements 13.5, 13.6**

- [x] 6. Twin Overview components
  - [x] 6.1 Create CognitiveBlendSlider component
    - Implement slider with 0-100 range
    - Add range indicators (AI Logic, Balanced, Human Mimicry)
    - Show warning when blend > 80%
    - Display current percentage value
    - _Requirements: 2.1, 2.2, 2.3, 7.1, 7.2, 7.3_

  - [ ]* 6.2 Write property tests for CognitiveBlendSlider
    - **Property 3: Cognitive blend slider updates**
    - **Property 4: Cognitive blend range indicators**
    - **Property 5: High blend warning display**
    - **Validates: Requirements 2.3, 7.2, 7.3**

  - [x] 6.3 Create KillSwitch component
    - Implement stop/re-enable button with confirmation
    - Add warning styling (red background)
    - Show "Twin Paused" status when active
    - _Requirements: 2.5, 2.6, 7.5, 7.6, 7.7_

  - [ ]* 6.4 Write property tests for KillSwitch
    - **Property 6: Kill switch state display**
    - **Validates: Requirements 7.7**

  - [x] 6.5 Create ActivityStream component
    - Implement chronological list of activities
    - Add status indicators with correct colors
    - Show approve/reject buttons for awaiting_approval
    - Implement infinite scroll/pagination
    - _Requirements: 3.1, 3.2, 3.3, 3.4, 3.5, 3.6, 3.7_

  - [ ]* 6.6 Write property tests for ActivityStream
    - **Property 7: Chronological ordering**
    - **Property 8: Required fields rendering**
    - **Property 9: Status color mapping**
    - **Property 10: Approval buttons visibility**
    - **Validates: Requirements 3.1, 3.2, 3.3, 3.5**

  - [x] 6.7 Create TwinOverview page
    - Compose CognitiveBlendSlider, KillSwitch, ActivityStream
    - Add connected apps count and learning confidence
    - Apply glass panel styling
    - _Requirements: 2.7, 2.8_

- [x] 7. Checkpoint - Twin Overview complete
  - Ensure all tests pass, ask the user if questions arise.

- [x] 8. Apps Marketplace components
  - [x] 8.1 Create AppCard component
    - Display icon, name, description, status badge
    - Show Install or Configure button based on status
    - Add hover animation with elevation
    - Apply glass morphism styling
    - _Requirements: 4.5, 4.7, 4.8, 5.1, 5.2, 5.3, 5.4, 5.5, 5.6, 5.7_

  - [x] 8.2 Write property tests for AppCard

    - **Property 12: Action button by status**
    - **Validates: Requirements 4.7, 4.8, 5.5**

  - [x] 8.3 Create ConfigModal component
    - Implement slide-in modal from right
    - Display app name and icon
    - Add permission toggles (Read, Write, Auto Respond)
    - Add Save and Disconnect buttons
    - Implement close on Escape and outside click
    - _Requirements: 6.1, 6.2, 6.3, 6.4, 6.5, 6.6, 6.7, 6.8, 6.9_

  - [x] 8.4 Write property tests for ConfigModal

    - **Property 13: Modal displays app information**
    - **Property 14: Permission toggle state reflection**
    - **Property 15: Permission toggle local update**
    - **Property 16: Modal close triggers**
    - **Validates: Requirements 6.2, 6.4, 6.5, 6.8**

  - [x] 8.5 Create AppSearch and AppTabs components
    - Implement search bar for filtering
    - Implement tabs: All, Installed, Not Installed
    - _Requirements: 4.1, 4.2_

  - [x] 8.6 Write property tests for tab filtering

    - **Property 11: Tab filtering**
    - **Validates: Requirements 4.3**

  - [x] 8.7 Create Apps Marketplace page
    - Compose AppSearch, AppTabs, AppGrid with AppCards
    - Wire up ConfigModal for installed apps
    - Handle install flow
    - _Requirements: 4.4_

- [x] 9. Checkpoint - Apps Marketplace complete
  - Ensure all tests pass, ask the user if questions arise.

- [x] 10. Memory Panel
  - [x] 10.1 Create useMemory hook
    - Implement memory list fetching with search
    - Add memory detail fetching
    - _Requirements: 8.5_

  - [x] 10.2 Create PersonalityProfile component
    - Display CSM personality summary
    - Show personality traits and tone preferences
    - _Requirements: 8.1_

  - [x] 10.3 Create MemoryList and MemoryEntry components
    - Display learning events chronologically
    - Show event type, timestamp, description
    - Add view details functionality
    - _Requirements: 8.2, 8.3, 8.4_

  - [x] 10.4 Create Memory Panel page
    - Compose PersonalityProfile, MemoryList
    - Add search/filter functionality
    - Apply glass panel styling
    - _Requirements: 8.5, 8.6_

- [x] 11. Voice Panel
  - [x] 11.1 Create useVoice hook
    - Implement voice profile fetching
    - Implement call history fetching
    - Add approve session and terminate call mutations
    - _Requirements: 9.3, 9.5_

  - [x] 11.2 Create VoiceStatus component
    - Display phone number or "not provisioned" message
    - Show approval status and expiration
    - Add "Approve Voice Session" button when not approved
    - _Requirements: 9.1, 9.4, 9.5_

  - [ ]* 11.3 Write property tests for VoiceStatus
    - **Property 17: Phone number conditional display**
    - **Property 18: Voice approval button visibility**
    - **Validates: Requirements 9.1, 9.5**

  - [x] 11.4 Create CallHistory component
    - Display call records with direction, number, duration, timestamp
    - _Requirements: 9.2_

  - [x] 11.5 Create VoiceKillSwitch component
    - Implement terminate active call functionality
    - _Requirements: 9.3_

  - [x] 11.6 Create Voice Panel page
    - Compose VoiceStatus, CallHistory, VoiceKillSwitch
    - Apply glass panel styling
    - _Requirements: 9.6_

- [x] 12. Security Panel
  - [x] 12.1 Create useAudit hook
    - Implement audit log fetching with filters
    - Implement permissions fetching and updating
    - _Requirements: 10.2_

  - [x] 12.2 Create AuditLog component
    - Display audit entries with timestamp, action, target, outcome
    - Implement filtering by date range, action type, integration
    - Add search functionality
    - _Requirements: 10.1, 10.2, 10.3_

  - [ ]* 12.3 Write property tests for AuditLog
    - **Property 19: Audit log filtering**
    - **Validates: Requirements 10.2**

  - [x] 12.4 Create PermissionGrid component
    - Display per-app permission summaries
    - _Requirements: 10.4_

  - [x] 12.5 Create DataExport component
    - Implement data export option
    - _Requirements: 10.5_

  - [x] 12.6 Create Security Panel page
    - Compose AuditLog, PermissionGrid, DataExport
    - Display global kill switch status
    - Apply glass panel styling
    - _Requirements: 10.6, 10.7_

- [x] 13. Checkpoint - Memory, Voice, Security complete
  - Ensure all tests pass, ask the user if questions arise.

- [x] 14. Settings Panel
  - [x] 14.1 Create useSubscription hook
    - Implement subscription fetching
    - Add upgrade mutation
    - _Requirements: 11.2_

  - [x] 14.2 Create Settings Panel page
    - Display user profile information
    - Display subscription tier with upgrade options
    - Implement Twin model selection based on tier
    - Add notification preferences
    - Add data retention settings
    - Apply glass panel styling
    - _Requirements: 11.1, 11.2, 11.3, 11.4, 11.5, 11.6_

  - [x] 14.3 Write property tests for model selection

    - **Property 20: Model selection by subscription tier**
    - **Validates: Requirements 11.3**

- [x] 15. State management and error handling
  - [x] 15.1 Create loading, error, and empty state components
    - Implement LoadingState component
    - Implement EmptyState component
    - Implement ErrorBoundary component
    - _Requirements: 13.3_

  - [x] 15.2 Write property tests for state handling

    - **Property 21: Loading, error, and empty states**
    - **Validates: Requirements 13.3**

  - [x] 15.3 Implement error handling in API client
    - Handle network failures with retry
    - Handle 401 with redirect
    - Handle validation errors with field messages
    - _Requirements: 13.6_

- [x] 16. Accessibility implementation
  - [x] 16.1 Add keyboard accessibility to all interactive elements
    - Ensure Tab navigation works
    - Ensure Enter/Space activation works
    - _Requirements: 14.1_

  - [x] 16.2 Add ARIA labels to icon-only buttons
    - Audit all icon buttons
    - Add descriptive aria-label attributes
    - _Requirements: 14.2_

  - [x] 16.3 Implement semantic HTML structure
    - Use nav, main, section, button elements appropriately
    - _Requirements: 14.3_

  - [x] 16.4 Verify focus states
    - Ensure purple-600 focus ring on all interactive elements
    - _Requirements: 14.6_

  - [ ]* 16.5 Write property tests for accessibility
    - **Property 24: Keyboard accessibility**
    - **Property 25: ARIA labels for icon buttons**
    - **Property 26: WCAG AA color contrast**
    - **Property 27: Visible focus states**
    - **Validates: Requirements 14.1, 14.2, 14.4, 14.6**

- [x] 17. Animations and polish
  - [x] 17.1 Add page transition animations
    - Implement content transitions between pages
    - _Requirements: 15.4_

  - [x] 17.2 Add modal animations
    - Implement slide and fade for modals
    - _Requirements: 15.5_

  - [x] 17.3 Add hover animations
    - Implement scale/elevation on interactive elements
    - _Requirements: 15.6_

  - [x] 17.4 Implement responsive sidebar
    - Collapse to icons-only on smaller screens
    - _Requirements: 1.7_

- [x] 18. Final checkpoint - All features complete
  - Ensure all tests pass, ask the user if questions arise.
  - Verify all 28 correctness properties are covered by tests.

## Notes

- Tasks marked with `*` are optional and can be skipped for faster MVP
- Each task references specific requirements for traceability
- Checkpoints ensure incremental validation
- Property tests validate universal correctness properties
- Unit tests validate specific examples and edge cases
- Use fast-check for all property-based tests with minimum 100 iterations
