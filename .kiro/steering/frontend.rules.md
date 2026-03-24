---
inclusion: fileMatch
fileMatchPattern: ['neuro-frontend/**/*.ts', 'neuro-frontend/**/*.tsx', 'neuro-frontend/**/*.css']
---

# NeuroTwin Frontend Rules

## Tech Stack
- Next.js (App Router) with TypeScript strict mode
- Tailwind CSS + Framer Motion for animations
- react-icons for iconography

## Directory Structure
```
neuro-frontend/src/
├── app/           # Next.js App Router pages
├── components/    # UI primitives, dashboard, twin, automation, memory, voice
├── hooks/         # Custom React hooks
├── lib/           # Utilities and API clients
├── types/         # TypeScript type definitions
└── styles/        # Global styles
```

## Component Conventions
- One component per file, named exports preferred
- Co-locate component-specific types in same file
- Use `use client` only when client interactivity required
- Props interfaces: `{ComponentName}Props`

## Design Tokens
| Token | Value |
|-------|-------|
| Primary | `#4A3AFF` (purple-700, cognitive purple) |
| Accent | `#897FFF` (purple-600, hover/focus states) |
| Surface | Glass panels with `backdrop-blur` |
| Radius | `rounded-xl` cards, `rounded-lg` inputs |

## Glass Panel Pattern
```tsx
className="bg-white/10 backdrop-blur-md border border-white/20 rounded-xl"
```

## Animation Rules
- Framer Motion for enter/exit animations
- Transitions under 300ms
- Prefer `spring` over `tween`

## Dashboard Layout
- Fixed sidebar (left): Navigation (Twin, Chat, Automation, Memory, Voice, Settings, Security)
- Main workspace (right): Context-dependent panels
- Cognitive command center design, not chat UI

## Key Panels
1. **Twin Overview**: Cognitive Blend, Learning Confidence, Connected Apps, Kill-switch
2. **Activity Stream**: Real-time Twin actions with status indicators
3. **Automation Hub**: Visual node-based workflow builder
4. **Memory Panel**: Personality profile, learning events, editable entries
5. **Voice Twin**: Phone assignment, call history, personality slider
6. **Security**: Audit logs, per-app permissions, data export

## Safety UI (Critical)
- Kill-switch prominently accessible from Twin Overview and Voice panels
- Actions requiring approval show clear warning states
- Audit logs display timestamp, action type, outcome
- Cognitive Blend slider shows current percentage value

## API Integration
- React Query or SWR for data fetching
- API client in `lib/api.ts` with typed endpoints
- Handle loading, error, empty states for all data displays
- Optimistic updates for user-initiated actions

## Accessibility (Required)
- Keyboard accessible interactive elements
- Semantic HTML elements
- ARIA labels for icon-only buttons
- WCAG AA color contrast minimum

## Apps Marketplace

### Structure
Users browse, install, and configure integrations (WhatsApp, Discord, Excel, etc.) to extend Twin capabilities.

### App Card Display
- Icon + name + short description
- Status badge: Installed / Not Installed / Needs Attention
- Actions: Install (not installed) or Configure/Remove (installed)

### Configuration Modal
After install, show permissions panel:
- Permission toggles (Read, Send, Auto-Respond, etc.)
- Save/Disconnect actions

### API Endpoints
```
GET    /api/apps              # List all apps
POST   /api/apps/install      # Install app
GET    /api/apps/{id}         # Get app details
PUT    /api/apps/{id}/settings # Update settings
DELETE /api/apps/{id}         # Uninstall app
```

### App Data Model
| Field | Purpose |
|-------|---------|
| id | Unique identifier |
| name | Display name |
| icon | Icon reference |
| description | Short explanation |
| installed | Boolean status |
| config | JSON permissions/settings |
| scopes | OAuth scopes required |

### Install Flow
1. User clicks Install
2. OAuth redirect if required (Discord, WhatsApp Business, etc.)
3. Backend stores app config
4. UI updates to installed state with settings panel
