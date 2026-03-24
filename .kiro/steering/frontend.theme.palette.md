---
inclusion: fileMatch
fileMatchPattern: ['neuro-frontend/**/*.ts', 'neuro-frontend/**/*.tsx', 'neuro-frontend/**/*.css', 'neuro-frontend/tailwind.config.*']
---

# NeuroTwin Frontend Theme & Color Palette

Design system rules for the NeuroTwin cognitive UI. Apply these when creating or modifying frontend components.

## Color Palette

### Primary (Purple Cognitive)
| Token | Hex | Usage |
|-------|-----|-------|
| `purple-700` | `#4A3AFF` | Primary buttons, CTAs, links |
| `purple-600` | `#897FFF` | Hover/active states, focus rings |
| `purple-500` | `#ADA3FD` | Secondary accents |
| `purple-400` | `#A8A2FF` | Disabled states |
| `purple-300` | `#EAE8FF` | Light backgrounds, badges |
| `purple-200` | `#F1F0FB` | Subtle highlights |
| `purple-100` | `#F6F5FF` | Card backgrounds |

### Neutral
| Token | Hex | Usage |
|-------|-----|-------|
| `neutral-800` | `#170F49` | Sidebar, primary text |
| `neutral-700` | `#514F6E` | Secondary text |
| `neutral-600` | `#6F6C8F` | Muted/placeholder text |
| `neutral-500` | `#A0A3BD` | Icons, dividers |
| `neutral-400` | `#D9DBE9` | Borders, separators |
| `neutral-300` | `#F1F2F9` | Subtle backgrounds |
| `neutral-200` | `#FBFBFF` | Main content background |
| `white` | `#FFFFFF` | Cards, modals |

## Component Styling Rules

- **Sidebar**: Use `bg-neutral-800` with `text-white`
- **Main content area**: Use `bg-neutral-200`
- **Cards/Modals**: Apply glass effect (see below)
- **Primary buttons**: `bg-purple-700 hover:bg-purple-600 text-white`
- **Secondary buttons**: `bg-purple-100 text-purple-700 hover:bg-purple-200`
- **Text hierarchy**: `neutral-800` (primary) → `neutral-700` (secondary) → `neutral-600` (muted)
- **Borders**: Use `border-neutral-400` or `border-neutral-400/40` for subtle

## Glass Effect Pattern

Apply to cards, modals, and floating elements for the cognitive OS aesthetic:

```css
.glass {
  @apply bg-white/70 backdrop-blur-xl border border-neutral-400/40 shadow-lg rounded-xl;
}
```

## Tailwind Config Extension

Ensure `tailwind.config.js` extends these colors:

```js
theme: {
  extend: {
    colors: {
      purple: {
        700: "#4A3AFF",
        600: "#897FFF",
        500: "#ADA3FD",
        400: "#A8A2FF",
        300: "#EAE8FF",
        200: "#F1F0FB",
        100: "#F6F5FF",
      },
      neutral: {
        800: "#170F49",
        700: "#514F6E",
        600: "#6F6C8F",
        500: "#A0A3BD",
        400: "#D9DBE9",
        300: "#F1F2F9",
        200: "#FBFBFF",
      }
    }
  }
}
```

## Do's and Don'ts

- **Do** use semantic color tokens (`purple-700`) instead of raw hex values
- **Do** maintain consistent border-radius (`rounded-xl` for cards, `rounded-lg` for buttons)
- **Do** apply glass effect to elevated surfaces
- **Don't** use colors outside this palette without approval
- **Don't** mix dark mode neutral colors with light backgrounds inconsistently
