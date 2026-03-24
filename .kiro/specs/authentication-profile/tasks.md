# Implementation Plan: Authentication and Profile Management

## Overview

This implementation plan breaks down the authentication and profile management feature into discrete, incremental coding tasks. Each task builds on previous work, with testing integrated throughout to catch errors early. The plan follows the design document and ensures all requirements are covered.

## Tasks

- [x] 1. Set up project structure and core types
  - Create directory structure for auth and profile features
  - Define TypeScript types for auth and user data
  - Set up validation schemas with Zod
  - _Requirements: All_

- [x] 2. Implement Token Manager
  - [x] 2.1 Create TokenManager class for secure token storage
    - Implement setTokens, getTokens, clearTokens, updateAccessToken methods
    - Handle localStorage with SSR safety checks
    - _Requirements: 4.8, 5.1_
  
  - [x] 2.2 Write property test for TokenManager

    - **Property 15: Logout clears all tokens**
    - **Validates: Requirements 11.3**

- [ ] 3. Implement API Client with token refresh
  - [x] 3.1 Create Axios client with base configuration
    - Set up API base URL from environment variables
    - Configure default headers
    - _Requirements: 5.6_
  
  - [x] 3.2 Add request interceptor for authentication
    - Attach access token to all requests
    - _Requirements: 5.6_
  
  - [x] 3.3 Add response interceptor for token refresh
    - Detect 401 errors and trigger refresh
    - Queue concurrent requests during refresh
    - Retry original request after successful refresh
    - Redirect to login on refresh failure
    - _Requirements: 4.5, 4.6, 4.7, 5.2, 5.3, 5.4, 5.5_
  
  - [x] 3.4 Write property tests for API client

    - **Property 5: Expired tokens trigger automatic refresh**
    - **Property 6: Successful token refresh updates storage and retries request**
    - **Property 7: Failed token refresh clears tokens and redirects**
    - **Validates: Requirements 4.5, 4.6, 4.7, 5.2, 5.4**

- [x] 4. Implement Auth API layer
  - [x] 4.1 Create auth API functions
    - Implement login, signup, getCurrentUser, logout functions
    - Implement requestPasswordReset, resetPassword functions
    - Implement getGoogleOAuthUrl, handleOAuthCallback functions
    - _Requirements: 1.5, 2.5, 6.2, 6.7, 11.2_
  
  - [ ]* 4.2 Write unit tests for auth API
    - Test API call construction and response handling
    - Test error handling for network and server errors
    - _Requirements: 1.5, 2.5, 6.2, 6.7_

- [x] 5. Implement User API layer
  - [x] 5.1 Create user API functions
    - Implement getProfile, updateProfile functions
    - Implement uploadProfileImage, changePassword functions
    - _Requirements: 7.1, 7.6, 8.7, 9.6_
  
  - [ ]* 5.2 Write unit tests for user API
    - Test API call construction and response handling
    - Test multipart form data for image upload
    - _Requirements: 7.6, 8.7, 9.6_

- [x] 6. Checkpoint - Ensure all tests pass
  - Ensure all tests pass, ask the user if questions arise.

- [x] 7. Implement Authentication Context
  - [x] 7.1 Create AuthContext with state management
    - Define AuthState interface and initial state
    - Implement AuthProvider component
    - Initialize auth state from stored tokens on mount
    - _Requirements: 4.1, 4.3, 4.4_
  
  - [x] 7.2 Implement authentication methods
    - Implement login method with token storage and redirect
    - Implement signup method
    - Implement loginWithGoogle method
    - Implement logout method with token clearing
    - Implement refreshUser method
    - _Requirements: 1.5, 1.6, 2.5, 3.1, 11.2, 11.3, 11.4_
  
  - [x] 7.3 Create useAuth hook
    - Export useAuth hook for consuming auth context
    - Add error handling for usage outside provider
    - _Requirements: 4.1_
  
  - [ ]* 7.4 Write property tests for auth context
    - **Property 1: Successful login stores tokens and redirects**
    - **Property 2: Failed login displays error message**
    - **Property 3: Authenticated users bypass auth pages**
    - **Validates: Requirements 1.5, 1.6, 1.7, 1.10**

- [x] 8. Implement Next.js middleware for route protection
  - [x] 8.1 Create middleware for auth guard
    - Protect /dashboard/* routes from unauthenticated access
    - Redirect authenticated users away from /auth/* pages
    - Store attempted URL for post-login redirect
    - _Requirements: 4.1, 4.2, 4.3_
  
  - [ ]* 8.2 Write property tests for middleware
    - **Property 4: Unauthenticated users cannot access dashboard**
    - **Validates: Requirements 4.2**

- [x] 9. Implement auth UI components
  - [x] 9.1 Create AuthCard component
    - Implement glass morphism card with title and subtitle
    - Add Framer Motion animations
    - _Requirements: 16.1, 16.2, 16.3, 16.4_
  
  - [x] 9.2 Create PasswordInput component
    - Implement password input with visibility toggle
    - Add label and error message support
    - Include accessibility attributes
    - _Requirements: 1.9, 2.9, 15.1, 15.3_
  
  - [x] 9.3 Create OAuthButton component
    - Implement Google OAuth button with branding
    - Support signin and signup modes
    - _Requirements: 1.2, 2.2_
  
  - [ ]* 9.4 Write unit tests for auth components
    - Test component rendering and user interactions
    - Test accessibility attributes
    - _Requirements: 15.1, 15.2, 15.3_

- [x] 10. Implement Login Page
  - [x] 10.1 Create login page with form
    - Implement email and password inputs
    - Add "Remember me" checkbox
    - Add "Forgot password?" link
    - Add Google OAuth button
    - Integrate with useAuth hook
    - _Requirements: 1.1, 1.2, 1.3, 1.4, 1.5, 1.6, 1.11_
  
  - [x] 10.2 Add form validation with React Hook Form and Zod
    - Implement loginSchema validation
    - Display inline validation errors
    - _Requirements: 12.1, 12.2, 12.3, 12.4, 12.7_
  
  - [x] 10.3 Add loading and error states
    - Show loading spinner during authentication
    - Display error messages for failed login
    - Disable form during submission
    - _Requirements: 1.7, 1.8, 13.1, 13.2, 13.3_
  
  - [ ]* 10.4 Write property tests for login page
    - **Property 16: Required fields show error when empty**
    - **Property 17: Email validation rejects invalid formats**
    - **Validates: Requirements 12.3, 12.4**

- [x] 11. Implement Signup Page
  - [x] 11.1 Create signup page with form
    - Implement email, username, displayName, password inputs
    - Add Terms of Service checkbox
    - Add Google OAuth button
    - Integrate with useAuth hook
    - _Requirements: 2.1, 2.2, 2.3, 2.4, 2.5, 2.12_
  
  - [x] 11.2 Add form validation
    - Implement signupSchema validation
    - Display inline validation errors
    - Validate Terms checkbox
    - _Requirements: 2.4, 2.7, 2.8, 12.1, 12.2, 12.5_
  
  - [x] 11.3 Add success state for email verification
    - Show success message after registration
    - Display link to login page
    - _Requirements: 2.6_
  
  - [ ]* 11.4 Write property tests for signup page
    - **Property 8: Valid registration data calls API**
    - **Property 9: Invalid registration data shows field-specific errors**
    - **Property 13: Password validation enforces minimum length**
    - **Validates: Requirements 2.5, 2.7, 2.8, 12.5**

- [x] 12. Checkpoint - Ensure all tests pass
  - Ensure all tests pass, ask the user if questions arise.

- [x] 13. Implement Forgot Password Page
  - [x] 13.1 Create forgot password page with email input
    - Implement email input field
    - Add form validation
    - Call requestPasswordReset API
    - _Requirements: 6.1, 6.2, 6.3, 6.4_
  
  - [ ]* 13.2 Write unit tests for forgot password page
    - Test form submission and API call
    - Test success message display
    - _Requirements: 6.2, 6.4_

- [x] 14. Implement Reset Password Page
  - [x] 14.1 Create reset password page with token handling
    - Extract token from URL query parameter
    - Implement new password and confirm password inputs
    - Add form validation with password matching
    - Call resetPassword API
    - _Requirements: 6.5, 6.6, 6.7, 6.8, 6.9_
  
  - [ ]* 14.2 Write property tests for password reset
    - **Property 14: Password confirmation validates match**
    - **Validates: Requirements 9.6**

- [x] 15. Implement OAuth Callback Page
  - [x] 15.1 Create OAuth callback handler
    - Extract authorization code from URL
    - Call handleOAuthCallback API
    - Store tokens and redirect on success
    - Display error on failure
    - _Requirements: 3.3, 3.4, 3.5, 3.6_
  
  - [ ]* 15.2 Write property tests for OAuth callback
    - **Property 10: OAuth callback success stores tokens and redirects**
    - **Validates: Requirements 3.4**

- [x] 16. Implement Profile Form component
  - [x] 16.1 Create profile form with editable fields
    - Implement username, displayName, bio inputs
    - Display email as read-only
    - Display account creation date
    - Add form validation
    - _Requirements: 7.1, 7.2, 7.3, 7.4, 7.5_
  
  - [x] 16.2 Integrate with user API
    - Load current profile data on mount
    - Call updateProfile API on save
    - Display success/error messages
    - _Requirements: 7.6, 7.7, 7.8, 7.9_
  
  - [ ]* 16.3 Write property tests for profile form
    - **Property 11: Profile save triggers API call**
    - **Validates: Requirements 7.6**

- [x] 17. Implement ImageUpload component
  - [x] 17.1 Create image upload with preview
    - Implement file picker for JPEG/PNG
    - Validate file type and size (max 5MB)
    - Display image preview before upload
    - Show current profile image
    - _Requirements: 8.1, 8.2, 8.3, 8.4, 8.5, 8.6_
  
  - [x] 17.2 Integrate with user API
    - Call uploadProfileImage API
    - Update displayed image on success
    - Display error messages
    - _Requirements: 8.7, 8.8, 8.9_
  
  - [ ]* 17.3 Write property tests for image upload
    - **Property 12: Image save triggers upload API call**
    - **Validates: Requirements 8.7**

- [x] 18. Implement PasswordChangeForm component
  - [x] 18.1 Create password change form
    - Implement current password, new password, confirm password inputs
    - Add form validation with password matching
    - Display in modal or expandable section
    - _Requirements: 9.1, 9.2, 9.3, 9.4, 9.5, 9.6_
  
  - [x] 18.2 Integrate with user API
    - Call changePassword API
    - Display success/error messages
    - Clear form on success
    - _Requirements: 9.7, 9.8_
  
  - [ ]* 18.3 Write unit tests for password change form
    - Test form validation and submission
    - Test error handling
    - _Requirements: 9.5, 9.6, 9.7, 9.8_

- [x] 19. Implement Profile Settings Page
  - [x] 19.1 Create profile settings page layout
    - Integrate ProfileForm component
    - Integrate ImageUpload component
    - Integrate PasswordChangeForm component
    - Apply glass morphism styling
    - _Requirements: 7.1, 8.1, 9.1_
  
  - [ ]* 19.2 Write integration tests for profile page
    - Test complete profile update flow
    - Test image upload flow
    - Test password change flow
    - _Requirements: 7.6, 8.7, 9.7_

- [x] 20. Implement user profile display in dashboard
  - [x] 20.1 Update Sidebar component
    - Display user profile image as circular avatar
    - Display user display name or username
    - Add click handler to navigate to profile settings
    - _Requirements: 10.1, 10.2, 10.3_
  
  - [x] 20.2 Add user menu or dropdown
    - Display user email
    - Display account status
    - Add logout button
    - _Requirements: 10.4, 10.5, 11.1_
  
  - [ ]* 20.3 Write unit tests for profile display
    - Test avatar rendering
    - Test navigation to profile settings
    - Test logout functionality
    - _Requirements: 10.1, 10.3, 11.1_

- [x] 21. Implement Auth Layout
  - [x] 21.1 Create auth pages layout
    - Center content on page
    - Apply neutral-200 background
    - Add responsive padding
    - _Requirements: 14.1, 14.2, 14.3, 14.4_
  
  - [ ]* 21.2 Write unit tests for auth layout
    - Test responsive behavior
    - Test styling consistency
    - _Requirements: 14.1, 14.2_

- [x] 22. Add accessibility features
  - [x] 22.1 Ensure all forms have proper labels
    - Add htmlFor attributes to all labels
    - Add ARIA labels to icon-only buttons
    - _Requirements: 15.1, 15.3_
  
  - [x] 22.2 Add ARIA attributes for errors
    - Add role="alert" to error messages
    - Ensure errors are announced to screen readers
    - _Requirements: 15.2_
  
  - [x] 22.3 Test keyboard navigation
    - Verify all interactive elements are keyboard accessible
    - Test tab order
    - Verify focus indicators
    - _Requirements: 15.4, 15.6_
  
  - [ ]* 22.4 Write property tests for accessibility
    - **Property 18: All form inputs have associated labels**
    - **Property 19: Form errors are announced to screen readers**
    - **Validates: Requirements 15.1, 15.2**

- [x] 23. Add animations and transitions
  - [x] 23.1 Add Framer Motion animations to auth pages
    - Animate AuthCard entrance
    - Animate form transitions
    - Animate error messages
    - _Requirements: 16.3, 16.4, 16.5, 16.7_
  
  - [x] 23.2 Add loading states with animations
    - Animate loading spinners
    - Animate button states
    - _Requirements: 13.1_
  
  - [ ]* 23.3 Write unit tests for animations
    - Test animation presence
    - Test animation timing
    - _Requirements: 16.3, 16.7_

- [x] 24. Final checkpoint - Ensure all tests pass
  - Ensure all tests pass, ask the user if questions arise.

- [x] 25. Integration and polish
  - [x] 25.1 Wire all components together
    - Ensure auth flow works end-to-end
    - Verify token refresh works across all pages
    - Test OAuth flow completely
    - _Requirements: All_
  
  - [x] 25.2 Add error boundaries
    - Wrap auth pages in error boundaries
    - Display user-friendly error messages
    - _Requirements: 13.3, 13.4, 13.5_
  
  - [x] 25.3 Optimize performance
    - Implement request deduplication
    - Add loading states
    - Optimize bundle size
    - _Requirements: Performance Considerations_
  
  - [ ]* 25.4 Write end-to-end integration tests
    - Test complete login flow
    - Test complete signup flow
    - Test complete password reset flow
    - Test complete profile update flow
    - _Requirements: All_

## Notes

- Tasks marked with `*` are optional and can be skipped for faster MVP
- Each task references specific requirements for traceability
- Checkpoints ensure incremental validation
- Property tests validate universal correctness properties
- Unit tests validate specific examples and edge cases
- Integration tests verify end-to-end flows
