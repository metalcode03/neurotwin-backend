# Requirements Document

## Introduction

This feature modernizes the Django admin panel for the NeuroTwin platform. The default Django admin interface will be replaced with a polished, branded experience using a Django admin beautifier package (django-unfold). Custom branding, the NeuroTwin logo, analytics dashboards with charts, and a cohesive modern look across all admin pages will be implemented. The scope covers all 11 registered apps: authentication, subscription, credits, csm, twin, memory, learning, safety, automation, voice, and core.

## Glossary

- **Admin_Panel**: The Django admin interface accessible at `/admin/`, used by platform administrators to manage NeuroTwin data and monitor platform activity.
- **Admin_Theme**: The django-unfold package that provides a modern, responsive admin UI layer on top of Django's built-in admin framework.
- **Admin_Dashboard**: The landing page of the Admin_Panel that displays summary statistics and charts for key platform metrics.
- **Branding_Header**: The top navigation bar of the Admin_Panel displaying the platform name and logo.
- **Analytics_Widget**: A visual component on the Admin_Dashboard that renders a chart or summary statistic for a specific platform metric.
- **Sidebar_Navigation**: The left-hand navigation menu in the Admin_Panel that organizes registered models into logical groups.
- **Admin_User**: A Django user with `is_staff=True` who has access to the Admin_Panel.

## Requirements

### Requirement 1: Admin Theme Integration

**User Story:** As an Admin_User, I want the Admin_Panel to use a modern UI theme, so that the interface feels polished and professional.

#### Acceptance Criteria

1. THE Admin_Theme SHALL replace the default Django admin styling with the django-unfold theme across all Admin_Panel pages.
2. WHEN an Admin_User navigates to any page in the Admin_Panel, THE Admin_Theme SHALL render a responsive layout that adapts to desktop and tablet screen widths.
3. THE Admin_Theme SHALL apply consistent styling to all model list views, detail views, and form views across all 11 registered apps.
4. WHEN the Admin_Theme is installed, THE Admin_Panel SHALL retain all existing model registrations and admin functionality without modification to business logic.

### Requirement 2: Custom Branding

**User Story:** As an Admin_User, I want the Admin_Panel to display NeuroTwin branding, so that the interface reflects the platform identity.

#### Acceptance Criteria

1. THE Branding_Header SHALL display "NeuroTwin AI Admin" as the site title instead of the default "Django administration" text.
2. THE Branding_Header SHALL display the NeuroTwin logo image in the header area alongside the site title.
3. WHEN an Admin_User views the browser tab, THE Admin_Panel SHALL display "NeuroTwin AI Admin" as the browser tab title.
4. THE Branding_Header SHALL display "NeuroTwin" as the site header text visible on the login page and throughout the Admin_Panel.

### Requirement 3: Sidebar Navigation Organization

**User Story:** As an Admin_User, I want the sidebar navigation to group models logically, so that I can find and manage platform data efficiently.

#### Acceptance Criteria

1. THE Sidebar_Navigation SHALL group registered models into logical categories: "Users & Auth" (User, VerificationToken, PasswordResetToken), "Subscriptions & Billing" (Subscription, SubscriptionHistory, PaymentTransaction, WebhookLog, CreditTopUp), "AI & Credits" (UserCredits, CreditUsageLog, AIRequestLog, BrainRoutingConfig), "Twin & Cognition" (Twin, OnboardingProgress, CSMProfile, CSMChangeLog), "Memory & Learning" (MemoryRecord, MemoryAccessLog, LearningEvent), "Safety & Audit" (PermissionScope, PermissionHistory, AuditLog), "Automation" (all automation models), and "Voice" (VoiceProfile, CallRecord, VoiceApprovalHistory).
2. WHEN an Admin_User expands a sidebar group, THE Sidebar_Navigation SHALL display all models belonging to that group.
3. THE Sidebar_Navigation SHALL use distinct icons for each group to provide visual differentiation.

### Requirement 4: Admin Dashboard with Analytics

**User Story:** As an Admin_User, I want to see key platform metrics on the admin landing page, so that I can monitor platform health at a glance.

#### Acceptance Criteria

1. WHEN an Admin_User navigates to the Admin_Dashboard, THE Admin_Dashboard SHALL display summary statistics including total users, active subscriptions, total credits consumed, and total AI requests.
2. WHEN an Admin_User views the Admin_Dashboard, THE Admin_Dashboard SHALL render a line chart showing AI request volume over the last 30 days.
3. WHEN an Admin_User views the Admin_Dashboard, THE Admin_Dashboard SHALL render a bar chart showing credit consumption grouped by brain mode.
4. WHEN an Admin_User views the Admin_Dashboard, THE Admin_Dashboard SHALL render a pie chart showing the distribution of subscription tiers across active users.
5. WHEN an Admin_User views the Admin_Dashboard, THE Admin_Dashboard SHALL render a line chart showing new user registrations over the last 30 days.
6. THE Admin_Dashboard SHALL load all Analytics_Widgets using data queried from the database at page load time.
7. IF the database query for an Analytics_Widget fails, THEN THE Admin_Dashboard SHALL display a fallback message indicating the data is temporarily unavailable instead of rendering a broken chart.

### Requirement 5: Enhanced Model List Views

**User Story:** As an Admin_User, I want model list views to look modern and be easy to scan, so that I can manage records efficiently.

#### Acceptance Criteria

1. THE Admin_Panel SHALL display colored status badges for status fields (e.g., subscription status, payment status, AI request status) instead of plain text values.
2. THE Admin_Panel SHALL display user-friendly formatted values for credit amounts, timestamps, and monetary values in all list views.
3. WHEN an Admin_User views a model list, THE Admin_Panel SHALL provide functional search, filter, and ordering controls styled consistently with the Admin_Theme.

### Requirement 6: Admin Login Page Branding

**User Story:** As an Admin_User, I want the login page to reflect NeuroTwin branding, so that the experience is consistent from the first interaction.

#### Acceptance Criteria

1. WHEN an unauthenticated user navigates to the Admin_Panel login page, THE Admin_Panel SHALL display the NeuroTwin logo above the login form.
2. WHEN an unauthenticated user views the login page, THE Admin_Panel SHALL display "NeuroTwin AI Admin" as the page heading.
3. THE Admin_Panel login page SHALL use the Admin_Theme styling for the login form, including input fields and the submit button.

### Requirement 7: Dark Mode Support

**User Story:** As an Admin_User, I want to use the admin panel in dark mode, so that I can work comfortably in low-light environments.

#### Acceptance Criteria

1. THE Admin_Panel SHALL support a dark color scheme as an alternative to the default light theme.
2. WHEN an Admin_User toggles the theme preference, THE Admin_Panel SHALL switch between light and dark modes without requiring a page reload.
3. THE Admin_Panel SHALL persist the Admin_User's theme preference across browser sessions.
