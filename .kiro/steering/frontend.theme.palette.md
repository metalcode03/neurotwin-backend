---
inclusion: fileMatch
fileMatchPattern: ['neuro-frontend/**/*.ts', 'neuro-frontend/**/*.tsx', 'neuro-frontend/**/*.css', 'neuro-frontend/tailwind.config.*']
---

# NeuroTwin Frontend Theme & Color Palette

Design system rules for the NeuroTwin cognitive UI. Apply these when creating or modifying frontend components.

## Tailwind v4 Setup
Colors are defined via `@theme inline` in `globals.css` — no `tailwind.config.js` color extension needed.
Use Tailwind color tokens directly (e.g. `bg-purple-700`, `text-neutral-500`).

## Color Palette

### Primary (Purple Cognitive)
| Token | Hex | Usage |
|-------|-----|-------|
| `purple-700` | `#4A3AFF` | Primary buttons, CTAs, active nav item background |
| `purple-600` | `#897FFF` | Hover/active states, focus rings, active nav indicator |
| `purple-500` | `#ADA3FD` | Secondary accents |
| `purple-400` | `#A8A2FF` | Active nav left-border indicator |
| `purple-300` | `#EAE8FF` | Light backgrounds, badges |
| `purple-200` | `#F1F0FB` | Subtle highlights, button hover backgrounds |
| `purple-100` | `#F6F5FF` | Card backgrounds, icon container backgrounds |

### Neutral (Light Mode)
| Token | Hex | Usage |
|-------|-----|-------|
| `neutral-800` | `#170F49` | Primary text, sidebar text |
| `neutral-700` | `#514F6E` | Secondary text |
| `neutral-600` | `#6F6C8F` | Muted/placeholder text |
| `neutral-500` | `#A0A3BD` | Icons, dividers |
| `neutral-400` | `#D9DBE9` | Borders, separators |
| `neutral-300` | `#F1F2F9` | Subtle hover backgrounds |
| `neutral-200` | `#FBFBFF` | Main content background |

### Semantic / Status Colors
| Color | Usage |
|-------|-------|
| `emerald-600 / emerald-400` | Success states, audit log success badge |
| `red-600 / red-400` | Error states, failure badge, kill-switch alert |
| `orange-500 / orange-400` | Warning states, pending approval badge, danger button |
| `green-100 / green-700` | Badge success variant |
| `orange-100 / orange-700` | Badge warning variant |

## CSS Variables (Theme-Adaptive)
These variables switch automatically between light and dark mode. Prefer them over hardcoded colors for theme-sensitive values:

| Variable | Light | Dark |
|----------|-------|------|
| `--background` | `#FAFAFA` | `#09090B` |
| `--foreground` | `#09090B` | `#FAFAFA` |
| `--sidebar-bg` | `#FFFFFF` | `#111113` |
| `--header-bg` | `#FFFFFF` | `rgba(17,17,19,0.8)` |
| `--border-color` | `#E4E4E7` | `#27272A` |
| `--card-bg` | `rgba(255,255,255,0.85)` | `rgba(24,24,27,0.6)` |
| `--text-primary` | `#09090B` | `#FAFAFA` |
| `--text-secondary` | `#52525B` | `#A1A1AA` |
| `--text-muted` | `#A1A1AA` | `#71717A` |

Usage: `style={{ background: 'var(--sidebar-bg)' }}` or `color: var(--text-primary)`

## Dark Mode Color Overrides
In dark mode, neutral tokens are remapped:
- `neutral-200` → `#09090B` (page background)
- `neutral-300` → `#18181B`
- `neutral-400` → `#27272A` (borders)
- `neutral-800` → `#FAFAFA` (primary text)

Always pair light and dark variants explicitly in className:
```tsx
className="bg-white dark:bg-[#111113] border border-neutral-200 dark:border-white/10"
```

## Glass Effect
The `glass` utility class (defined in `globals.css`) adapts to light/dark automatically:

```css
/* Light */
background: var(--card-bg);  /* rgba(255,255,255,0.85) */
backdrop-filter: blur(20px);
border: 1px solid var(--border-color);
border-radius: 0.75rem;

/* Dark */
background: var(--card-bg);  /* rgba(24,24,27,0.6) */
border: 1px solid rgba(255,255,255,0.05);
```

Use via `GlassPanel` component or `className="glass"` directly.

## Standard Card Pattern
Most dashboard panels use solid backgrounds, not glass:
```tsx
className="bg-white dark:bg-[#111113] border border-neutral-200 dark:border-white/10 rounded-3xl p-6 md:p-8 shadow-sm"
```

## Component Styling Reference

### Sidebar
- Background: `var(--sidebar-bg)` (white / `#111113`)
- Border: `border-r border-neutral-400 dark:border-transparent`
- Active nav item: `bg-purple-700 text-white`
- Active indicator: `absolute left-0 w-1 h-8 bg-purple-400 rounded-r`
- Hover: `hover:bg-neutral-300 dark:hover:bg-neutral-400/7`

### Page Background
- `bg-[#FBFBFF] dark:bg-[#09090B]` (use explicit hex, not token, for page backgrounds)

### Primary Buttons
- `bg-purple-700 text-white hover:bg-purple-600 focus:ring-purple-600`

### Outline Buttons
- `border border-neutral-400 text-neutral-800 hover:bg-purple-100 focus:ring-purple-600`

### Danger Buttons
- `bg-orange-500 text-white hover:bg-orange-600`

### Ghost Buttons
- `text-neutral-700 hover:bg-neutral-300`

### Text Hierarchy
- Primary: `text-neutral-900 dark:text-white` (headings, labels)
- Secondary: `text-neutral-500 dark:text-neutral-400` (descriptions, subtitles)
- Muted: `text-neutral-400 dark:text-neutral-500` (placeholders, icons)

### Inputs
```tsx
className="bg-neutral-50 dark:bg-black/20 border border-neutral-200 dark:border-white/10 rounded-2xl text-neutral-900 dark:text-white placeholder-neutral-400 dark:placeholder-neutral-500 focus:outline-none focus:ring-2 focus:ring-neutral-900 dark:focus:ring-white focus:border-transparent transition-all"
```

### Filter Pills (Active / Inactive)
- Active: `bg-neutral-900 text-white dark:bg-white dark:text-black shadow-sm`
- Inactive: `bg-white dark:bg-white/5 border border-neutral-200 dark:border-white/5 text-neutral-600 dark:text-neutral-300 hover:bg-neutral-50 dark:hover:bg-white/10`

### Icon Containers
- Subtle: `bg-purple-50 dark:bg-purple-500/10 rounded-2xl border border-purple-100 dark:border-purple-500/20`
- Neutral: `bg-neutral-50 dark:bg-white/5 rounded-2xl border border-neutral-100 dark:border-white/5`

### Status / Outcome Badges
- Success: `text-emerald-600 dark:text-emerald-400 bg-emerald-50 dark:bg-emerald-500/10 border border-emerald-100 dark:border-emerald-500/20`
- Failure: `text-red-600 dark:text-red-400 bg-red-50 dark:bg-red-500/10 border border-red-100 dark:border-red-500/20`
- Pending: `text-orange-600 dark:text-orange-400 bg-orange-50 dark:bg-orange-500/10 border border-orange-100 dark:border-orange-500/20`

## Border Radius
| Element | Radius |
|---------|--------|
| Cards / panels | `rounded-3xl` |
| Modals / GlassPanel | `rounded-xl` |
| Buttons | `rounded-lg` |
| Inputs | `rounded-2xl` |
| Badges / pills | `rounded-full` |
| Icon containers | `rounded-2xl` |
| Audit entries / list items | `rounded-2xl` |

## Typography
- Base font size: `14px` (set on `body`)
- Headings: `text-2xl md:text-3xl font-bold tracking-tight`
- Subheadings: `text-xl font-bold tracking-tight`
- Body: `text-[15px]`
- Small / labels: `text-[13px] font-semibold`
- Micro / badges: `text-[11px] font-bold uppercase tracking-wider`

## Do's and Don'ts
- Do use semantic color tokens (`purple-700`) instead of raw hex — except for page backgrounds where explicit hex is conventional (`bg-[#FBFBFF]`)
- Do always pair light + dark variants for every color class
- Do use CSS variables for sidebar, header, and card backgrounds
- Do use `rounded-3xl` for cards, `rounded-2xl` for inputs and list items
- Don't use `bg-white/10 backdrop-blur-md` (old glass pattern) — use the `glass` utility or standard card pattern
- Don't use `bg-neutral-800` for the sidebar — use `var(--sidebar-bg)`
- Don't mix dark mode overrides inconsistently
