# Design Document: Authentication and Profile Management

## Overview

The Authentication and Profile Management feature provides secure user authentication and profile management for the NeuroTwin frontend. Built with Next.js 14+ App Router, this feature integrates with the existing Django backend authentication API to enable email/password registration, Google OAuth, JWT token management, password reset flows, and user profile editing.

Key design principles:
- **Security First**: JWT tokens stored securely, automatic token refresh, protected routes
- **Seamless OAuth**: Google sign-in integration with fallback to email/password
- **Glass Morphism**: Consistent with dashboard aesthetic using purple color palette
- **Form Validation**: Real-time validation with clear error messages
- **Accessibility**: WCAG AA compliant with keyboard navigation and screen reader support

## Architecture

The authentication system follows a layered architecture:

1. **Presentation Layer**: Auth pages (login, signup, forgot password, reset password) and profile settings
2. **State Management Layer**: AuthContext provides global authentication state
3. **API Layer**: Axios-based API client with automatic token refresh interceptor
4. **Storage Layer**: TokenManager handles secure token storage in localStorage

### Authentication Flow

1. User submits credentials on login page
2. AuthContext calls authApi.login()
3. API client sends request to Django backend
4. Backend returns JWT access + refresh tokens
5. TokenManager stores tokens in localStorage
6. AuthContext updates state with user data
7. User is redirected to /dashboard/twin

### Token Refresh Flow

1. API request receives 401 Unauthorized
2. Axios interceptor catches the error
3. Interceptor calls refresh endpoint with refresh token
4. Backend returns new access + refresh tokens
5. TokenManager updates stored tokens
6. Original request is retried with new access token
7. If refresh fails, user is redirected to login

### Route Protection

Next.js middleware checks authentication status for /dashboard/* routes:
- If unauthenticated → redirect to /auth/login
- If authenticated but token expired → attempt refresh
- If refresh succeeds → allow access
- If refresh fails → redirect to /auth/login


## Components and Interfaces

### Directory Structure

```
neuro-frontend/src/
├── app/
│   ├── auth/
│   │   ├── layout.tsx              # Auth pages layout
│   │   ├── login/page.tsx          # Login page
│   │   ├── signup/page.tsx         # Signup page
│   │   ├── forgot-password/page.tsx # Forgot password
│   │   ├── reset-password/page.tsx  # Reset password
│   │   └── oauth/callback/page.tsx  # OAuth callback handler
│   └── dashboard/
│       └── settings/
│           └── profile/page.tsx     # Profile settings
├── components/
│   ├── auth/
│   │   ├── AuthCard.tsx            # Glass card wrapper
│   │   ├── PasswordInput.tsx       # Password with toggle
│   │   └── OAuthButton.tsx         # Google OAuth button
│   └── profile/
│       ├── ProfileForm.tsx         # Profile edit form
│       ├── ImageUpload.tsx         # Avatar upload
│       └── PasswordChangeForm.tsx  # Change password
├── hooks/
│   ├── useAuth.ts                  # Auth context & hooks
│   └── useProfile.ts               # Profile management
├── lib/
│   ├── api/
│   │   ├── client.ts               # Axios client with interceptors
│   │   ├── auth.ts                 # Auth API calls
│   │   └── user.ts                 # User API calls
│   ├── auth/
│   │   └── token-manager.ts        # Token storage & refresh
│   └── validation/
│       └── auth-schemas.ts         # Zod validation schemas
├── middleware.ts                   # Next.js middleware for auth
└── types/
    ├── auth.ts                     # Auth types
    └── user.ts                     # User types
```

### Data Models

#### Auth Types

```typescript
// types/auth.ts

export interface LoginCredentials {
  email: string;
  password: string;
  rememberMe?: boolean;
}

export interface SignupData {
  email: string;
  password: string;
  username: string;
  displayName: string;
  acceptedTerms: boolean;
}

export interface AuthTokens {
  accessToken: string;
  refreshToken: string;
}

export interface AuthUser {
  id: string;
  email: string;
  username: string;
  displayName: string;
  profileImage?: string;
  isVerified: boolean;
  isActive: boolean;
  createdAt: string;
  oauthProvider?: 'google' | null;
}

export interface AuthState {
  user: AuthUser | null;
  tokens: AuthTokens | null;
  isAuthenticated: boolean;
  isLoading: boolean;
}
```

#### User Types

```typescript
// types/user.ts

export interface UserProfile {
  id: string;
  email: string;
  username: string;
  displayName: string;
  bio?: string;
  profileImage?: string;
  createdAt: string;
  updatedAt: string;
}

export interface ProfileUpdateData {
  username?: string;
  displayName?: string;
  bio?: string;
}
```

### Core Implementation

#### 1. Token Manager

Handles secure storage and retrieval of JWT tokens:

```typescript
// lib/auth/token-manager.ts

const ACCESS_TOKEN_KEY = 'neurotwin_access_token';
const REFRESH_TOKEN_KEY = 'neurotwin_refresh_token';

export class TokenManager {
  static setTokens(accessToken: string, refreshToken: string): void {
    if (typeof window === 'undefined') return;
    localStorage.setItem(ACCESS_TOKEN_KEY, accessToken);
    localStorage.setItem(REFRESH_TOKEN_KEY, refreshToken);
  }

  static getTokens(): { accessToken: string; refreshToken: string } | null {
    if (typeof window === 'undefined') return null;
    const accessToken = localStorage.getItem(ACCESS_TOKEN_KEY);
    const refreshToken = localStorage.getItem(REFRESH_TOKEN_KEY);
    if (!accessToken || !refreshToken) return null;
    return { accessToken, refreshToken };
  }

  static clearTokens(): void {
    if (typeof window === 'undefined') return;
    localStorage.removeItem(ACCESS_TOKEN_KEY);
    localStorage.removeItem(REFRESH_TOKEN_KEY);
  }

  static updateAccessToken(accessToken: string): void {
    if (typeof window === 'undefined') return;
    localStorage.setItem(ACCESS_TOKEN_KEY, accessToken);
  }
}
```

#### 2. API Client with Automatic Token Refresh

Axios client with interceptors for authentication and token refresh:

```typescript
// lib/api/client.ts

import axios, { AxiosInstance, AxiosError, InternalAxiosRequestConfig } from 'axios';
import { TokenManager } from '@/lib/auth/token-manager';

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

class ApiClient {
  private client: AxiosInstance;
  private isRefreshing = false;
  private refreshSubscribers: ((token: string) => void)[] = [];

  constructor() {
    this.client = axios.create({
      baseURL: API_BASE_URL,
      headers: { 'Content-Type': 'application/json' },
    });
    this.setupInterceptors();
  }

  private setupInterceptors() {
    // Request interceptor: Add access token
    this.client.interceptors.request.use(
      (config: InternalAxiosRequestConfig) => {
        const token = TokenManager.getAccessToken();
        if (token && config.headers) {
          config.headers.Authorization = `Bearer ${token}`;
        }
        return config;
      }
    );

    // Response interceptor: Handle token refresh
    this.client.interceptors.response.use(
      (response) => response,
      async (error: AxiosError) => {
        const originalRequest = error.config as InternalAxiosRequestConfig & { _retry?: boolean };

        if (error.response?.status === 401 && !originalRequest._retry) {
          if (this.isRefreshing) {
            // Queue request until refresh completes
            return new Promise((resolve) => {
              this.refreshSubscribers.push((token: string) => {
                if (originalRequest.headers) {
                  originalRequest.headers.Authorization = `Bearer ${token}`;
                }
                resolve(this.client(originalRequest));
              });
            });
          }

          originalRequest._retry = true;
          this.isRefreshing = true;

          try {
            const refreshToken = TokenManager.getRefreshToken();
            if (!refreshToken) throw new Error('No refresh token');

            const response = await axios.post(`${API_BASE_URL}/api/v1/auth/refresh`, {
              refresh_token: refreshToken,
            });

            const { access_token, refresh_token } = response.data.data;
            TokenManager.setTokens(access_token, refresh_token);

            // Notify queued requests
            this.refreshSubscribers.forEach((callback) => callback(access_token));
            this.refreshSubscribers = [];

            if (originalRequest.headers) {
              originalRequest.headers.Authorization = `Bearer ${access_token}`;
            }
            return this.client(originalRequest);
          } catch (refreshError) {
            TokenManager.clearTokens();
            window.location.href = '/auth/login';
            return Promise.reject(refreshError);
          } finally {
            this.isRefreshing = false;
          }
        }

        return Promise.reject(error);
      }
    );
  }

  getInstance(): AxiosInstance {
    return this.client;
  }
}

export const apiClient = new ApiClient().getInstance();
```

#### 3. Authentication Context

Provides global authentication state and methods:

```typescript
// hooks/useAuth.ts
'use client';

import { createContext, useContext, useState, useEffect, ReactNode } from 'react';
import { useRouter } from 'next/navigation';
import { AuthState, LoginCredentials, SignupData } from '@/types/auth';
import { TokenManager } from '@/lib/auth/token-manager';
import { authApi } from '@/lib/api/auth';

interface AuthContextValue extends AuthState {
  login: (credentials: LoginCredentials) => Promise<void>;
  signup: (data: SignupData) => Promise<void>;
  loginWithGoogle: () => Promise<void>;
  logout: () => Promise<void>;
  refreshUser: () => Promise<void>;
}

const AuthContext = createContext<AuthContextValue | undefined>(undefined);

export function AuthProvider({ children }: { children: ReactNode }) {
  const router = useRouter();
  const [state, setState] = useState<AuthState>({
    user: null,
    tokens: null,
    isAuthenticated: false,
    isLoading: true,
  });

  // Initialize auth state from stored tokens
  useEffect(() => {
    const initAuth = async () => {
      const tokens = TokenManager.getTokens();
      if (tokens) {
        try {
          const user = await authApi.getCurrentUser();
          setState({ user, tokens, isAuthenticated: true, isLoading: false });
        } catch (error) {
          TokenManager.clearTokens();
          setState({ user: null, tokens: null, isAuthenticated: false, isLoading: false });
        }
      } else {
        setState(prev => ({ ...prev, isLoading: false }));
      }
    };
    initAuth();
  }, []);

  const login = async (credentials: LoginCredentials) => {
    const response = await authApi.login(credentials);
    TokenManager.setTokens(response.access_token, response.refresh_token);
    const user = await authApi.getCurrentUser();
    setState({
      user,
      tokens: { accessToken: response.access_token, refreshToken: response.refresh_token },
      isAuthenticated: true,
      isLoading: false,
    });
    router.push('/dashboard/twin');
  };

  const signup = async (data: SignupData) => {
    await authApi.signup(data);
  };

  const loginWithGoogle = async () => {
    window.location.href = await authApi.getGoogleOAuthUrl();
  };

  const logout = async () => {
    try {
      await authApi.logout(state.tokens?.refreshToken || '');
    } finally {
      TokenManager.clearTokens();
      setState({ user: null, tokens: null, isAuthenticated: false, isLoading: false });
      router.push('/auth/login');
    }
  };

  const refreshUser = async () => {
    const user = await authApi.getCurrentUser();
    setState(prev => ({ ...prev, user }));
  };

  return (
    <AuthContext.Provider value={{ ...state, login, signup, loginWithGoogle, logout, refreshUser }}>
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  const context = useContext(AuthContext);
  if (!context) throw new Error('useAuth must be used within AuthProvider');
  return context;
}
```


#### 4. Form Validation Schemas

Zod schemas for form validation:

```typescript
// lib/validation/auth-schemas.ts

import { z } from 'zod';

export const loginSchema = z.object({
  email: z.string().email('Please enter a valid email address'),
  password: z.string().min(1, 'Password is required'),
  rememberMe: z.boolean().optional(),
});

export const signupSchema = z.object({
  email: z.string().email('Please enter a valid email address'),
  password: z.string().min(8, 'Password must be at least 8 characters'),
  username: z.string().min(3, 'Username must be at least 3 characters'),
  displayName: z.string().min(1, 'Display name is required'),
  acceptedTerms: z.boolean().refine(val => val === true, {
    message: 'You must accept the terms of service',
  }),
});

export const resetPasswordSchema = z.object({
  newPassword: z.string().min(8, 'Password must be at least 8 characters'),
  confirmPassword: z.string().min(8, 'Password must be at least 8 characters'),
}).refine(data => data.newPassword === data.confirmPassword, {
  message: 'Passwords do not match',
  path: ['confirmPassword'],
});

export const profileUpdateSchema = z.object({
  username: z.string().min(3, 'Username must be at least 3 characters').optional(),
  displayName: z.string().min(1, 'Display name is required').optional(),
  bio: z.string().max(500, 'Bio must be less than 500 characters').optional(),
});

export const passwordChangeSchema = z.object({
  currentPassword: z.string().min(1, 'Current password is required'),
  newPassword: z.string().min(8, 'Password must be at least 8 characters'),
  confirmPassword: z.string().min(8, 'Password must be at least 8 characters'),
}).refine(data => data.newPassword === data.confirmPassword, {
  message: 'Passwords do not match',
  path: ['confirmPassword'],
});
```

#### 5. Next.js Middleware for Route Protection

```typescript
// middleware.ts

import { NextResponse } from 'next/server';
import type { NextRequest } from 'next/server';

export function middleware(request: NextRequest) {
  const { pathname } = request.nextUrl;

  // Check if accessing protected dashboard routes
  if (pathname.startsWith('/dashboard')) {
    const accessToken = request.cookies.get('neurotwin_access_token')?.value;
    
    if (!accessToken) {
      // Redirect to login with return URL
      const loginUrl = new URL('/auth/login', request.url);
      loginUrl.searchParams.set('returnUrl', pathname);
      return NextResponse.redirect(loginUrl);
    }
  }

  // Redirect authenticated users away from auth pages
  if (pathname.startsWith('/auth')) {
    const accessToken = request.cookies.get('neurotwin_access_token')?.value;
    
    if (accessToken) {
      return NextResponse.redirect(new URL('/dashboard/twin', request.url));
    }
  }

  return NextResponse.next();
}

export const config = {
  matcher: ['/dashboard/:path*', '/auth/:path*'],
};
```

### UI Components

#### AuthCard Component

Glass morphism card for auth pages:

```typescript
// components/auth/AuthCard.tsx
'use client';

import { motion } from 'framer-motion';
import { cn } from '@/lib/utils';

export interface AuthCardProps {
  children: React.ReactNode;
  className?: string;
  title?: string;
  subtitle?: string;
}

export function AuthCard({ children, className, title, subtitle }: AuthCardProps) {
  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.3, type: 'spring' }}
      className={cn(
        'w-full max-w-md mx-auto',
        'bg-white/70 backdrop-blur-xl border border-neutral-400/40 shadow-lg rounded-xl',
        'p-8',
        className
      )}
    >
      {title && (
        <div className="mb-6 text-center">
          <h1 className="text-2xl font-bold text-neutral-800">{title}</h1>
          {subtitle && <p className="text-sm text-neutral-600 mt-2">{subtitle}</p>}
        </div>
      )}
      {children}
    </motion.div>
  );
}
```

#### PasswordInput Component

Password input with visibility toggle:

```typescript
// components/auth/PasswordInput.tsx
'use client';

import { useState, forwardRef, InputHTMLAttributes } from 'react';
import { LuEye, LuEyeOff } from 'react-icons/lu';
import { cn } from '@/lib/utils';

export interface PasswordInputProps extends Omit<InputHTMLAttributes<HTMLInputElement>, 'type'> {
  label?: string;
  error?: string;
}

export const PasswordInput = forwardRef<HTMLInputElement, PasswordInputProps>(
  ({ label, error, className, ...props }, ref) => {
    const [showPassword, setShowPassword] = useState(false);

    return (
      <div className="w-full">
        {label && (
          <label htmlFor={props.id} className="block text-sm font-medium text-neutral-700 mb-2">
            {label}
          </label>
        )}
        <div className="relative">
          <input
            ref={ref}
            type={showPassword ? 'text' : 'password'}
            className={cn(
              'w-full px-4 py-2 pr-10 rounded-lg border bg-white text-neutral-800',
              'focus:outline-none focus:ring-2 focus:ring-purple-600 focus:border-transparent',
              'transition-colors',
              error ? 'border-red-500' : 'border-neutral-400',
              className
            )}
            {...props}
          />
          <button
            type="button"
            onClick={() => setShowPassword(!showPassword)}
            className="absolute right-3 top-1/2 -translate-y-1/2 text-neutral-500 hover:text-neutral-700"
            aria-label={showPassword ? 'Hide password' : 'Show password'}
          >
            {showPassword ? <LuEyeOff className="w-5 h-5" /> : <LuEye className="w-5 h-5" />}
          </button>
        </div>
        {error && (
          <p className="mt-1 text-sm text-red-600" role="alert">
            {error}
          </p>
        )}
      </div>
    );
  }
);

PasswordInput.displayName = 'PasswordInput';
```

#### ImageUpload Component

Profile image upload with preview:

```typescript
// components/profile/ImageUpload.tsx
'use client';

import { useState, useRef } from 'react';
import { LuUpload, LuX } from 'react-icons/lu';
import { Button } from '@/components/ui/Button';
import { cn } from '@/lib/utils';

export interface ImageUploadProps {
  currentImage?: string;
  onUpload: (file: File) => Promise<void>;
  isLoading?: boolean;
}

export function ImageUpload({ currentImage, onUpload, isLoading }: ImageUploadProps) {
  const [preview, setPreview] = useState<string | null>(null);
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [error, setError] = useState<string | null>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);

  const handleFileSelect = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;

    // Validate file type
    if (!['image/jpeg', 'image/png'].includes(file.type)) {
      setError('Please select a JPEG or PNG image');
      return;
    }

    // Validate file size (5MB)
    if (file.size > 5 * 1024 * 1024) {
      setError('Image must be less than 5MB');
      return;
    }

    setError(null);
    setSelectedFile(file);
    
    // Create preview
    const reader = new FileReader();
    reader.onloadend = () => {
      setPreview(reader.result as string);
    };
    reader.readAsDataURL(file);
  };

  const handleUpload = async () => {
    if (!selectedFile) return;
    
    try {
      await onUpload(selectedFile);
      setPreview(null);
      setSelectedFile(null);
    } catch (err: any) {
      setError(err.message || 'Upload failed');
    }
  };

  const handleCancel = () => {
    setPreview(null);
    setSelectedFile(null);
    setError(null);
    if (fileInputRef.current) {
      fileInputRef.current.value = '';
    }
  };

  const displayImage = preview || currentImage;

  return (
    <div className="space-y-4">
      <div className="flex items-center gap-4">
        <div className="relative">
          <div className="w-24 h-24 rounded-full overflow-hidden bg-neutral-300 border-2 border-neutral-400">
            {displayImage ? (
              <img src={displayImage} alt="Profile" className="w-full h-full object-cover" />
            ) : (
              <div className="w-full h-full flex items-center justify-center text-neutral-600">
                <LuUpload className="w-8 h-8" />
              </div>
            )}
          </div>
        </div>

        <div className="flex-1">
          <input
            ref={fileInputRef}
            type="file"
            accept="image/jpeg,image/png"
            onChange={handleFileSelect}
            className="hidden"
            id="profile-image-upload"
          />
          <label htmlFor="profile-image-upload">
            <Button
              type="button"
              variant="outline"
              onClick={() => fileInputRef.current?.click()}
              disabled={isLoading}
              as="span"
            >
              <LuUpload className="w-4 h-4 mr-2" />
              Choose Image
            </Button>
          </label>
          <p className="text-xs text-neutral-600 mt-2">
            JPEG or PNG, max 5MB
          </p>
        </div>
      </div>

      {error && (
        <p className="text-sm text-red-600" role="alert">
          {error}
        </p>
      )}

      {preview && (
        <div className="flex gap-2">
          <Button
            type="button"
            variant="primary"
            onClick={handleUpload}
            disabled={isLoading}
          >
            {isLoading ? 'Uploading...' : 'Save Image'}
          </Button>
          <Button
            type="button"
            variant="outline"
            onClick={handleCancel}
            disabled={isLoading}
          >
            Cancel
          </Button>
        </div>
      )}
    </div>
  );
}
```


## Correctness Properties

A property is a characteristic or behavior that should hold true across all valid executions of a system—essentially, a formal statement about what the system should do. Properties serve as the bridge between human-readable specifications and machine-verifiable correctness guarantees.

### Property 1: Successful login stores tokens and redirects

*For any* valid email and password combination, when login succeeds, the system should store both access and refresh tokens in localStorage and redirect to /dashboard/twin

**Validates: Requirements 1.5, 1.6**

### Property 2: Failed login displays error message

*For any* invalid credentials, when login fails, the system should display an error message inline without storing tokens or redirecting

**Validates: Requirements 1.7**

### Property 3: Authenticated users bypass auth pages

*For any* authenticated user (with valid tokens), when they visit /auth/login or /auth/signup, the system should redirect them to /dashboard/twin

**Validates: Requirements 1.10, 2.11**

### Property 4: Unauthenticated users cannot access dashboard

*For any* unauthenticated user (no tokens), when they attempt to access any /dashboard/* route, the system should redirect them to /auth/login

**Validates: Requirements 4.2**

### Property 5: Expired tokens trigger automatic refresh

*For any* API request that returns 401 Unauthorized, the system should attempt to refresh the access token using the refresh token before failing

**Validates: Requirements 4.5, 5.2**

### Property 6: Successful token refresh updates storage and retries request

*For any* successful token refresh, the system should update the stored access token and retry the original failed request

**Validates: Requirements 4.6, 5.4**

### Property 7: Failed token refresh clears tokens and redirects

*For any* failed token refresh attempt, the system should clear all stored tokens and redirect to /auth/login

**Validates: Requirements 4.7**

### Property 8: Valid registration data calls API

*For any* valid registration data (email, password ≥8 chars, username ≥3 chars, displayName, acceptedTerms=true), when submitted, the system should call POST /api/v1/auth/register

**Validates: Requirements 2.5**

### Property 9: Invalid registration data shows field-specific errors

*For any* invalid registration data, the system should display validation errors inline below the corresponding input field

**Validates: Requirements 2.7**

### Property 10: OAuth callback success stores tokens and redirects

*For any* successful OAuth callback, the system should store JWT tokens and redirect to /dashboard/twin

**Validates: Requirements 3.4**

### Property 11: Profile save triggers API call

*For any* profile update data (username, displayName, bio), when user clicks "Save Changes", the system should call PUT /api/v1/users/profile with the updated data

**Validates: Requirements 7.6**

### Property 12: Image save triggers upload API call

*For any* valid image file (JPEG/PNG, ≤5MB), when user clicks "Save", the system should call POST /api/v1/users/profile/image with the file

**Validates: Requirements 8.7**

### Property 13: Password validation enforces minimum length

*For any* password input, the system should validate that it is at least 8 characters and display an error if shorter

**Validates: Requirements 9.5, 12.5**

### Property 14: Password confirmation validates match

*For any* new password and confirm password pair, the system should validate that they match and display an error if they don't

**Validates: Requirements 9.6**

### Property 15: Logout clears all tokens

*For any* logout action, the system should clear both access and refresh tokens from localStorage

**Validates: Requirements 11.3**

### Property 16: Required fields show error when empty

*For any* required form field, when left empty and form is submitted, the system should display "This field is required" error

**Validates: Requirements 12.3**

### Property 17: Email validation rejects invalid formats

*For any* email input, the system should validate the format and display "Please enter a valid email address" error for invalid formats

**Validates: Requirements 12.4**

### Property 18: All form inputs have associated labels

*For any* form input element, there should be a corresponding label element with matching htmlFor attribute

**Validates: Requirements 15.1**

### Property 19: Form errors are announced to screen readers

*For any* form validation error, the error message should have role="alert" attribute for screen reader announcement

**Validates: Requirements 15.2**

## Error Handling

### API Errors

- **Network Errors**: Display "Network error. Please try again." toast message
- **Server Errors (500)**: Display "Something went wrong. Please try again later." toast message
- **Validation Errors (400)**: Display field-specific errors inline below inputs
- **Authentication Errors (401)**: Attempt token refresh, redirect to login if refresh fails
- **Not Found (404)**: Display "Resource not found" message

### Form Validation Errors

- Display errors inline below the corresponding input field
- Use red text color (text-red-600) for error messages
- Add red border to invalid inputs (border-red-500)
- Clear errors when user starts typing in the field
- Disable submit button while validation errors exist

### File Upload Errors

- **Invalid file type**: "Please select a JPEG or PNG image"
- **File too large**: "Image must be less than 5MB"
- **Upload failed**: Display server error message or generic "Upload failed"

### OAuth Errors

- **User cancellation**: No error message (expected behavior)
- **OAuth provider error**: "Google sign-in failed. Please try again."
- **Callback error**: "Authentication failed. Please try again."

## Testing Strategy

### Unit Testing

Unit tests will verify specific examples, edge cases, and error conditions:

- **Auth Components**: Test rendering, user interactions, form submissions
- **Token Manager**: Test token storage, retrieval, clearing
- **API Client**: Test request/response handling, interceptors
- **Form Validation**: Test validation rules, error messages
- **OAuth Flow**: Test redirect URL generation, callback handling

### Property-Based Testing

Property tests will verify universal properties across all inputs using fast-check library:

- **Configuration**: Minimum 100 iterations per property test
- **Tagging**: Each test tagged with **Feature: authentication-profile, Property {number}: {property_text}**
- **Coverage**: All 19 correctness properties implemented as property-based tests

Example property test structure:

```typescript
// __tests__/auth/login.property.test.ts

import fc from 'fast-check';
import { TokenManager } from '@/lib/auth/token-manager';
import { authApi } from '@/lib/api/auth';

describe('Feature: authentication-profile, Property 1: Successful login stores tokens and redirects', () => {
  it('should store tokens and redirect for any valid credentials', async () => {
    await fc.assert(
      fc.asyncProperty(
        fc.emailAddress(),
        fc.string({ minLength: 8 }),
        async (email, password) => {
          // Mock successful API response
          jest.spyOn(authApi, 'login').mockResolvedValue({
            access_token: 'mock_access_token',
            refresh_token: 'mock_refresh_token',
          });

          // Perform login
          await login({ email, password });

          // Verify tokens are stored
          const tokens = TokenManager.getTokens();
          expect(tokens).not.toBeNull();
          expect(tokens?.accessToken).toBe('mock_access_token');
          expect(tokens?.refreshToken).toBe('mock_refresh_token');
        }
      ),
      { numRuns: 100 }
    );
  });
});
```

### Integration Testing

Integration tests will verify end-to-end flows:

- **Login Flow**: Complete login process from form submission to dashboard redirect
- **Signup Flow**: Registration, email verification, first login
- **Password Reset Flow**: Request reset, receive email, reset password, login
- **OAuth Flow**: Initiate OAuth, handle callback, store tokens, redirect
- **Token Refresh Flow**: Expired token, automatic refresh, request retry
- **Profile Update Flow**: Edit profile, upload image, save changes

### Accessibility Testing

- **Keyboard Navigation**: All interactive elements accessible via keyboard
- **Screen Reader**: ARIA labels, roles, and announcements
- **Color Contrast**: WCAG AA compliance for all text/background combinations
- **Focus Management**: Visible focus indicators, logical tab order

## Performance Considerations

### Token Storage

- Use localStorage for token storage (synchronous, fast access)
- Consider httpOnly cookies for enhanced security in production
- Implement token expiration checking before API requests

### API Request Optimization

- Implement request deduplication for concurrent token refresh attempts
- Use axios request cancellation for abandoned requests
- Cache user profile data to reduce API calls

### Form Validation

- Use debounced validation for real-time feedback (300ms delay)
- Validate on blur for better UX (don't validate while typing)
- Use Zod for efficient schema-based validation

### Image Upload

- Client-side image compression before upload (reduce file size)
- Show upload progress indicator for large files
- Implement retry logic for failed uploads

## Security Considerations

### Token Security

- Store tokens in localStorage (acceptable for SPA, consider httpOnly cookies for production)
- Never log tokens or include in error messages
- Clear tokens immediately on logout
- Implement token rotation on refresh

### Password Security

- Enforce minimum 8 character password length
- Never store passwords in state longer than necessary
- Clear password fields after submission
- Use password visibility toggle for better UX

### OAuth Security

- Validate OAuth state parameter to prevent CSRF
- Use PKCE (Proof Key for Code Exchange) for enhanced security
- Verify OAuth provider certificates
- Handle OAuth errors gracefully without exposing sensitive info

### API Security

- Include CSRF tokens for state-changing requests
- Validate all user input on both client and server
- Implement rate limiting for auth endpoints
- Use HTTPS for all API communication

## Deployment Considerations

### Environment Variables

Required environment variables:

```
NEXT_PUBLIC_API_URL=https://api.neurotwin.com
NEXT_PUBLIC_GOOGLE_CLIENT_ID=your_google_client_id
```

### Build Configuration

- Enable strict TypeScript mode
- Configure Tailwind CSS purging for production
- Optimize bundle size (code splitting, tree shaking)
- Enable source maps for debugging

### Monitoring

- Log authentication events (login, logout, token refresh)
- Track OAuth conversion rates
- Monitor token refresh success/failure rates
- Alert on unusual authentication patterns

