# Requirements Document

## Introduction

The NeuroTwin Dashboard Frontend is the authenticated web interface for the NeuroTwin cognitive digital twin platform. Built with Next.js 14+ App Router, TailwindCSS, and Framer Motion, this dashboard provides users with a cognitive command center to manage their Twin, connected apps, automations, memory, voice capabilities, and safety controls. This is the authenticated dashboard UI only — no landing pages or public marketing content.

## Glossary

- **Dashboard**: The authenticated web interface for managing the NeuroTwin platform
- **Sidebar**: Fixed left navigation panel with icon-based menu items
- **Glass_Panel**: UI component with backdrop blur and semi-transparent background for cognitive OS aesthetic
- **Twin_Overview**: Main dashboard panel showing Twin status, Cognitive Blend, and quick actions
- **Cognitive_Blend_Slider**: Interactive slider (0-100%) controlling human vs AI logic balance
- **Kill_Switch**: Emergency button to halt all Twin automations immediately
- **Activity_Stream**: Real-time feed showing Twin actions and their status
- **Apps_Marketplace**: Interface for browsing, installing, and configuring integrations
- **App_Card**: UI component displaying integration information and actions
- **Configuration_Modal**: Slide-out panel for configuring app permissions
- **Audit_Log_Panel**: Interface displaying timestamped Twin actions for transparency

## Requirements

### Requirement 1: Dashboard Layout and Navigation

**User Story:** As an authenticated user, I want a consistent dashboard layout with sidebar navigation, so that I can easily access all Twin management features.

#### Acceptance Criteria

1. THE Dashboard SHALL display a fixed sidebar on the left with navigation icons using react-icons
2. THE Sidebar SHALL include menu items: Twin (FaBrain), Chat (FaComments), Apps (FaPuzzlePiece), Automation (FaSyncAlt), Memory (FaDatabase), Voice (FaMicrophone), Security (FaShieldAlt), Settings (FaCog)
3. WHEN a user clicks a sidebar menu item, THE Dashboard SHALL navigate to the corresponding page without full page refresh
4. THE Sidebar SHALL use bg-neutral-800 background with white text for the dark theme
5. THE Main_Content_Area SHALL use bg-neutral-200 background
6. WHEN a menu item is active, THE Sidebar SHALL highlight it with purple-700 accent color
7. THE Dashboard SHALL be responsive and collapse the sidebar to icons-only on smaller screens

### Requirement 2: Twin Overview Panel

**User Story:** As a user, I want to see my Twin's status and key controls at a glance, so that I can quickly understand and manage my Twin's behavior.

#### Acceptance Criteria

1. THE Twin_Overview SHALL display the current Cognitive_Blend percentage value prominently
2. THE Twin_Overview SHALL include an interactive Cognitive_Blend_Slider (0-100%)
3. WHEN a user adjusts the Cognitive_Blend_Slider, THE System SHALL update the value via API and reflect the change immediately
4. THE Twin_Overview SHALL display an Autonomy toggle switch
5. THE Twin_Overview SHALL display a prominent Kill_Switch button with warning styling
6. WHEN a user clicks the Kill_Switch, THE System SHALL call the API to halt all automations and show confirmation
7. THE Twin_Overview SHALL display connected apps count and learning confidence metrics
8. THE Twin_Overview SHALL apply glass morphism styling (bg-white/70 backdrop-blur-xl border border-neutral-400/40)

### Requirement 3: Activity Stream

**User Story:** As a user, I want to see a live feed of my Twin's actions, so that I can monitor what it's doing on my behalf.

#### Acceptance Criteria

1. THE Activity_Stream SHALL display a chronological list of Twin actions
2. EACH activity item SHALL show: action type, target integration, timestamp, and status
3. THE Activity_Stream SHALL display status indicators: success (green), pending (yellow), failed (red), waiting for approval (orange)
4. WHEN a new action occurs, THE Activity_Stream SHALL update in real-time without page refresh
5. WHEN an action requires approval, THE Activity_Stream SHALL show approve/reject buttons
6. THE Activity_Stream SHALL support infinite scroll or pagination for historical actions
7. THE Activity_Stream SHALL apply glass panel styling

### Requirement 4: Apps Marketplace

**User Story:** As a user, I want to browse and install integrations for my Twin, so that it can act across my digital ecosystem.

#### Acceptance Criteria

1. THE Apps_Marketplace SHALL display a search bar for filtering apps
2. THE Apps_Marketplace SHALL display tabs: All, Installed, Not Installed
3. WHEN a user selects a tab, THE Apps_Marketplace SHALL filter the displayed apps accordingly
4. THE Apps_Marketplace SHALL display apps as App_Cards in a grid layout
5. EACH App_Card SHALL show: icon (react-icons), name, description, status badge
6. THE Status_Badge SHALL display: "Installed" (green), "Not Installed" (gray), or "Needs Attention" (orange)
7. WHEN an app is not installed, THE App_Card SHALL show an "Install" button
8. WHEN an app is installed, THE App_Card SHALL show a "Configure" button

### Requirement 5: App Card Component

**User Story:** As a user, I want clear visual information about each integration, so that I can make informed decisions about which apps to connect.

#### Acceptance Criteria

1. THE App_Card SHALL display the app icon using react-icons library
2. THE App_Card SHALL display the app name in neutral-800 text
3. THE App_Card SHALL display a short description in neutral-600 text
4. THE App_Card SHALL display a status badge with appropriate color coding
5. THE App_Card SHALL display an action button (Install or Configure) styled with btn-primary or btn-outline
6. WHEN a user hovers over an App_Card, THE Card SHALL show subtle elevation animation
7. THE App_Card SHALL apply glass morphism styling

### Requirement 6: App Configuration Modal

**User Story:** As a user, I want to configure permissions for installed apps, so that I can control what my Twin can do with each integration.

#### Acceptance Criteria

1. WHEN a user clicks Configure on an App_Card, THE Configuration_Modal SHALL slide in from the right side
2. THE Configuration_Modal SHALL display the app name and icon at the top
3. THE Configuration_Modal SHALL display permission toggles: Read, Write, Auto Respond
4. EACH permission toggle SHALL show its current state (enabled/disabled)
5. WHEN a user toggles a permission, THE System SHALL update the state locally
6. THE Configuration_Modal SHALL display a "Save" button (btn-primary) to persist changes
7. THE Configuration_Modal SHALL display a "Disconnect" button (btn-outline with warning color) to uninstall
8. WHEN a user clicks outside the modal or presses Escape, THE Modal SHALL close
9. THE Configuration_Modal SHALL animate with Framer Motion (slide from right, duration < 300ms)

### Requirement 7: Cognitive Control Panel

**User Story:** As a user, I want dedicated controls for my Twin's cognitive settings, so that I can fine-tune how it behaves.

#### Acceptance Criteria

1. THE Cognitive_Control_Panel SHALL display the Cognitive_Blend_Slider with current percentage
2. THE Cognitive_Blend_Slider SHALL show visual indicators for behavior ranges: 0-30% (AI Logic), 31-70% (Balanced), 71-100% (Human Mimicry)
3. WHEN Cognitive_Blend exceeds 80%, THE Panel SHALL display a warning that actions require confirmation
4. THE Cognitive_Control_Panel SHALL display an Autonomy toggle with clear on/off states
5. THE Cognitive_Control_Panel SHALL display the Kill_Switch button prominently
6. THE Kill_Switch SHALL have distinct warning styling (red background, white text)
7. WHEN Kill_Switch is active, THE Panel SHALL show "Twin Paused" status with re-enable option

### Requirement 8: Memory Panel

**User Story:** As a user, I want to view and manage my Twin's memory, so that I can understand what it has learned and correct any issues.

#### Acceptance Criteria

1. THE Memory_Panel SHALL display personality profile summary from CSM
2. THE Memory_Panel SHALL display recent learning events in chronological order
3. EACH learning event SHALL show: event type, timestamp, and brief description
4. THE Memory_Panel SHALL allow users to view memory entry details
5. THE Memory_Panel SHALL provide search/filter functionality for memories
6. THE Memory_Panel SHALL apply glass panel styling

### Requirement 9: Voice Twin Panel

**User Story:** As a Twin+ or Executive user, I want to manage my Voice Twin settings, so that I can control phone-based interactions.

#### Acceptance Criteria

1. THE Voice_Panel SHALL display the assigned phone number (if provisioned)
2. THE Voice_Panel SHALL display call history with: direction, phone number, duration, timestamp
3. THE Voice_Panel SHALL display a Voice Kill_Switch to terminate active calls
4. THE Voice_Panel SHALL display voice approval status and expiration
5. IF voice is not approved, THE Panel SHALL show an "Approve Voice Session" button
6. THE Voice_Panel SHALL apply glass panel styling

### Requirement 10: Security Panel

**User Story:** As a user, I want to review my Twin's actions and manage permissions, so that I can maintain trust and control.

#### Acceptance Criteria

1. THE Security_Panel SHALL display audit logs with: timestamp, action type, target, outcome
2. THE Audit_Log SHALL support filtering by date range, action type, and integration
3. THE Audit_Log SHALL support search functionality
4. THE Security_Panel SHALL display per-app permission summaries
5. THE Security_Panel SHALL provide a data export option
6. THE Security_Panel SHALL display the global Kill_Switch status
7. THE Security_Panel SHALL apply glass panel styling

### Requirement 11: Settings Panel

**User Story:** As a user, I want to manage my account and Twin preferences, so that I can customize my experience.

#### Acceptance Criteria

1. THE Settings_Panel SHALL display user profile information
2. THE Settings_Panel SHALL display current subscription tier and upgrade options
3. THE Settings_Panel SHALL provide Twin model selection (based on subscription tier)
4. THE Settings_Panel SHALL provide notification preferences
5. THE Settings_Panel SHALL provide data retention settings
6. THE Settings_Panel SHALL apply glass panel styling

### Requirement 12: Design System Implementation

**User Story:** As a developer, I want consistent design tokens and components, so that the UI maintains visual coherence.

#### Acceptance Criteria

1. THE Tailwind_Config SHALL extend colors with the NeuroTwin palette (purple-100 through purple-700, neutral-200 through neutral-800)
2. THE System SHALL provide a .glass utility class for glass morphism effect
3. THE System SHALL provide .btn-primary class (bg-purple-700 text-white hover:bg-purple-600)
4. THE System SHALL provide .btn-outline class (border border-neutral-400 hover:bg-purple-100)
5. ALL cards and modals SHALL use rounded-xl border radius
6. ALL buttons and inputs SHALL use rounded-lg border radius
7. THE System SHALL use Framer Motion for all enter/exit animations with duration < 300ms

### Requirement 13: State Management and API Integration

**User Story:** As a developer, I want organized state management and API integration, so that data flows predictably through the application.

#### Acceptance Criteria

1. THE System SHALL use React Query or SWR for server state management
2. THE API_Client SHALL be centralized in lib/api.ts with typed endpoints
3. ALL data displays SHALL handle loading, error, and empty states
4. WHEN a user initiates an action, THE System SHALL provide optimistic updates where appropriate
5. THE System SHALL store JWT tokens securely and include them in API requests
6. WHEN a token expires, THE System SHALL redirect to login

### Requirement 14: Accessibility

**User Story:** As a user with accessibility needs, I want the dashboard to be fully accessible, so that I can use all features effectively.

#### Acceptance Criteria

1. ALL interactive elements SHALL be keyboard accessible
2. ALL icon-only buttons SHALL have ARIA labels
3. THE System SHALL use semantic HTML elements (nav, main, section, button)
4. ALL color combinations SHALL meet WCAG AA contrast requirements
5. THE System SHALL support screen reader navigation
6. Focus states SHALL be clearly visible with purple-600 ring

### Requirement 15: Animations and Transitions

**User Story:** As a user, I want smooth animations that enhance the experience, so that the interface feels polished and responsive.

#### Acceptance Criteria

1. THE System SHALL use Framer Motion for component animations
2. ALL transitions SHALL complete in under 300ms
3. THE System SHALL prefer spring animations over tween for natural feel
4. WHEN navigating between pages, THE System SHALL animate content transitions
5. WHEN modals open/close, THE System SHALL animate with slide and fade effects
6. WHEN hovering interactive elements, THE System SHALL show subtle scale or elevation changes
