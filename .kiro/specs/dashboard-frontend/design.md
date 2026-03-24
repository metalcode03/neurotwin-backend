# Design Document: NeuroTwin Dashboard Frontend

## Overview

The NeuroTwin Dashboard Frontend is a Next.js 14+ application using the App Router pattern, providing an authenticated cognitive command center for managing the NeuroTwin platform. The design follows a glass morphism aesthetic with the NeuroTwin purple color palette, emphasizing safety controls and real-time feedback.

Key design principles:
- **Cognitive Command Center**: Dashboard-first design, not chat UI
- **Safety First**: Kill-switch and approval controls always accessible
- **Glass Morphism**: Elevated surfaces with backdrop blur for modern aesthetic
- **Real-time Updates**: Live activity stream and instant feedback
- **Accessibility**: WCAG AA compliant with full keyboard navigation

## Architecture

```mermaid
graph TB
    subgraph "Next.js App Router"
        LAYOUT[Root Layout]
        DASHBOARD[Dashboard Layout]
        
        subgraph "Pages"
            TWIN[/dashboard/twin]
            CHAT[/dashboard/chat]
            APPS[/dashboard/apps]
            AUTO[/dashboard/automation]
            MEM[/dashboard/memory]
            VOICE[/dashboard/voice]
            SEC[/dashboard/security]
            SET[/dashboard/settings]
        end
    end

    subgraph "Components"
        SIDEBAR[Sidebar]
        GLASS[GlassPanel]
        SLIDER[CognitiveBlendSlider]
        KILL[KillSwitch]
        STREAM[ActivityStream]
        APPCARD[AppCard]
        MODAL[ConfigModal]
    end

    subgraph "State Layer"
        RQ[React Query]
        CONTEXT[Auth Context]
        STORE[UI State]
    end

    subgraph "API Layer"
        CLIENT[API Client]
        AUTH[Auth Interceptor]
    end

    subgraph "Backend API"
        API[Django REST API]
    end

    LAYOUT --> DASHBOARD
    DASHBOARD --> SIDEBAR
    DASHBOARD --> TWIN
    DASHBOARD --> CHAT
    DASHBOARD --> APPS
    DASHBOARD --> AUTO
    DASHBOARD --> MEM
    DASHBOARD --> VOICE
    DASHBOARD --> SEC
    DASHBOARD --> SET

    TWIN --> GLASS
    TWIN --> SLIDER
    TWIN --> KILL
    TWIN --> STREAM

    APPS --> APPCARD
    APPS --> MODAL

    RQ --> CLIENT
    CLIENT --> AUTH
    AUTH --> API
    CONTEXT --> AUTH
```

## Components and Interfaces

### 1. Directory Structure

```
neuro-frontend/src/
├── app/
│   ├── layout.tsx                 # Root layout with providers
│   ├── page.tsx                   # Redirect to /dashboard/twin
│   └── dashboard/
│       ├── layout.tsx             # Dashboard layout with sidebar
│       ├── twin/page.tsx          # Twin overview
│       ├── chat/page.tsx          # Chat interface
│       ├── apps/page.tsx          # Apps marketplace
│       ├── automation/page.tsx    # Automation hub
│       ├── memory/page.tsx        # Memory panel
│       ├── voice/page.tsx         # Voice twin
│       ├── security/page.tsx      # Security & audit
│       └── settings/page.tsx      # User settings
├── components/
│   ├── ui/                        # Primitive UI components
│   │   ├── GlassPanel.tsx
│   │   ├── Button.tsx
│   │   ├── Toggle.tsx
│   │   ├── Slider.tsx
│   │   ├── Badge.tsx
│   │   ├── Modal.tsx
│   │   └── Input.tsx
│   ├── layout/
│   │   ├── Sidebar.tsx
│   │   ├── SidebarItem.tsx
│   │   └── MainContent.tsx
│   ├── twin/
│   │   ├── TwinOverview.tsx
│   │   ├── CognitiveBlendSlider.tsx
│   │   ├── KillSwitch.tsx
│   │   └── ActivityStream.tsx
│   ├── apps/
│   │   ├── AppCard.tsx
│   │   ├── AppGrid.tsx
│   │   ├── AppSearch.tsx
│   │   ├── AppTabs.tsx
│   │   └── ConfigModal.tsx
│   ├── memory/
│   │   ├── MemoryList.tsx
│   │   ├── MemoryEntry.tsx
│   │   └── PersonalityProfile.tsx
│   ├── voice/
│   │   ├── VoiceStatus.tsx
│   │   ├── CallHistory.tsx
│   │   └── VoiceKillSwitch.tsx
│   └── security/
│       ├── AuditLog.tsx
│       ├── PermissionGrid.tsx
│       └── DataExport.tsx
├── hooks/
│   ├── useAuth.ts
│   ├── useTwin.ts
│   ├── useApps.ts
│   ├── useActivity.ts
│   ├── useMemory.ts
│   ├── useVoice.ts
│   └── useAudit.ts
├── lib/
│   ├── api.ts                     # API client with typed endpoints
│   ├── auth.ts                    # Auth utilities
│   └── utils.ts                   # General utilities
├── types/
│   ├── twin.ts
│   ├── apps.ts
│   ├── activity.ts
│   ├── memory.ts
│   ├── voice.ts
│   └── api.ts
└── styles/
    └── globals.css                # Global styles with Tailwind
```

### 2. Core UI Components

#### GlassPanel Component

```typescript
// components/ui/GlassPanel.tsx
'use client';

import { motion, HTMLMotionProps } from 'framer-motion';
import { cn } from '@/lib/utils';

export interface GlassPanelProps extends HTMLMotionProps<'div'> {
  children: React.ReactNode;
  className?: string;
  animate?: boolean;
}

export function GlassPanel({ 
  children, 
  className, 
  animate = true,
  ...props 
}: GlassPanelProps) {
  const Component = animate ? motion.div : 'div';
  
  return (
    <Component
      className={cn(
        'bg-white/70 backdrop-blur-xl border border-neutral-400/40 shadow-lg rounded-xl',
        className
      )}
      initial={animate ? { opacity: 0, y: 10 } : undefined}
      animate={animate ? { opacity: 1, y: 0 } : undefined}
      transition={{ duration: 0.2, type: 'spring' }}
      {...props}
    >
      {children}
    </Component>
  );
}
```

#### Button Component

```typescript
// components/ui/Button.tsx
'use client';

import { forwardRef, ButtonHTMLAttributes } from 'react';
import { cn } from '@/lib/utils';

export interface ButtonProps extends ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: 'primary' | 'outline' | 'danger' | 'ghost';
  size?: 'sm' | 'md' | 'lg';
}

export const Button = forwardRef<HTMLButtonElement, ButtonProps>(
  ({ className, variant = 'primary', size = 'md', ...props }, ref) => {
    const variants = {
      primary: 'bg-purple-700 text-white hover:bg-purple-600 focus:ring-purple-600',
      outline: 'border border-neutral-400 text-neutral-800 hover:bg-purple-100',
      danger: 'bg-red-600 text-white hover:bg-red-700 focus:ring-red-600',
      ghost: 'text-neutral-700 hover:bg-neutral-300',
    };

    const sizes = {
      sm: 'px-3 py-1.5 text-sm',
      md: 'px-4 py-2 text-base',
      lg: 'px-6 py-3 text-lg',
    };

    return (
      <button
        ref={ref}
        className={cn(
          'rounded-lg font-medium transition-colors focus:outline-none focus:ring-2 focus:ring-offset-2',
          variants[variant],
          sizes[size],
          className
        )}
        {...props}
      />
    );
  }
);

Button.displayName = 'Button';
```

#### Slider Component

```typescript
// components/ui/Slider.tsx
'use client';

import { useState, useCallback } from 'react';
import { cn } from '@/lib/utils';

export interface SliderProps {
  value: number;
  onChange: (value: number) => void;
  min?: number;
  max?: number;
  step?: number;
  label?: string;
  showValue?: boolean;
  className?: string;
  'aria-label'?: string;
}

export function Slider({
  value,
  onChange,
  min = 0,
  max = 100,
  step = 1,
  label,
  showValue = true,
  className,
  'aria-label': ariaLabel,
}: SliderProps) {
  const percentage = ((value - min) / (max - min)) * 100;

  return (
    <div className={cn('w-full', className)}>
      {label && (
        <label className="block text-sm font-medium text-neutral-700 mb-2">
          {label}
        </label>
      )}
      <div className="flex items-center gap-4">
        <input
          type="range"
          min={min}
          max={max}
          step={step}
          value={value}
          onChange={(e) => onChange(Number(e.target.value))}
          aria-label={ariaLabel || label}
          className="w-full h-2 bg-neutral-300 rounded-lg appearance-none cursor-pointer
                     [&::-webkit-slider-thumb]:appearance-none
                     [&::-webkit-slider-thumb]:w-5
                     [&::-webkit-slider-thumb]:h-5
                     [&::-webkit-slider-thumb]:bg-purple-700
                     [&::-webkit-slider-thumb]:rounded-full
                     [&::-webkit-slider-thumb]:cursor-pointer
                     [&::-webkit-slider-thumb]:transition-transform
                     [&::-webkit-slider-thumb]:hover:scale-110"
          style={{
            background: `linear-gradient(to right, #4A3AFF ${percentage}%, #D9DBE9 ${percentage}%)`,
          }}
        />
        {showValue && (
          <span className="text-lg font-semibold text-purple-700 min-w-[3rem] text-right">
            {value}%
          </span>
        )}
      </div>
    </div>
  );
}
```

### 3. Layout Components

#### Sidebar Component

```typescript
// components/layout/Sidebar.tsx
'use client';

import { usePathname } from 'next/navigation';
import Link from 'next/link';
import { motion } from 'framer-motion';
import { 
  FaBrain, FaComments, FaPuzzlePiece, FaSyncAlt, 
  FaDatabase, FaMicrophone, FaShieldAlt, FaCog 
} from 'react-icons/fa';
import { cn } from '@/lib/utils';

interface NavItem {
  href: string;
  icon: React.ComponentType<{ className?: string }>;
  label: string;
}

const navItems: NavItem[] = [
  { href: '/dashboard/twin', icon: FaBrain, label: 'Twin' },
  { href: '/dashboard/chat', icon: FaComments, label: 'Chat' },
  { href: '/dashboard/apps', icon: FaPuzzlePiece, label: 'Apps' },
  { href: '/dashboard/automation', icon: FaSyncAlt, label: 'Automation' },
  { href: '/dashboard/memory', icon: FaDatabase, label: 'Memory' },
  { href: '/dashboard/voice', icon: FaMicrophone, label: 'Voice' },
  { href: '/dashboard/security', icon: FaShieldAlt, label: 'Security' },
  { href: '/dashboard/settings', icon: FaCog, label: 'Settings' },
];

export function Sidebar() {
  const pathname = usePathname();

  return (
    <nav 
      className="fixed left-0 top-0 h-screen w-64 bg-neutral-800 text-white flex flex-col"
      aria-label="Main navigation"
    >
      <div className="p-6">
        <h1 className="text-xl font-bold text-purple-400">NeuroTwin</h1>
      </div>
      
      <ul className="flex-1 px-3 space-y-1">
        {navItems.map((item) => {
          const isActive = pathname === item.href;
          const Icon = item.icon;
          
          return (
            <li key={item.href}>
              <Link
                href={item.href}
                className={cn(
                  'flex items-center gap-3 px-4 py-3 rounded-lg transition-colors',
                  'hover:bg-white/10 focus:outline-none focus:ring-2 focus:ring-purple-600',
                  isActive && 'bg-purple-700 text-white'
                )}
                aria-current={isActive ? 'page' : undefined}
              >
                <Icon className="w-5 h-5" aria-hidden="true" />
                <span>{item.label}</span>
                {isActive && (
                  <motion.div
                    layoutId="activeIndicator"
                    className="absolute left-0 w-1 h-8 bg-purple-400 rounded-r"
                  />
                )}
              </Link>
            </li>
          );
        })}
      </ul>
    </nav>
  );
}
```

#### Dashboard Layout

```typescript
// app/dashboard/layout.tsx
import { Sidebar } from '@/components/layout/Sidebar';
import { AuthProvider } from '@/hooks/useAuth';
import { QueryProvider } from '@/lib/query-provider';

export default function DashboardLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <QueryProvider>
      <AuthProvider>
        <div className="min-h-screen bg-neutral-200">
          <Sidebar />
          <main className="ml-64 p-6">
            {children}
          </main>
        </div>
      </AuthProvider>
    </QueryProvider>
  );
}
```

### 4. Twin Components

#### CognitiveBlendSlider Component

```typescript
// components/twin/CognitiveBlendSlider.tsx
'use client';

import { useState } from 'react';
import { motion } from 'framer-motion';
import { Slider } from '@/components/ui/Slider';
import { GlassPanel } from '@/components/ui/GlassPanel';
import { cn } from '@/lib/utils';

export interface CognitiveBlendSliderProps {
  value: number;
  onChange: (value: number) => void;
  isLoading?: boolean;
}

function getBlendRange(value: number): { label: string; color: string; description: string } {
  if (value <= 30) {
    return {
      label: 'AI Logic',
      color: 'text-blue-600',
      description: 'Pure AI reasoning with minimal personality',
    };
  }
  if (value <= 70) {
    return {
      label: 'Balanced',
      color: 'text-purple-600',
      description: 'Balanced blend of personality and AI',
    };
  }
  return {
    label: 'Human Mimicry',
    color: 'text-orange-600',
    description: 'Heavy personality mimicry',
  };
}

export function CognitiveBlendSlider({ 
  value, 
  onChange, 
  isLoading 
}: CognitiveBlendSliderProps) {
  const range = getBlendRange(value);
  const showWarning = value > 80;

  return (
    <GlassPanel className="p-6">
      <h3 className="text-lg font-semibold text-neutral-800 mb-4">
        Cognitive Blend
      </h3>
      
      <Slider
        value={value}
        onChange={onChange}
        min={0}
        max={100}
        aria-label="Cognitive Blend percentage"
      />
      
      <div className="mt-4 flex items-center justify-between">
        <div>
          <span className={cn('font-medium', range.color)}>
            {range.label}
          </span>
          <p className="text-sm text-neutral-600 mt-1">
            {range.description}
          </p>
        </div>
        
        {/* Range indicators */}
        <div className="flex gap-2 text-xs">
          <span className="px-2 py-1 bg-blue-100 text-blue-700 rounded">0-30%</span>
          <span className="px-2 py-1 bg-purple-100 text-purple-700 rounded">31-70%</span>
          <span className="px-2 py-1 bg-orange-100 text-orange-700 rounded">71-100%</span>
        </div>
      </div>
      
      {showWarning && (
        <motion.div
          initial={{ opacity: 0, height: 0 }}
          animate={{ opacity: 1, height: 'auto' }}
          className="mt-4 p-3 bg-orange-100 border border-orange-300 rounded-lg"
        >
          <p className="text-sm text-orange-800">
            ⚠️ Actions will require your confirmation before execution
          </p>
        </motion.div>
      )}
    </GlassPanel>
  );
}
```

#### KillSwitch Component

```typescript
// components/twin/KillSwitch.tsx
'use client';

import { useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { FaStop, FaPlay } from 'react-icons/fa';
import { Button } from '@/components/ui/Button';
import { GlassPanel } from '@/components/ui/GlassPanel';

export interface KillSwitchProps {
  isActive: boolean;
  onActivate: () => Promise<void>;
  onDeactivate: () => Promise<void>;
}

export function KillSwitch({ isActive, onActivate, onDeactivate }: KillSwitchProps) {
  const [isLoading, setIsLoading] = useState(false);
  const [showConfirm, setShowConfirm] = useState(false);

  const handleToggle = async () => {
    if (!isActive && !showConfirm) {
      setShowConfirm(true);
      return;
    }
    
    setIsLoading(true);
    try {
      if (isActive) {
        await onDeactivate();
      } else {
        await onActivate();
        setShowConfirm(false);
      }
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <GlassPanel className="p-6">
      <div className="flex items-center justify-between">
        <div>
          <h3 className="text-lg font-semibold text-neutral-800">
            Kill Switch
          </h3>
          <p className="text-sm text-neutral-600 mt-1">
            {isActive ? 'Twin is paused' : 'Twin is active'}
          </p>
        </div>
        
        <Button
          variant={isActive ? 'primary' : 'danger'}
          onClick={handleToggle}
          disabled={isLoading}
          aria-label={isActive ? 'Re-enable Twin' : 'Stop all Twin automations'}
        >
          {isActive ? (
            <>
              <FaPlay className="mr-2" aria-hidden="true" />
              Re-enable
            </>
          ) : (
            <>
              <FaStop className="mr-2" aria-hidden="true" />
              Stop Twin
            </>
          )}
        </Button>
      </div>
      
      <AnimatePresence>
        {showConfirm && !isActive && (
          <motion.div
            initial={{ opacity: 0, height: 0 }}
            animate={{ opacity: 1, height: 'auto' }}
            exit={{ opacity: 0, height: 0 }}
            className="mt-4 p-4 bg-red-50 border border-red-200 rounded-lg"
          >
            <p className="text-sm text-red-800 mb-3">
              This will immediately halt all Twin automations and terminate active calls.
            </p>
            <div className="flex gap-2">
              <Button variant="danger" onClick={handleToggle} disabled={isLoading}>
                Confirm Stop
              </Button>
              <Button variant="outline" onClick={() => setShowConfirm(false)}>
                Cancel
              </Button>
            </div>
          </motion.div>
        )}
      </AnimatePresence>
      
      {isActive && (
        <motion.div
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          className="mt-4 p-3 bg-yellow-100 border border-yellow-300 rounded-lg"
        >
          <p className="text-sm text-yellow-800">
            🛑 Twin Paused — No automated actions will be performed
          </p>
        </motion.div>
      )}
    </GlassPanel>
  );
}
```

#### ActivityStream Component

```typescript
// components/twin/ActivityStream.tsx
'use client';

import { useEffect, useRef } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { FaCheck, FaClock, FaTimes, FaExclamationTriangle } from 'react-icons/fa';
import { GlassPanel } from '@/components/ui/GlassPanel';
import { Button } from '@/components/ui/Button';
import { Activity, ActivityStatus } from '@/types/activity';
import { formatRelativeTime } from '@/lib/utils';

export interface ActivityStreamProps {
  activities: Activity[];
  onApprove?: (id: string) => void;
  onReject?: (id: string) => void;
  onLoadMore?: () => void;
  hasMore?: boolean;
  isLoading?: boolean;
}

const statusConfig: Record<ActivityStatus, { icon: React.ComponentType; color: string; label: string }> = {
  success: { icon: FaCheck, color: 'text-green-600 bg-green-100', label: 'Success' },
  pending: { icon: FaClock, color: 'text-yellow-600 bg-yellow-100', label: 'Pending' },
  failed: { icon: FaTimes, color: 'text-red-600 bg-red-100', label: 'Failed' },
  awaiting_approval: { icon: FaExclamationTriangle, color: 'text-orange-600 bg-orange-100', label: 'Awaiting Approval' },
};

export function ActivityStream({
  activities,
  onApprove,
  onReject,
  onLoadMore,
  hasMore,
  isLoading,
}: ActivityStreamProps) {
  const containerRef = useRef<HTMLDivElement>(null);

  return (
    <GlassPanel className="p-6">
      <h3 className="text-lg font-semibold text-neutral-800 mb-4">
        Activity Stream
      </h3>
      
      <div 
        ref={containerRef}
        className="space-y-3 max-h-96 overflow-y-auto"
        role="log"
        aria-live="polite"
        aria-label="Twin activity stream"
      >
        <AnimatePresence mode="popLayout">
          {activities.map((activity) => {
            const status = statusConfig[activity.status];
            const StatusIcon = status.icon;
            
            return (
              <motion.div
                key={activity.id}
                initial={{ opacity: 0, x: -20 }}
                animate={{ opacity: 1, x: 0 }}
                exit={{ opacity: 0, x: 20 }}
                className="flex items-start gap-3 p-3 bg-white/50 rounded-lg"
              >
                <div className={`p-2 rounded-full ${status.color}`}>
                  <StatusIcon className="w-4 h-4" aria-hidden="true" />
                </div>
                
                <div className="flex-1 min-w-0">
                  <p className="text-sm font-medium text-neutral-800 truncate">
                    {activity.description}
                  </p>
                  <p className="text-xs text-neutral-600 mt-1">
                    {activity.integration} • {formatRelativeTime(activity.timestamp)}
                  </p>
                  
                  {activity.status === 'awaiting_approval' && (
                    <div className="flex gap-2 mt-2">
                      <Button 
                        size="sm" 
                        variant="primary"
                        onClick={() => onApprove?.(activity.id)}
                      >
                        Approve
                      </Button>
                      <Button 
                        size="sm" 
                        variant="outline"
                        onClick={() => onReject?.(activity.id)}
                      >
                        Reject
                      </Button>
                    </div>
                  )}
                </div>
                
                <span className="sr-only">{status.label}</span>
              </motion.div>
            );
          })}
        </AnimatePresence>
        
        {hasMore && (
          <Button
            variant="ghost"
            onClick={onLoadMore}
            disabled={isLoading}
            className="w-full"
          >
            {isLoading ? 'Loading...' : 'Load more'}
          </Button>
        )}
      </div>
    </GlassPanel>
  );
}
```

### 5. Apps Marketplace Components

#### AppCard Component

```typescript
// components/apps/AppCard.tsx
'use client';

import { motion } from 'framer-motion';
import { IconType } from 'react-icons';
import { GlassPanel } from '@/components/ui/GlassPanel';
import { Button } from '@/components/ui/Button';
import { Badge } from '@/components/ui/Badge';
import { App, AppStatus } from '@/types/apps';

export interface AppCardProps {
  app: App;
  onInstall: (appId: string) => void;
  onConfigure: (appId: string) => void;
  isLoading?: boolean;
}

const statusStyles: Record<AppStatus, { variant: 'success' | 'default' | 'warning'; label: string }> = {
  installed: { variant: 'success', label: 'Installed' },
  not_installed: { variant: 'default', label: 'Not Installed' },
  needs_attention: { variant: 'warning', label: 'Needs Attention' },
};

export function AppCard({ app, onInstall, onConfigure, isLoading }: AppCardProps) {
  const status = statusStyles[app.status];
  const Icon = app.icon as IconType;

  return (
    <motion.div
      whileHover={{ y: -4, boxShadow: '0 10px 40px rgba(0,0,0,0.1)' }}
      transition={{ type: 'spring', stiffness: 300 }}
    >
      <GlassPanel className="p-5 h-full flex flex-col">
        <div className="flex items-start gap-4">
          <div className="p-3 bg-purple-100 rounded-xl">
            <Icon className="w-6 h-6 text-purple-700" aria-hidden="true" />
          </div>
          
          <div className="flex-1 min-w-0">
            <h4 className="font-semibold text-neutral-800 truncate">
              {app.name}
            </h4>
            <Badge variant={status.variant} className="mt-1">
              {status.label}
            </Badge>
          </div>
        </div>
        
        <p className="text-sm text-neutral-600 mt-3 flex-1">
          {app.description}
        </p>
        
        <div className="mt-4">
          {app.status === 'installed' || app.status === 'needs_attention' ? (
            <Button
              variant="outline"
              onClick={() => onConfigure(app.id)}
              disabled={isLoading}
              className="w-full"
            >
              Configure
            </Button>
          ) : (
            <Button
              variant="primary"
              onClick={() => onInstall(app.id)}
              disabled={isLoading}
              className="w-full"
            >
              Install
            </Button>
          )}
        </div>
      </GlassPanel>
    </motion.div>
  );
}
```

#### ConfigModal Component

```typescript
// components/apps/ConfigModal.tsx
'use client';

import { useState, useEffect } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { FaTimes } from 'react-icons/fa';
import { IconType } from 'react-icons';
import { Button } from '@/components/ui/Button';
import { Toggle } from '@/components/ui/Toggle';
import { App, AppPermissions } from '@/types/apps';

export interface ConfigModalProps {
  app: App | null;
  isOpen: boolean;
  onClose: () => void;
  onSave: (appId: string, permissions: AppPermissions) => Promise<void>;
  onDisconnect: (appId: string) => Promise<void>;
}

export function ConfigModal({ 
  app, 
  isOpen, 
  onClose, 
  onSave, 
  onDisconnect 
}: ConfigModalProps) {
  const [permissions, setPermissions] = useState<AppPermissions>({
    read: false,
    write: false,
    autoRespond: false,
  });
  const [isLoading, setIsLoading] = useState(false);

  useEffect(() => {
    if (app?.config) {
      setPermissions(app.config);
    }
  }, [app]);

  const handleSave = async () => {
    if (!app) return;
    setIsLoading(true);
    try {
      await onSave(app.id, permissions);
      onClose();
    } finally {
      setIsLoading(false);
    }
  };

  const handleDisconnect = async () => {
    if (!app) return;
    setIsLoading(true);
    try {
      await onDisconnect(app.id);
      onClose();
    } finally {
      setIsLoading(false);
    }
  };

  const Icon = app?.icon as IconType;

  return (
    <AnimatePresence>
      {isOpen && (
        <>
          {/* Backdrop */}
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            className="fixed inset-0 bg-black/30 backdrop-blur-sm z-40"
            onClick={onClose}
            aria-hidden="true"
          />
          
          {/* Modal */}
          <motion.div
            initial={{ x: '100%' }}
            animate={{ x: 0 }}
            exit={{ x: '100%' }}
            transition={{ type: 'spring', damping: 25, stiffness: 300 }}
            className="fixed right-0 top-0 h-full w-96 bg-white shadow-2xl z-50"
            role="dialog"
            aria-modal="true"
            aria-labelledby="config-modal-title"
          >
            <div className="flex flex-col h-full">
              {/* Header */}
              <div className="flex items-center justify-between p-6 border-b border-neutral-300">
                <div className="flex items-center gap-3">
                  {Icon && (
                    <div className="p-2 bg-purple-100 rounded-lg">
                      <Icon className="w-5 h-5 text-purple-700" aria-hidden="true" />
                    </div>
                  )}
                  <h2 id="config-modal-title" className="text-lg font-semibold text-neutral-800">
                    {app?.name}
                  </h2>
                </div>
                <button
                  onClick={onClose}
                  className="p-2 hover:bg-neutral-100 rounded-lg transition-colors"
                  aria-label="Close configuration"
                >
                  <FaTimes className="w-5 h-5 text-neutral-600" />
                </button>
              </div>
              
              {/* Content */}
              <div className="flex-1 p-6 space-y-6 overflow-y-auto">
                <div>
                  <h3 className="text-sm font-medium text-neutral-700 mb-4">
                    Permissions
                  </h3>
                  
                  <div className="space-y-4">
                    <Toggle
                      label="Read"
                      description="Allow Twin to read data from this app"
                      checked={permissions.read}
                      onChange={(checked) => setPermissions(p => ({ ...p, read: checked }))}
                    />
                    <Toggle
                      label="Write"
                      description="Allow Twin to create or modify data"
                      checked={permissions.write}
                      onChange={(checked) => setPermissions(p => ({ ...p, write: checked }))}
                    />
                    <Toggle
                      label="Auto Respond"
                      description="Allow Twin to send messages automatically"
                      checked={permissions.autoRespond}
                      onChange={(checked) => setPermissions(p => ({ ...p, autoRespond: checked }))}
                    />
                  </div>
                </div>
              </div>
              
              {/* Footer */}
              <div className="p-6 border-t border-neutral-300 space-y-3">
                <Button
                  variant="primary"
                  onClick={handleSave}
                  disabled={isLoading}
                  className="w-full"
                >
                  Save Changes
                </Button>
                <Button
                  variant="outline"
                  onClick={handleDisconnect}
                  disabled={isLoading}
                  className="w-full text-red-600 border-red-300 hover:bg-red-50"
                >
                  Disconnect App
                </Button>
              </div>
            </div>
          </motion.div>
        </>
      )}
    </AnimatePresence>
  );
}
```

### 6. API Client and Hooks

#### API Client

```typescript
// lib/api.ts
import { 
  Twin, TwinUpdateRequest,
  App, AppPermissions,
  Activity,
  Memory,
  VoiceProfile, CallRecord,
  AuditEntry, PermissionScope,
  Subscription
} from '@/types';

const API_BASE = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000/api/v1';

class ApiError extends Error {
  constructor(public status: number, message: string) {
    super(message);
    this.name = 'ApiError';
  }
}

async function request<T>(
  endpoint: string,
  options: RequestInit = {}
): Promise<T> {
  const token = typeof window !== 'undefined' 
    ? localStorage.getItem('auth_token') 
    : null;

  const response = await fetch(`${API_BASE}${endpoint}`, {
    ...options,
    headers: {
      'Content-Type': 'application/json',
      ...(token && { Authorization: `Bearer ${token}` }),
      ...options.headers,
    },
  });

  if (!response.ok) {
    if (response.status === 401) {
      // Token expired, redirect to login
      if (typeof window !== 'undefined') {
        localStorage.removeItem('auth_token');
        window.location.href = '/login';
      }
    }
    const error = await response.json().catch(() => ({ message: 'Request failed' }));
    throw new ApiError(response.status, error.message);
  }

  return response.json();
}

export const api = {
  // Twin endpoints
  twin: {
    get: () => request<Twin>('/twin'),
    updateBlend: (blend: number) => 
      request<Twin>('/twin/blend', { method: 'PATCH', body: JSON.stringify({ cognitive_blend: blend }) }),
  },

  // Kill switch endpoints
  killSwitch: {
    activate: () => request<void>('/kill-switch/activate', { method: 'POST' }),
    deactivate: () => request<void>('/kill-switch/deactivate', { method: 'POST' }),
  },

  // Apps endpoints
  apps: {
    list: () => request<App[]>('/integrations'),
    install: (type: string) => 
      request<App>(`/integrations/${type}/connect`, { method: 'POST' }),
    configure: (id: string, permissions: AppPermissions) =>
      request<App>(`/integrations/${id}/permissions`, { method: 'PATCH', body: JSON.stringify(permissions) }),
    disconnect: (id: string) =>
      request<void>(`/integrations/${id}`, { method: 'DELETE' }),
  },

  // Activity endpoints
  activity: {
    list: (page = 1) => request<{ items: Activity[]; hasMore: boolean }>(`/audit?page=${page}`),
    approve: (id: string) => request<void>(`/actions/${id}/approve`, { method: 'POST' }),
    reject: (id: string) => request<void>(`/actions/${id}/reject`, { method: 'POST' }),
  },

  // Memory endpoints
  memory: {
    list: (query?: string) => request<Memory[]>(`/memory${query ? `?q=${query}` : ''}`),
    get: (id: string) => request<Memory>(`/memory/${id}`),
  },

  // Voice endpoints
  voice: {
    getProfile: () => request<VoiceProfile>('/voice'),
    getCalls: () => request<CallRecord[]>('/voice/calls'),
    approveSession: () => request<void>('/voice/approve-session', { method: 'POST' }),
    terminateCall: (id: string) => request<void>(`/voice/call/${id}`, { method: 'DELETE' }),
  },

  // Security endpoints
  security: {
    getAuditLog: (filters?: Record<string, string>) => {
      const params = new URLSearchParams(filters);
      return request<AuditEntry[]>(`/audit?${params}`);
    },
    getPermissions: () => request<PermissionScope[]>('/permissions'),
    updatePermissions: (permissions: PermissionScope[]) =>
      request<void>('/permissions', { method: 'PATCH', body: JSON.stringify(permissions) }),
  },

  // Subscription endpoints
  subscription: {
    get: () => request<Subscription>('/subscription'),
    upgrade: (tier: string) => 
      request<Subscription>('/subscription/upgrade', { method: 'POST', body: JSON.stringify({ tier }) }),
  },
};
```

#### useTwin Hook

```typescript
// hooks/useTwin.ts
'use client';

import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { api } from '@/lib/api';
import { Twin } from '@/types/twin';

export function useTwin() {
  const queryClient = useQueryClient();

  const twinQuery = useQuery({
    queryKey: ['twin'],
    queryFn: api.twin.get,
  });

  const updateBlendMutation = useMutation({
    mutationFn: api.twin.updateBlend,
    onMutate: async (newBlend) => {
      // Optimistic update
      await queryClient.cancelQueries({ queryKey: ['twin'] });
      const previous = queryClient.getQueryData<Twin>(['twin']);
      queryClient.setQueryData<Twin>(['twin'], (old) => 
        old ? { ...old, cognitive_blend: newBlend } : old
      );
      return { previous };
    },
    onError: (err, newBlend, context) => {
      // Rollback on error
      queryClient.setQueryData(['twin'], context?.previous);
    },
    onSettled: () => {
      queryClient.invalidateQueries({ queryKey: ['twin'] });
    },
  });

  const activateKillSwitchMutation = useMutation({
    mutationFn: api.killSwitch.activate,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['twin'] });
    },
  });

  const deactivateKillSwitchMutation = useMutation({
    mutationFn: api.killSwitch.deactivate,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['twin'] });
    },
  });

  return {
    twin: twinQuery.data,
    isLoading: twinQuery.isLoading,
    error: twinQuery.error,
    updateBlend: updateBlendMutation.mutate,
    isUpdatingBlend: updateBlendMutation.isPending,
    activateKillSwitch: activateKillSwitchMutation.mutateAsync,
    deactivateKillSwitch: deactivateKillSwitchMutation.mutateAsync,
    isKillSwitchLoading: activateKillSwitchMutation.isPending || deactivateKillSwitchMutation.isPending,
  };
}
```

## Data Models

### TypeScript Type Definitions

```typescript
// types/twin.ts
export interface Twin {
  id: string;
  user_id: string;
  model: 'gemini-3-flash' | 'qwen' | 'mistral' | 'gemini-3-pro';
  cognitive_blend: number;
  is_active: boolean;
  kill_switch_active: boolean;
  created_at: string;
  updated_at: string;
}

export interface TwinUpdateRequest {
  cognitive_blend?: number;
  model?: Twin['model'];
}

// types/apps.ts
export type AppStatus = 'installed' | 'not_installed' | 'needs_attention';

export interface AppPermissions {
  read: boolean;
  write: boolean;
  autoRespond: boolean;
}

export interface App {
  id: string;
  name: string;
  icon: string; // react-icons component name
  description: string;
  status: AppStatus;
  config: AppPermissions | null;
  scopes: string[];
}

// types/activity.ts
export type ActivityStatus = 'success' | 'pending' | 'failed' | 'awaiting_approval';

export interface Activity {
  id: string;
  description: string;
  integration: string;
  action_type: string;
  status: ActivityStatus;
  timestamp: string;
  cognitive_blend: number;
  reasoning?: string;
}

// types/memory.ts
export interface Memory {
  id: string;
  content: string;
  source: 'conversation' | 'action' | 'feedback';
  timestamp: string;
  relevance_score?: number;
}

export interface PersonalityProfile {
  personality: {
    openness: number;
    conscientiousness: number;
    extraversion: number;
    agreeableness: number;
    neuroticism: number;
  };
  tone: {
    formality: number;
    warmth: number;
    directness: number;
    humor_level: number;
  };
  communication: {
    preferred_greeting: string;
    sign_off_style: string;
    response_length: 'brief' | 'moderate' | 'detailed';
    emoji_usage: 'none' | 'minimal' | 'moderate' | 'frequent';
  };
}

// types/voice.ts
export interface VoiceProfile {
  id: string;
  phone_number: string | null;
  voice_clone_id: string | null;
  is_approved: boolean;
  approval_expires_at: string | null;
}

export interface CallRecord {
  id: string;
  direction: 'inbound' | 'outbound';
  phone_number: string;
  transcript: string | null;
  duration_seconds: number;
  started_at: string;
  ended_at: string | null;
}

// types/security.ts
export type ActionType = 'read' | 'write' | 'send' | 'delete' | 'financial' | 'legal' | 'call';

export interface PermissionScope {
  integration: string;
  action_type: ActionType;
  is_granted: boolean;
  requires_approval: boolean;
}

export interface AuditEntry {
  id: string;
  timestamp: string;
  action_type: ActionType;
  target_integration: string;
  input_data: Record<string, unknown>;
  outcome: 'success' | 'failure' | 'pending_approval';
  cognitive_blend: number;
  reasoning_chain: string | null;
  is_twin_generated: boolean;
}

// types/subscription.ts
export type SubscriptionTier = 'free' | 'pro' | 'twin_plus' | 'executive';

export interface Subscription {
  id: string;
  tier: SubscriptionTier;
  started_at: string;
  expires_at: string | null;
  is_active: boolean;
}

export interface TierFeatures {
  available_models: string[];
  has_cognitive_learning: boolean;
  has_voice_twin: boolean;
  has_autonomous_workflows: boolean;
  has_custom_models: boolean;
}
```

### Tailwind Configuration

```typescript
// tailwind.config.ts
import type { Config } from 'tailwindcss';

const config: Config = {
  content: [
    './src/pages/**/*.{js,ts,jsx,tsx,mdx}',
    './src/components/**/*.{js,ts,jsx,tsx,mdx}',
    './src/app/**/*.{js,ts,jsx,tsx,mdx}',
  ],
  theme: {
    extend: {
      colors: {
        purple: {
          700: '#4A3AFF',
          600: '#897FFF',
          500: '#ADA3FD',
          400: '#A8A2FF',
          300: '#EAE8FF',
          200: '#F1F0FB',
          100: '#F6F5FF',
        },
        neutral: {
          800: '#170F49',
          700: '#514F6E',
          600: '#6F6C8F',
          500: '#A0A3BD',
          400: '#D9DBE9',
          300: '#F1F2F9',
          200: '#FBFBFF',
        },
      },
      backdropBlur: {
        xl: '24px',
      },
    },
  },
  plugins: [],
};

export default config;
```

### Global CSS with Glass Utilities

```css
/* styles/globals.css */
@tailwind base;
@tailwind components;
@tailwind utilities;

@layer components {
  .glass {
    @apply bg-white/70 backdrop-blur-xl border border-neutral-400/40 shadow-lg rounded-xl;
  }

  .btn-primary {
    @apply bg-purple-700 text-white px-4 py-2 rounded-lg hover:bg-purple-600 transition-colors;
  }

  .btn-outline {
    @apply border border-neutral-400 px-4 py-2 rounded-lg hover:bg-purple-100 transition-colors;
  }
}

@layer base {
  :root {
    --background: #FBFBFF;
    --foreground: #170F49;
  }

  body {
    @apply bg-neutral-200 text-neutral-800;
  }

  /* Focus visible styles for accessibility */
  :focus-visible {
    @apply outline-none ring-2 ring-purple-600 ring-offset-2;
  }
}
```

## Correctness Properties

*A property is a characteristic or behavior that should hold true across all valid executions of a system—essentially, a formal statement about what the system should do. Properties serve as the bridge between human-readable specifications and machine-verifiable correctness guarantees.*

### Navigation Properties

**Property 1: Client-side navigation**
*For any* sidebar menu item click, the URL should change to the corresponding route and the page content should update without a full page refresh (no window.location reload).
**Validates: Requirements 1.3**

**Property 2: Active menu highlighting**
*For any* current route in the dashboard, exactly one sidebar menu item should have the active highlight styling (purple-700 background), and it should correspond to the current route.
**Validates: Requirements 1.6**

### Cognitive Blend Properties

**Property 3: Cognitive blend slider updates**
*For any* valid slider value (0-100), adjusting the Cognitive Blend slider should trigger an API call with the new value and immediately update the displayed percentage.
**Validates: Requirements 2.3**

**Property 4: Cognitive blend range indicators**
*For any* cognitive blend value, the correct range indicator should be displayed: 0-30% shows "AI Logic", 31-70% shows "Balanced", 71-100% shows "Human Mimicry".
**Validates: Requirements 7.2**

**Property 5: High blend warning display**
*For any* cognitive blend value greater than 80%, a warning message about action confirmation should be visible. For values 80% or below, no warning should be displayed.
**Validates: Requirements 7.3**

**Property 6: Kill switch state display**
*For any* kill switch state, when active the panel should display "Twin Paused" status with a re-enable option; when inactive, the stop button should be displayed.
**Validates: Requirements 7.7**

### Activity Stream Properties

**Property 7: Chronological ordering**
*For any* list of activities or learning events, items should be displayed in consistent chronological order (newest first).
**Validates: Requirements 3.1, 8.2**

**Property 8: Required fields rendering**
*For any* rendered item (activity, app card, learning event, call record, or audit entry), all required fields specified in the requirements must be present in the rendered output.
**Validates: Requirements 3.2, 4.5, 8.3, 9.2, 10.1**

**Property 9: Status color mapping**
*For any* status value (success, pending, failed, awaiting_approval, installed, not_installed, needs_attention), the correct color indicator should be applied according to the design system.
**Validates: Requirements 3.3, 4.6**

**Property 10: Approval buttons visibility**
*For any* activity with status 'awaiting_approval', approve and reject buttons should be visible. For activities with other statuses, these buttons should not be present.
**Validates: Requirements 3.5**

### Apps Marketplace Properties

**Property 11: Tab filtering**
*For any* tab selection (All, Installed, Not Installed), the displayed apps should match the filter criteria: All shows all apps, Installed shows only apps with status 'installed' or 'needs_attention', Not Installed shows only apps with status 'not_installed'.
**Validates: Requirements 4.3**

**Property 12: Action button by status**
*For any* app card, the action button should be "Install" (btn-primary) when status is 'not_installed', and "Configure" (btn-outline) when status is 'installed' or 'needs_attention'.
**Validates: Requirements 4.7, 4.8, 5.5**

### Configuration Modal Properties

**Property 13: Modal displays app information**
*For any* app being configured, the configuration modal should display that app's name and icon at the top of the modal.
**Validates: Requirements 6.2**

**Property 14: Permission toggle state reflection**
*For any* permission toggle in the configuration modal, the toggle should reflect the current saved state from the app's config.
**Validates: Requirements 6.4**

**Property 15: Permission toggle local update**
*For any* permission toggle interaction, the local state should update immediately to reflect the new toggle position before saving.
**Validates: Requirements 6.5**

**Property 16: Modal close triggers**
*For any* open modal, clicking outside the modal or pressing the Escape key should close the modal.
**Validates: Requirements 6.8**

### Voice Panel Properties

**Property 17: Phone number conditional display**
*For any* voice profile, if a phone number is provisioned it should be displayed; if phone_number is null, an appropriate "not provisioned" message should be shown.
**Validates: Requirements 9.1**

**Property 18: Voice approval button visibility**
*For any* voice profile where is_approved is false, the "Approve Voice Session" button should be visible. When is_approved is true, the button should not be present.
**Validates: Requirements 9.5**

### Security Panel Properties

**Property 19: Audit log filtering**
*For any* filter combination (date range, action type, integration), the displayed audit entries should match all applied filter criteria.
**Validates: Requirements 10.2**

### Settings Properties

**Property 20: Model selection by subscription tier**
*For any* subscription tier, only the models allowed for that tier should be selectable in the Twin model selection. Free tier: Gemini-3 Flash, Qwen, Mistral. Pro+: adds Gemini-3 Pro.
**Validates: Requirements 11.3**

### State Management Properties

**Property 21: Loading, error, and empty states**
*For any* data-fetching component, it should render appropriately for all three states: loading (show loading indicator), error (show error message), empty (show empty state message).
**Validates: Requirements 13.3**

**Property 22: JWT token inclusion**
*For any* authenticated API request, the Authorization header should be present with the format "Bearer {token}".
**Validates: Requirements 13.5**

**Property 23: Token expiration redirect**
*For any* API response with status 401 (Unauthorized), the system should clear the stored token and redirect the user to the login page.
**Validates: Requirements 13.6**

### Accessibility Properties

**Property 24: Keyboard accessibility**
*For any* interactive element (button, link, toggle, slider), it should be focusable via Tab key and activatable via Enter or Space key.
**Validates: Requirements 14.1**

**Property 25: ARIA labels for icon buttons**
*For any* button that contains only an icon (no visible text), an aria-label attribute must be present with a descriptive label.
**Validates: Requirements 14.2**

**Property 26: WCAG AA color contrast**
*For any* text and background color combination in the UI, the contrast ratio should be at least 4.5:1 for normal text and 3:1 for large text.
**Validates: Requirements 14.4**

**Property 27: Visible focus states**
*For any* focused interactive element, a visible focus indicator (purple-600 ring) should be displayed.
**Validates: Requirements 14.6**

### Design System Properties

**Property 28: Consistent border radius**
*For any* card or modal component, the rounded-xl class should be applied. For any button or input component, the rounded-lg class should be applied.
**Validates: Requirements 12.5, 12.6**

## Error Handling

### API Error Handling

| Error Condition | Response | UI Behavior |
|----------------|----------|-------------|
| Network failure | No response | Show "Connection error" toast, retry button |
| 401 Unauthorized | Token expired/invalid | Clear token, redirect to /login |
| 403 Forbidden | Insufficient permissions | Show "Access denied" message in context |
| 404 Not Found | Resource doesn't exist | Show "Not found" empty state |
| 422 Validation Error | Invalid request data | Show field-level validation errors |
| 429 Rate Limited | Too many requests | Show "Please wait" message with countdown |
| 500 Server Error | Backend failure | Show "Something went wrong" with retry option |

### Component Error Boundaries

```typescript
// components/ErrorBoundary.tsx
'use client';

import { Component, ReactNode } from 'react';
import { Button } from '@/components/ui/Button';
import { GlassPanel } from '@/components/ui/GlassPanel';

interface Props {
  children: ReactNode;
  fallback?: ReactNode;
}

interface State {
  hasError: boolean;
  error?: Error;
}

export class ErrorBoundary extends Component<Props, State> {
  state: State = { hasError: false };

  static getDerivedStateFromError(error: Error): State {
    return { hasError: true, error };
  }

  render() {
    if (this.state.hasError) {
      return this.props.fallback || (
        <GlassPanel className="p-6 text-center">
          <h3 className="text-lg font-semibold text-neutral-800 mb-2">
            Something went wrong
          </h3>
          <p className="text-neutral-600 mb-4">
            {this.state.error?.message || 'An unexpected error occurred'}
          </p>
          <Button onClick={() => this.setState({ hasError: false })}>
            Try again
          </Button>
        </GlassPanel>
      );
    }

    return this.props.children;
  }
}
```

### Loading and Empty States

```typescript
// components/ui/LoadingState.tsx
export function LoadingState({ message = 'Loading...' }: { message?: string }) {
  return (
    <div className="flex items-center justify-center p-8">
      <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-purple-700" />
      <span className="ml-3 text-neutral-600">{message}</span>
    </div>
  );
}

// components/ui/EmptyState.tsx
export function EmptyState({ 
  title, 
  description, 
  action 
}: { 
  title: string; 
  description: string; 
  action?: ReactNode;
}) {
  return (
    <div className="text-center p-8">
      <h3 className="text-lg font-semibold text-neutral-800 mb-2">{title}</h3>
      <p className="text-neutral-600 mb-4">{description}</p>
      {action}
    </div>
  );
}
```

### Form Validation Errors

| Field | Validation | Error Message |
|-------|------------|---------------|
| Cognitive Blend | 0-100 integer | "Value must be between 0 and 100" |
| Permission toggles | Boolean | N/A (toggle can't be invalid) |
| Search query | Max 200 chars | "Search query too long" |
| Date range | Start <= End | "Start date must be before end date" |

### Kill Switch Error Handling

```typescript
// Special handling for kill switch failures
async function handleKillSwitchActivation() {
  try {
    await api.killSwitch.activate();
  } catch (error) {
    // Kill switch failures are critical - show prominent error
    showCriticalError({
      title: 'Failed to activate kill switch',
      message: 'Please try again or contact support immediately',
      actions: [
        { label: 'Retry', onClick: handleKillSwitchActivation },
        { label: 'Contact Support', href: '/support' },
      ],
    });
  }
}
```

## Testing Strategy

### Unit Testing

Unit tests verify specific examples, edge cases, and component behavior. Use **Jest** with **React Testing Library** for component testing.

**Focus Areas:**
- Component rendering with various props
- User interaction handling (clicks, keyboard events)
- Conditional rendering based on state
- Error boundary behavior
- Hook behavior with mocked API responses

**Example Test Structure:**
```typescript
// __tests__/components/twin/CognitiveBlendSlider.test.tsx
import { render, screen, fireEvent } from '@testing-library/react';
import { CognitiveBlendSlider } from '@/components/twin/CognitiveBlendSlider';

describe('CognitiveBlendSlider', () => {
  it('displays current blend value', () => {
    render(<CognitiveBlendSlider value={50} onChange={jest.fn()} />);
    expect(screen.getByText('50%')).toBeInTheDocument();
  });

  it('shows warning when blend exceeds 80%', () => {
    render(<CognitiveBlendSlider value={85} onChange={jest.fn()} />);
    expect(screen.getByText(/require your confirmation/)).toBeInTheDocument();
  });

  it('calls onChange when slider is adjusted', () => {
    const onChange = jest.fn();
    render(<CognitiveBlendSlider value={50} onChange={onChange} />);
    fireEvent.change(screen.getByRole('slider'), { target: { value: '75' } });
    expect(onChange).toHaveBeenCalledWith(75);
  });
});
```

### Property-Based Testing

Property-based tests verify universal properties across many generated inputs. Use **fast-check** as the PBT library for TypeScript/JavaScript.

**Configuration:**
- Minimum 100 iterations per property test
- Each test tagged with: `// Feature: dashboard-frontend, Property N: [property text]`

**Key Properties to Test:**

1. **Cognitive blend range indicators (Property 4)**
```typescript
import fc from 'fast-check';

// Feature: dashboard-frontend, Property 4: Cognitive blend range indicators
test('displays correct range indicator for any blend value', () => {
  fc.assert(
    fc.property(fc.integer({ min: 0, max: 100 }), (blend) => {
      const { getByText } = render(<CognitiveBlendSlider value={blend} onChange={() => {}} />);
      
      if (blend <= 30) {
        expect(getByText('AI Logic')).toBeInTheDocument();
      } else if (blend <= 70) {
        expect(getByText('Balanced')).toBeInTheDocument();
      } else {
        expect(getByText('Human Mimicry')).toBeInTheDocument();
      }
    }),
    { numRuns: 100 }
  );
});
```

2. **Status color mapping (Property 9)**
```typescript
// Feature: dashboard-frontend, Property 9: Status color mapping
test('applies correct color for any activity status', () => {
  const statuses: ActivityStatus[] = ['success', 'pending', 'failed', 'awaiting_approval'];
  const expectedColors = {
    success: 'text-green-600',
    pending: 'text-yellow-600',
    failed: 'text-red-600',
    awaiting_approval: 'text-orange-600',
  };

  fc.assert(
    fc.property(fc.constantFrom(...statuses), (status) => {
      const activity = createMockActivity({ status });
      const { container } = render(<ActivityItem activity={activity} />);
      expect(container.querySelector(`.${expectedColors[status]}`)).toBeInTheDocument();
    }),
    { numRuns: 100 }
  );
});
```

3. **Tab filtering (Property 11)**
```typescript
// Feature: dashboard-frontend, Property 11: Tab filtering
test('filters apps correctly for any tab selection', () => {
  fc.assert(
    fc.property(
      fc.array(fc.record({
        id: fc.uuid(),
        name: fc.string(),
        status: fc.constantFrom('installed', 'not_installed', 'needs_attention'),
      }), { minLength: 1, maxLength: 20 }),
      fc.constantFrom('all', 'installed', 'not_installed'),
      (apps, tab) => {
        const filtered = filterAppsByTab(apps, tab);
        
        if (tab === 'all') {
          expect(filtered.length).toBe(apps.length);
        } else if (tab === 'installed') {
          expect(filtered.every(a => a.status === 'installed' || a.status === 'needs_attention')).toBe(true);
        } else {
          expect(filtered.every(a => a.status === 'not_installed')).toBe(true);
        }
      }
    ),
    { numRuns: 100 }
  );
});
```

4. **Required fields rendering (Property 8)**
```typescript
// Feature: dashboard-frontend, Property 8: Required fields rendering
test('activity items contain all required fields', () => {
  fc.assert(
    fc.property(
      fc.record({
        id: fc.uuid(),
        description: fc.string({ minLength: 1 }),
        integration: fc.string({ minLength: 1 }),
        action_type: fc.string({ minLength: 1 }),
        status: fc.constantFrom('success', 'pending', 'failed', 'awaiting_approval'),
        timestamp: fc.date().map(d => d.toISOString()),
        cognitive_blend: fc.integer({ min: 0, max: 100 }),
      }),
      (activity) => {
        const { getByText } = render(<ActivityItem activity={activity} />);
        expect(getByText(activity.description)).toBeInTheDocument();
        expect(getByText(activity.integration)).toBeInTheDocument();
      }
    ),
    { numRuns: 100 }
  );
});
```

### Integration Testing

Integration tests verify component interactions and API integration. Use **Playwright** or **Cypress** for end-to-end testing.

**Key Flows to Test:**
- Login → Dashboard navigation → Twin overview display
- Cognitive blend adjustment → API call → UI update
- Kill switch activation → Confirmation → API call → Status update
- App installation → OAuth flow → Configuration modal
- Activity stream → Approve action → Status update

### Accessibility Testing

Use **axe-core** with Jest for automated accessibility testing:

```typescript
import { axe, toHaveNoViolations } from 'jest-axe';

expect.extend(toHaveNoViolations);

test('Twin overview has no accessibility violations', async () => {
  const { container } = render(<TwinOverview />);
  const results = await axe(container);
  expect(results).toHaveNoViolations();
});
```

### Test Organization

```
neuro-frontend/
├── __tests__/
│   ├── components/
│   │   ├── ui/
│   │   │   ├── Button.test.tsx
│   │   │   ├── GlassPanel.test.tsx
│   │   │   └── Slider.test.tsx
│   │   ├── twin/
│   │   │   ├── CognitiveBlendSlider.test.tsx
│   │   │   ├── KillSwitch.test.tsx
│   │   │   └── ActivityStream.test.tsx
│   │   ├── apps/
│   │   │   ├── AppCard.test.tsx
│   │   │   └── ConfigModal.test.tsx
│   │   └── layout/
│   │       └── Sidebar.test.tsx
│   ├── hooks/
│   │   ├── useTwin.test.tsx
│   │   └── useApps.test.tsx
│   ├── property/
│   │   ├── cognitive-blend.property.test.tsx
│   │   ├── status-mapping.property.test.tsx
│   │   ├── tab-filtering.property.test.tsx
│   │   └── accessibility.property.test.tsx
│   └── integration/
│       ├── twin-flow.test.tsx
│       ├── apps-flow.test.tsx
│       └── navigation.test.tsx
├── e2e/
│   ├── dashboard.spec.ts
│   ├── twin-management.spec.ts
│   └── apps-marketplace.spec.ts
```
