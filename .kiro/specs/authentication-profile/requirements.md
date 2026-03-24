# Requirements Document

## Introduction

The Authentication and Profile Management feature provides secure user authentication and profile management for the NeuroTwin frontend application. Built with Next.js 14+ App Router, this feature integrates with the existing Django backend authentication API to enable email/password registration, Google OAuth, JWT token management, password reset flows, and user profile editing. The UI follows the established glass morphism design system with the NeuroTwin purple color palette.

## Glossary

- **Auth_System**: The frontend authentication system that manages user sessions and tokens
- **Login_Page**: The `/auth/login` route where users authenticate with email/password or Google OAuth
- **Signup_Page**: The `/auth/signup` route where users create new accounts
- **Auth_Guard**: Middleware that protects dashboard routes from unauthenticated access
- **JWT_Token**: JSON Web Token used for authenticating API requests (access + refresh tokens)
- **Token_Refresh**: Process of obtaining a new access token using a refresh token
- **Profile_Settings_Page**: The `/dashboard/settings/profile` route where users manage their profile
- **Profile_Image**: User's avatar image stored on the backend
- **Password_Reset_Flow**: Multi-step process for users to reset forgotten passwords via email
- **OAuth_Provider**: Third-party authentication service (Google) used for sign-in
- **Glass_Card**: UI component with glass morphism styling (backdrop-blur, semi-transparent)
- **Form_Validation**: Client-side validation of user input before submission

## Requirements

### Requirement 1: Login Page

**User Story:** As a user, I want to log in with my email and password or Google account, so that I can access my NeuroTwin dashboard.

#### Acceptance Criteria

1. THE Login_Page SHALL display a Glass_Card with email and password input fields
2. THE Login_Page SHALL display a "Sign in with Google" button with Google branding
3. THE Login_Page SHALL display a "Forgot password?" link that navigates to password reset
4. THE Login_Page SHALL display a "Remember me" checkbox
5. WHEN a user submits valid credentials, THE Auth_System SHALL call POST /api/v1/auth/login and store JWT tokens
6. WHEN login succeeds, THE Auth_System SHALL redirect the user to /dashboard/twin
7. WHEN login fails, THE Login_Page SHALL display an error message inline
8. THE Login_Page SHALL display a loading spinner during authentication
9. THE Login_Page SHALL include a password visibility toggle icon
10. WHEN an authenticated user visits the Login_Page, THE Auth_System SHALL redirect them to /dashboard/twin
11. THE Login_Page SHALL display a link to the Signup_Page

### Requirement 2: Signup Page

**User Story:** As a new user, I want to create an account with email/password or Google, so that I can start using NeuroTwin.

#### Acceptance Criteria

1. THE Signup_Page SHALL display a Glass_Card with email, password, username, and display name input fields
2. THE Signup_Page SHALL display a "Sign up with Google" button with Google branding
3. THE Signup_Page SHALL display a Terms of Service acceptance checkbox
4. THE Signup_Page SHALL validate that the Terms checkbox is checked before allowing submission
5. WHEN a user submits valid registration data, THE Auth_System SHALL call POST /api/v1/auth/register
6. WHEN registration succeeds, THE Signup_Page SHALL display a message to check email for verification
7. WHEN registration fails, THE Signup_Page SHALL display validation errors inline below each field
8. THE Signup_Page SHALL validate password strength (minimum 8 characters)
9. THE Signup_Page SHALL include a password visibility toggle icon
10. THE Signup_Page SHALL display a loading spinner during registration
11. WHEN an authenticated user visits the Signup_Page, THE Auth_System SHALL redirect them to /dashboard/twin
12. THE Signup_Page SHALL display a link to the Login_Page

### Requirement 3: Google OAuth Integration

**User Story:** As a user, I want to sign in with my Google account, so that I can access NeuroTwin without creating a separate password.

#### Acceptance Criteria

1. WHEN a user clicks "Sign in with Google" on Login_Page, THE Auth_System SHALL initiate Google OAuth flow
2. WHEN a user clicks "Sign up with Google" on Signup_Page, THE Auth_System SHALL initiate Google OAuth flow
3. WHEN Google OAuth succeeds, THE Auth_System SHALL call POST /api/v1/auth/oauth/google/callback with the authorization code
4. WHEN OAuth callback succeeds, THE Auth_System SHALL store JWT tokens and redirect to /dashboard/twin
5. WHEN OAuth callback fails, THE Auth_System SHALL display an error message and return to the auth page
6. THE Auth_System SHALL handle OAuth errors gracefully (user cancellation, network errors)

### Requirement 4: Authentication Guard

**User Story:** As a system, I want to protect dashboard routes from unauthenticated access, so that only logged-in users can access their Twin.

#### Acceptance Criteria

1. THE Auth_Guard SHALL protect all routes matching /dashboard/*
2. WHEN an unauthenticated user attempts to access a protected route, THE Auth_Guard SHALL redirect to /auth/login
3. THE Auth_Guard SHALL store the attempted URL and redirect back after successful login
4. THE Auth_Guard SHALL verify JWT token validity before allowing access
5. WHEN a JWT access token expires, THE Auth_Guard SHALL attempt to refresh it using the refresh token
6. WHEN token refresh succeeds, THE Auth_Guard SHALL update stored tokens and allow access
7. WHEN token refresh fails, THE Auth_Guard SHALL redirect to /auth/login and clear stored tokens
8. THE Auth_System SHALL store JWT tokens in httpOnly cookies or secure localStorage

### Requirement 5: Token Management

**User Story:** As a system, I want to automatically refresh expired access tokens, so that users maintain seamless access without repeated logins.

#### Acceptance Criteria

1. THE Auth_System SHALL store both access_token and refresh_token after successful authentication
2. WHEN an API request returns 401 Unauthorized, THE Auth_System SHALL attempt token refresh
3. THE Auth_System SHALL call POST /api/v1/auth/refresh with the refresh_token
4. WHEN refresh succeeds, THE Auth_System SHALL update the stored access_token and retry the original request
5. WHEN refresh fails, THE Auth_System SHALL clear all tokens and redirect to /auth/login
6. THE Auth_System SHALL include the access_token in the Authorization header for all API requests
7. THE Auth_System SHALL handle concurrent token refresh requests to avoid race conditions

### Requirement 6: Password Reset Flow

**User Story:** As a user who forgot my password, I want to reset it via email, so that I can regain access to my account.

#### Acceptance Criteria

1. WHEN a user clicks "Forgot password?" on Login_Page, THE Auth_System SHALL navigate to /auth/forgot-password
2. THE Forgot_Password_Page SHALL display a Glass_Card with an email input field
3. WHEN a user submits an email, THE Auth_System SHALL call POST /api/v1/auth/password-reset
4. THE Forgot_Password_Page SHALL display a message that an email has been sent (regardless of whether account exists)
5. THE Auth_System SHALL provide a /auth/reset-password route that accepts a token query parameter
6. THE Reset_Password_Page SHALL display a Glass_Card with new password and confirm password fields
7. WHEN a user submits a new password, THE Auth_System SHALL call POST /api/v1/auth/password-reset/confirm with the token
8. WHEN password reset succeeds, THE Reset_Password_Page SHALL display success message and redirect to /auth/login
9. WHEN password reset fails, THE Reset_Password_Page SHALL display an error message (invalid/expired token)

### Requirement 7: Profile Settings Page

**User Story:** As a user, I want to view and edit my profile information, so that I can keep my account details current.

#### Acceptance Criteria

1. THE Profile_Settings_Page SHALL display a Glass_Card with user profile information
2. THE Profile_Settings_Page SHALL display editable fields: username, display name, bio/description
3. THE Profile_Settings_Page SHALL display email as read-only text
4. THE Profile_Settings_Page SHALL display the current Profile_Image with a circular avatar
5. THE Profile_Settings_Page SHALL display account creation date as read-only text
6. WHEN a user clicks "Save Changes", THE Auth_System SHALL call PUT /api/v1/users/profile with updated data
7. WHEN profile update succeeds, THE Profile_Settings_Page SHALL display a success message
8. WHEN profile update fails, THE Profile_Settings_Page SHALL display validation errors inline
9. THE Profile_Settings_Page SHALL display a loading spinner during save operation

### Requirement 8: Profile Image Upload

**User Story:** As a user, I want to upload a profile picture, so that my account is personalized and recognizable.

#### Acceptance Criteria

1. THE Profile_Settings_Page SHALL display an "Upload Image" button or clickable avatar area
2. WHEN a user clicks the upload area, THE Auth_System SHALL open a file picker dialog
3. THE Auth_System SHALL accept only JPEG and PNG image files
4. WHEN a user selects an image larger than 5MB, THE Auth_System SHALL display an error message
5. WHEN a user selects a valid image, THE Profile_Settings_Page SHALL display a preview of the image
6. THE Profile_Settings_Page SHALL display "Save" and "Cancel" buttons for the image upload
7. WHEN a user clicks "Save", THE Auth_System SHALL call POST /api/v1/users/profile/image with the image file
8. WHEN image upload succeeds, THE Profile_Settings_Page SHALL update the displayed Profile_Image
9. WHEN image upload fails, THE Profile_Settings_Page SHALL display an error message

### Requirement 9: Password Change

**User Story:** As a logged-in user, I want to change my password from settings, so that I can maintain account security.

#### Acceptance Criteria

1. THE Profile_Settings_Page SHALL display a "Change Password" section or button
2. WHEN a user clicks "Change Password", THE Auth_System SHALL display a modal or expand a section
3. THE Password_Change_Form SHALL display fields: current password, new password, confirm new password
4. THE Password_Change_Form SHALL validate that new password is at least 8 characters
5. THE Password_Change_Form SHALL validate that new password and confirm password match
6. WHEN a user submits the form, THE Auth_System SHALL call POST /api/v1/users/change-password
7. WHEN password change succeeds, THE Auth_System SHALL display a success message
8. WHEN password change fails, THE Auth_System SHALL display an error message (incorrect current password)

### Requirement 10: User Profile Display in Dashboard

**User Story:** As a user, I want to see my profile information in the dashboard, so that I know which account I'm using.

#### Acceptance Criteria

1. THE Dashboard_Sidebar SHALL display the user's Profile_Image as a circular avatar
2. THE Dashboard_Sidebar SHALL display the user's display name or username
3. WHEN a user clicks the profile avatar, THE Auth_System SHALL navigate to /dashboard/settings/profile
4. THE Dashboard_Header SHALL display the user's email in a dropdown menu or settings area
5. THE Dashboard SHALL display account status (verified/unverified) if applicable

### Requirement 11: Logout Functionality

**User Story:** As a user, I want to log out of my account, so that I can secure my session when finished.

#### Acceptance Criteria

1. THE Dashboard SHALL display a "Logout" button in the sidebar or user menu
2. WHEN a user clicks "Logout", THE Auth_System SHALL call POST /api/v1/auth/logout with the refresh_token
3. WHEN logout succeeds, THE Auth_System SHALL clear all stored tokens
4. WHEN logout completes, THE Auth_System SHALL redirect to /auth/login
5. THE Auth_System SHALL handle logout failures gracefully by clearing tokens locally

### Requirement 12: Form Validation

**User Story:** As a user, I want immediate feedback on form errors, so that I can correct issues before submission.

#### Acceptance Criteria

1. ALL auth forms SHALL use React Hook Form for form state management
2. ALL auth forms SHALL use Zod schemas for validation rules
3. WHEN a user leaves a required field empty, THE Form SHALL display "This field is required" error
4. WHEN a user enters an invalid email, THE Form SHALL display "Please enter a valid email address" error
5. WHEN a user enters a password shorter than 8 characters, THE Form SHALL display "Password must be at least 8 characters" error
6. THE Form SHALL display validation errors below the corresponding input field
7. THE Form SHALL disable the submit button while validation errors exist
8. THE Form SHALL display validation errors in red text (error state)

### Requirement 13: Loading and Error States

**User Story:** As a user, I want clear feedback during operations, so that I understand what's happening.

#### Acceptance Criteria

1. WHEN a form is submitting, THE Auth_System SHALL display a loading spinner on the submit button
2. WHEN a form is submitting, THE Auth_System SHALL disable all form inputs
3. WHEN an API request fails, THE Auth_System SHALL display an error message in a toast or alert
4. WHEN a network error occurs, THE Auth_System SHALL display "Network error. Please try again." message
5. WHEN a server error occurs, THE Auth_System SHALL display "Something went wrong. Please try again later." message
6. THE Auth_System SHALL clear error messages when the user starts typing in a field

### Requirement 14: Responsive Design

**User Story:** As a mobile user, I want the auth pages to work on my device, so that I can access NeuroTwin anywhere.

#### Acceptance Criteria

1. THE Login_Page and Signup_Page SHALL be fully responsive on mobile, tablet, and desktop
2. THE Glass_Card SHALL adjust width based on screen size (max-w-md on mobile, max-w-lg on desktop)
3. THE Form inputs SHALL be touch-friendly with minimum 44px height on mobile
4. THE Auth pages SHALL use a single-column layout on mobile devices
5. THE Profile_Settings_Page SHALL stack sections vertically on mobile devices

### Requirement 15: Accessibility

**User Story:** As a user with accessibility needs, I want the auth system to be fully accessible, so that I can use all features.

#### Acceptance Criteria

1. ALL form inputs SHALL have associated labels with htmlFor attributes
2. ALL form validation errors SHALL be announced to screen readers
3. THE Password visibility toggle SHALL have an ARIA label
4. ALL buttons SHALL be keyboard accessible
5. THE Auth pages SHALL use semantic HTML elements (form, label, button)
6. ALL color combinations SHALL meet WCAG AA contrast requirements
7. Focus states SHALL be clearly visible with purple-600 ring

### Requirement 16: Design System Consistency

**User Story:** As a user, I want the auth pages to match the dashboard aesthetic, so that the experience feels cohesive.

#### Acceptance Criteria

1. THE Auth pages SHALL use the NeuroTwin purple color palette (purple-100 through purple-700)
2. THE Auth pages SHALL use glass morphism styling for cards (bg-white/70 backdrop-blur-xl)
3. THE Auth pages SHALL use Framer Motion for page transitions and animations
4. THE Auth pages SHALL use rounded-xl for cards and rounded-lg for inputs/buttons
5. THE Primary buttons SHALL use bg-purple-700 hover:bg-purple-600 text-white
6. THE Secondary buttons SHALL use bg-purple-100 text-purple-700 hover:bg-purple-200
7. ALL animations SHALL complete in under 300ms
