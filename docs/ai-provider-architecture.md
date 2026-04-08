# AI Provider Architecture

## System Overview

```
┌─────────────────────────────────────────────────────────────────┐
│                         AIService                                │
│  (Orchestrates credit validation, model routing, CSM loading)   │
└────────────────────────────┬────────────────────────────────────┘
                             │
                             │ Builds messages array:
                             │ [
                             │   {"role": "system", "content": "..."},
                             │   {"role": "user", "content": "..."}