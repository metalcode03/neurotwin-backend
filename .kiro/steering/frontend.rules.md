---
inclusion: fileMatch
fileMatchPattern: ['neuro-frontend/**/*.ts', 'neuro-frontend/**/*.tsx', 'neuro-frontend/**/*.css']
---

# NeuroTwin Frontend Rules

## Tech Stack
- Next.js (App Router) with TypeScript strict mode
- Tailwind CSS v4 (`@import "tailwindcss"`) + Framer Motion for animations
- `react-icons` (Lucide via `lu` prefix, Feather via `fi` prefix, FontAwesome via `fa` prefix)
- TanStack Query (`@tanstack/react-query`) for server state
- Axios via `apiClient` from `@/lib/api/client` for HTTP calls
- Fonts: Geist Sans + Geist Mono (loaded via `next/font/google`)

## Directory Structure
```
neuro-frontend/src/
├── app/                  # Next.js App Router pages
│   ├── auth/             # Login, register, password reset
│   ├── dashboard/        # Dashboard pages (twin, chat, apps, automation, memory, voice, security, conversations)
│   ├── onboarding/       # Onboarding wizard
│   └── oauth/            # OAuth callback handling
├── components/
│   ├── apps/             # App marketplace components
│   ├── auth/             # Auth forms
│   ├── automation/       # Workflow editor
│   ├── brain/            # AI brain / Twin chat
│   ├── credits/          # Credit usage display
│   ├── layout/           # Sidebar, Header, DashboardLayout
│   ├── marketplace/      # AppCard, AppDetailModal, InstallationProgress, ApiKeyModal
│   ├── memory/           # PersonalityProfile, MemoryList
│   ├── onboarding/       # OnboardingWizard
│   ├── profile/          # User profile
│   ├── security/         # AuditLog, PermissionGrid, DataExport
│   ├── twin/             # Twin overview, blend slider
│   ├── ui/               # Primitives: Button, Badge, GlassPanel, Skeleton, Toggle, Slider, etc.
│   └── voice/            # Voice Twin UI
├── hooks/                # useAuth, useTwin, useMemory, useAudit, useTheme, useCredits, etc.
├── lib/
│   ├── api/              # Typed API clients per domain (auth, twin, marketplace, automation, credits, brain)
│   ├── auth/             # TokenManager
│   ├── validation/       # Form validation helpers
│   ├── api.ts            # Legacy unified api object (use domain clients for new code)
│   ├── query-provider.tsx
│   └── utils.ts          # cn() and shared utilities
└── types/                # TypeScript type definitions per domain
```

## Component Conventions
- One component per file, named exports preferred
- Co-locate component-specific types in the same file
- Use `'use client'` only when client interactivity is required (state, effects, event handlers)
- Props interfaces named `{ComponentName}Props`
- Use `cn()` from `@/lib/utils` for conditional class merging

## Layout Architecture
- `app/dashboard/layout.tsx` — wraps with `QueryProvider` + `AuthProvider`, sets base background
- `app/dashboard/template.tsx` — wraps with `DashboardLayout` + `PageTransition` (use template for route-change animations)
- `DashboardLayout` — composes `Sidebar` + `Header` + scrollable `<main>`
- `Sidebar` — collapsible on desktop, slide-in overlay on mobile with backdrop; active item uses `bg-purple-700 text-white`
- `Header` — top bar with mobile menu trigger, theme toggle, user info

## Dashboard Navigation
Sidebar nav items (in order): Twin, Chat, Apps, Conversations, Automation, Memory, Voice, Security

## Glass Panel Pattern
Use the `GlassPanel` component or the `glass` CSS utility class directly:
```tsx
// Component (animated by default)
<GlassPanel className="p-6">...</GlassPanel>

// Raw utility
<div className="glass p-6">...</div>
```
The `glass` utility adapts automatically to light/dark mode via CSS variables.

## Card / Panel Pattern
Most dashboard panels use this pattern (not GlassPanel):
```tsx
<div className="bg-white dark:bg-[#111113] border border-neutral-200 dark:border-white/10 rounded-3xl p-6 md:p-8 shadow-sm">
```

## Page Layout Pattern
All dashboard pages follow this structure:
```tsx
<div className="min-h-screen bg-[#FBFBFF] dark:bg-[#09090B] p-4 md:p-8 transition-colors duration-300">
  <div className="max-w-7xl mx-auto space-y-6 md:space-y-8">
    <header>...</header>
    <section aria-label="...">...</section>
  </div>
</div>
```

## Button Variants
Use the `Button` component from `@/components/ui/Button`:
- `primary` — `bg-purple-700 text-white hover:bg-purple-600`
- `outline` — `border border-neutral-400 text-neutral-800 hover:bg-purple-100`
- `danger` — `bg-orange-500 text-white hover:bg-orange-600`
- `ghost` — `text-neutral-700 hover:bg-neutral-300`

Button uses Framer Motion `whileHover` scale + `whileTap` scale with spring transition.

## Animation Rules
- Framer Motion for enter/exit animations and micro-interactions
- Transitions ≤ 300ms; prefer `type: 'spring'` over `tween`
- `PageTransition` wraps all dashboard page content
- `GlassPanel` animates with `opacity: 0 → 1, y: 10 → 0` on mount
- Skeleton shimmer via `.shimmer` CSS class for loading states

## Dark Mode
- Dark mode toggled via `.dark` class on `<html>` (managed by `useTheme` hook, persisted to localStorage)
- Always provide both light and dark variants: `bg-white dark:bg-[#111113]`
- Use CSS variables (`var(--background)`, `var(--sidebar-bg)`, `var(--text-primary)`, etc.) for theme-sensitive values
- Never hardcode colors that need to change between modes

## API Integration
- Use TanStack Query (`useQuery`, `useMutation`) for all server state
- Domain API clients live in `src/lib/api/` — use these for new code, not the legacy `api.ts`
- All API clients use `apiClient` (Axios instance) from `@/lib/api/client`
- Handle loading, error, and empty states for every data display
- Invalidate relevant query keys after mutations

## Authentication
- `AuthProvider` wraps the app; use `useAuth()` hook to access `user`, `isAuthenticated`, `login`, `logout`
- Tokens managed by `TokenManager` in `@/lib/auth/token-manager`
- Protected routes redirect to `/auth/login?returnUrl=...`

## Accessibility (Required)
- All interactive elements keyboard accessible
- Semantic HTML (`<header>`, `<main>`, `<nav>`, `<section>`, `<ul>`, `<li>`)
- ARIA labels on icon-only buttons (`aria-label`)
- `aria-current="page"` on active nav items
- `role="status"` + `aria-live="polite"` on dynamic count/status text
- `role="alert"` on error/warning banners
- `sr-only` for screen-reader-only text

## Safety UI (Critical)
- Kill-switch status shown prominently on Security page and Twin Overview
- Kill-switch active state uses `role="alert"` with red warning styling
- Audit log entries display: action type, target integration, timestamp, cognitive blend %, outcome badge
- Actions requiring approval show clear warning states before execution

## App Marketplace
- Integration types fetched via `marketplaceApi.getIntegrationTypes()` with category + search filters
- Install flow: `installIntegration()` → check `auth_type` → OAuth redirect OR API key modal
- Installation progress tracked via `InstallationProgress` component polling `getInstallationProgress()`
- After install/uninstall, invalidate `['integrationTypes']` query key
- App cards in a responsive `grid-cols-1 md:grid-cols-2 lg:grid-cols-3` grid
- Skeleton loading: render `AppCardSkeleton` × 6 while fetching

## Search Inputs Pattern
```tsx
<div className="relative">
  <SearchIcon className="absolute left-4 top-1/2 -translate-y-1/2 w-5 h-5 text-neutral-400 dark:text-neutral-500" />
  <input
    className="w-full pl-12 pr-4 py-3.5 bg-neutral-50 dark:bg-black/20 border border-neutral-200 dark:border-white/10 rounded-2xl text-[15px] focus:outline-none focus:ring-2 focus:ring-neutral-900 dark:focus:ring-white focus:border-transparent transition-all"
  />
</div>
```

## Filter Pill / Tab Pattern
Active state: `bg-neutral-900 text-white dark:bg-white dark:text-black`
Inactive state: `bg-white dark:bg-white/5 border border-neutral-200 dark:border-white/5 text-neutral-600 dark:text-neutral-300 hover:bg-neutral-50 dark:hover:bg-white/10`
